"""
GLS Borderou IMAP Integration
Descarca borderouri de incasare (desfasuratoare de ramburs) din email-uri GLS

Email pattern:
- From: noreply@gls-romania.ro
- Subject: "Lista Colete cu Ramburs COD list – DD.MM.YYYY"
- Attachment: XLSX file cu coletele si sumele
"""

import os
import re
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# IMAP config (same as email_imap.py)
IMAP_SERVER = os.getenv('IMAP_SERVER', 'mail.obsid.ro')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
IMAP_USER = os.getenv('IMAP_USER', 'documente@obsid.ro')
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD', '')


def get_imap_connection():
    """Conecteaza la serverul IMAP."""
    if not IMAP_PASSWORD:
        raise ValueError("IMAP_PASSWORD nu este configurat in .env")

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASSWORD)
    return mail


def decode_email_subject(subject):
    """Decodeaza subject-ul email-ului."""
    if subject is None:
        return ""

    decoded_parts = decode_header(subject)
    decoded_subject = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
        else:
            decoded_subject += part

    return decoded_subject


def extract_date_from_subject(subject: str) -> Optional[str]:
    """
    Extrage data din subject-ul email-ului GLS.

    Pattern: "Lista Colete cu Ramburs COD list – 04.12.2025"
    Returns: "2025-12-04" (format ISO)
    """
    # Pattern pentru data in format DD.MM.YYYY
    pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
    match = re.search(pattern, subject)

    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    return None


def search_gls_borderou_emails(days_back: int = 60) -> List[Dict]:
    """
    Cauta email-uri de la GLS cu borderouri de ramburs.

    Args:
        days_back: Cate zile in urma sa caute

    Returns:
        Lista de dict-uri cu informatii despre email-uri
    """
    mail = get_imap_connection()

    try:
        mail.select('INBOX')

        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')

        # Cauta email-uri de la GLS cu "Lista Colete" sau "Ramburs" in subject
        search_criteria = f'(SINCE {since_date} FROM "gls-romania.ro")'

        status, messages = mail.search(None, search_criteria)

        if status != 'OK':
            return []

        email_ids = messages[0].split()
        results = []

        for email_id in email_ids:
            try:
                # Fetch doar header-ele pentru performanta
                status, msg_data = mail.fetch(email_id, '(RFC822.HEADER)')

                if status != 'OK':
                    continue

                raw_header = msg_data[0][1]
                msg = email.message_from_bytes(raw_header)

                subject = decode_email_subject(msg['Subject'])

                # Verifica daca e email de borderou (Lista Colete cu Ramburs)
                if 'Lista Colete' not in subject and 'Ramburs' not in subject:
                    continue

                # Extrage data din subject
                borderou_date = extract_date_from_subject(subject)

                if not borderou_date:
                    continue

                date_str = msg['Date']

                results.append({
                    'email_id': email_id,
                    'subject': subject,
                    'email_date': date_str,
                    'borderou_date': borderou_date
                })

            except Exception as e:
                print(f"Eroare la procesare email {email_id}: {e}")
                continue

        # Sorteaza dupa data borderoului (cele mai recente primele)
        results.sort(key=lambda x: x['borderou_date'], reverse=True)

        return results

    finally:
        mail.logout()


def download_gls_borderou_attachment(email_id) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Descarca atasamentul XLSX din email-ul GLS.

    Args:
        email_id: ID-ul email-ului

    Returns:
        Tuple (xlsx_bytes, filename) sau (None, None)
    """
    mail = get_imap_connection()

    try:
        mail.select('INBOX')

        # Fetch email complet
        status, msg_data = mail.fetch(email_id, '(RFC822)')

        if status != 'OK':
            return None, None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Cauta atasamentul XLSX
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                filename = part.get_filename()

                if filename:
                    # Decodeaza filename daca e encoded
                    decoded_filename = decode_header(filename)
                    if decoded_filename[0][1]:
                        filename = decoded_filename[0][0].decode(decoded_filename[0][1])
                    elif isinstance(decoded_filename[0][0], bytes):
                        filename = decoded_filename[0][0].decode('utf-8', errors='ignore')
                    else:
                        filename = decoded_filename[0][0]

                    # Verifica daca e XLSX sau XLS
                    if filename.lower().endswith(('.xlsx', '.xls')):
                        xlsx_bytes = part.get_payload(decode=True)
                        return xlsx_bytes, filename

        return None, None

    finally:
        mail.logout()


def parse_gls_borderou_xlsx(xlsx_bytes: bytes) -> Dict:
    """
    Parseaza fisierul XLSX cu borderou GLS.

    Structura fisierului GLS:
    - Row 0: "GLS General Logistics Systems Romania SRL"
    - Row 5: "Data tranferarii banilor: DD.MM.YYYY"
    - Row 7: Headers (Număr referinta, Număr colet, Referire la ramb., Livrat la data, Sumă ramburs, currency, Postal Address)
    - Row 8+: Coletele
    - Last row: Total (suma in coloana 4)

    Args:
        xlsx_bytes: Continutul fisierului XLSX

    Returns:
        Dict cu total_amount, parcels_count, parcels (lista), transfer_date
    """
    import pandas as pd

    try:
        # Citeste XLSX fara header
        df = pd.read_excel(BytesIO(xlsx_bytes), header=None)

        # Extrage data transferului din row 5
        transfer_date = None
        if len(df) > 5:
            date_text = str(df.iloc[5][0])
            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_text)
            if date_match:
                day, month, year = date_match.groups()
                transfer_date = f"{year}-{month}-{day}"

        # Gaseste randul cu header-uri (contine "colet" si "ramburs")
        header_row = 7  # Default
        for i in range(len(df)):
            row_str = ' '.join(str(v).lower() for v in df.iloc[i].values if pd.notna(v))
            if 'colet' in row_str and 'ramburs' in row_str:
                header_row = i
                break

        # Extrage coletele (de la header_row + 1 pana la ultima linie)
        parcels = []
        total_from_file = 0

        for i in range(header_row + 1, len(df)):
            row = df.iloc[i]

            # Coloana 1 = Număr colet
            parcel_number = row[1] if len(row) > 1 and pd.notna(row[1]) else None

            # Coloana 4 = Sumă ramburs
            amount = row[4] if len(row) > 4 and pd.notna(row[4]) else 0

            # Coloana 6 = Postal Address (contine numele)
            address = str(row[6]) if len(row) > 6 and pd.notna(row[6]) else ''

            # Coloana 3 = Livrat la data
            delivery_date = row[3] if len(row) > 3 and pd.notna(row[3]) else None

            # Daca nu are parcel_number, e linia de total
            if parcel_number is None or str(parcel_number) == 'nan':
                # Aceasta e linia de total
                try:
                    total_from_file = float(amount)
                except:
                    pass
                continue

            # Extrage numele din adresa (prima parte inainte de RO-)
            recipient_name = address.split('RO-')[0].strip() if 'RO-' in address else address[:50]

            try:
                cod_amount = float(amount)
            except:
                cod_amount = 0

            parcels.append({
                'parcel_number': str(int(parcel_number)) if isinstance(parcel_number, float) else str(parcel_number),
                'cod_amount': cod_amount,
                'recipient_name': recipient_name,
                'delivery_date': str(delivery_date) if delivery_date else None
            })

        # Calculeaza totalul din colete
        calculated_total = round(sum(p['cod_amount'] for p in parcels), 2)

        # Foloseste totalul din fisier daca e disponibil, altfel cel calculat
        final_total = total_from_file if total_from_file > 0 else calculated_total

        return {
            'total_amount': round(final_total, 2),
            'parcels_count': len(parcels),
            'parcels': parcels,
            'transfer_date': transfer_date,
            'calculated_total': calculated_total
        }

    except Exception as e:
        print(f"Eroare la parsare XLSX: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_amount': 0,
            'parcels_count': 0,
            'parcels': [],
            'error': str(e)
        }


def sync_gls_borderouri_from_email(days_back: int = 60) -> Dict:
    """
    Sincronizeaza borderouri GLS din email in Supabase.

    Args:
        days_back: Cate zile in urma sa caute

    Returns:
        Dict cu statistici
    """
    from .supabase_client import get_supabase_client

    stats = {
        'emails_found': 0,
        'borderouri_inserted': 0,
        'borderouri_skipped': 0,
        'parcels_inserted': 0,
        'errors': []
    }

    supabase = get_supabase_client()

    # Obtine borderouri existente
    existing = supabase.table('gls_borderouri').select('borderou_date, total_amount').execute()
    existing_keys = {(row['borderou_date'], float(row['total_amount'])) for row in existing.data}

    # Cauta email-uri GLS
    emails = search_gls_borderou_emails(days_back=days_back)
    stats['emails_found'] = len(emails)

    for email_info in emails:
        try:
            borderou_date = email_info['borderou_date']

            # Descarca atasamentul
            xlsx_bytes, filename = download_gls_borderou_attachment(email_info['email_id'])

            if not xlsx_bytes:
                stats['errors'].append(f"Nu s-a gasit atasament pentru {borderou_date}")
                continue

            # Parseaza XLSX
            parsed = parse_gls_borderou_xlsx(xlsx_bytes)

            if parsed.get('error'):
                stats['errors'].append(f"Eroare parsare {borderou_date}: {parsed['error']}")
                continue

            total_amount = parsed['total_amount']

            # Verifica duplicat
            if (borderou_date, total_amount) in existing_keys:
                stats['borderouri_skipped'] += 1
                continue

            # Insereaza borderou
            borderou_data = {
                'borderou_date': borderou_date,
                'email_date': email_info['email_date'],
                'email_subject': email_info['subject'],
                'file_name': filename,
                'total_amount': total_amount,
                'parcels_count': parsed['parcels_count'],
                'source': 'GLS'
            }

            result = supabase.table('gls_borderouri').insert(borderou_data).execute()

            if result.data:
                borderou_id = result.data[0]['id']
                stats['borderouri_inserted'] += 1
                existing_keys.add((borderou_date, total_amount))

                # Insereaza coletele
                for parcel in parsed['parcels']:
                    parcel_data = {
                        'borderou_id': borderou_id,
                        'parcel_number': parcel.get('parcel_number', ''),
                        'cod_amount': parcel.get('cod_amount', 0),
                        'recipient_name': parcel.get('recipient_name', '')
                    }

                    try:
                        supabase.table('gls_borderou_parcels').insert(parcel_data).execute()
                        stats['parcels_inserted'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Eroare inserare colet: {e}")

        except Exception as e:
            stats['errors'].append(f"Eroare procesare {email_info.get('borderou_date', 'unknown')}: {e}")

    return stats


def match_borderouri_with_bank_transactions() -> Dict:
    """
    Potriveste borderourile GLS cu tranzactiile bancare.

    Returns:
        Dict cu statistici matching
    """
    from .supabase_client import get_supabase_client

    supabase = get_supabase_client()

    stats = {
        'borderouri_total': 0,
        'borderouri_matched': 0,
        'borderouri_unmatched': 0,
        'matches': [],
        'unmatched': []
    }

    # Obtine borderouri nepotrivite
    borderouri = supabase.table('gls_borderouri') \
        .select('*') \
        .eq('op_matched', False) \
        .execute().data

    stats['borderouri_total'] = len(borderouri)

    # Obtine tranzactii bancare GLS
    bank_trans = supabase.table('bank_transactions') \
        .select('*') \
        .eq('source', 'GLS') \
        .execute().data

    # Creeaza index pentru tranzactii dupa suma
    trans_by_amount = {}
    for trans in bank_trans:
        amount = round(float(trans['amount']), 2)
        if amount not in trans_by_amount:
            trans_by_amount[amount] = []
        trans_by_amount[amount].append(trans)

    for borderou in borderouri:
        total = round(float(borderou['total_amount']), 2)

        # Cauta tranzactie cu suma identica
        if total in trans_by_amount and trans_by_amount[total]:
            trans = trans_by_amount[total][0]

            # Actualizeaza borderou cu info OP
            supabase.table('gls_borderouri').update({
                'op_reference': trans['op_reference'],
                'op_date': trans['transaction_date'],
                'op_matched': True
            }).eq('id', borderou['id']).execute()

            stats['borderouri_matched'] += 1
            stats['matches'].append({
                'borderou_date': borderou['borderou_date'],
                'amount': total,
                'op_reference': trans['op_reference'],
                'op_date': trans['transaction_date']
            })

            # Sterge din lista pentru a nu fi folosita din nou
            trans_by_amount[total].pop(0)
        else:
            stats['borderouri_unmatched'] += 1
            stats['unmatched'].append({
                'borderou_date': borderou['borderou_date'],
                'amount': total,
                'parcels_count': borderou['parcels_count']
            })

    return stats


def get_borderouri_status() -> Dict:
    """
    Returneaza statusul borderourilor GLS.

    Returns:
        Dict cu statistici
    """
    from .supabase_client import get_supabase_client

    supabase = get_supabase_client()

    # Total borderouri
    all_borderouri = supabase.table('gls_borderouri').select('*').execute().data

    matched = [b for b in all_borderouri if b['op_matched']]
    unmatched = [b for b in all_borderouri if not b['op_matched']]

    return {
        'total': len(all_borderouri),
        'matched': len(matched),
        'unmatched': len(unmatched),
        'matched_amount': sum(float(b['total_amount']) for b in matched),
        'unmatched_amount': sum(float(b['total_amount']) for b in unmatched),
        'unmatched_details': [
            {
                'borderou_date': b['borderou_date'],
                'amount': float(b['total_amount']),
                'parcels_count': b['parcels_count']
            }
            for b in unmatched
        ]
    }
