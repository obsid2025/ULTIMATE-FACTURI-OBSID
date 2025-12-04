"""
Parser pentru extrase de cont PDF de la Banca Transilvania
Extrage tranzactiile in acelasi format ca MT940 pentru import in Supabase
"""

import re
from typing import List, Dict, Optional
from datetime import datetime
import pdfplumber


def parse_bt_pdf_extract(pdf_path: str) -> List[Dict]:
    """
    Parseaza un extras de cont PDF de la Banca Transilvania.

    Args:
        pdf_path: Calea catre fisierul PDF

    Returns:
        Lista de tranzactii in format compatibil cu bank_transactions
    """
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # Extrage tranzactiile din text
    transactions = extract_transactions_from_text(full_text)

    return transactions


def parse_bt_pdf_from_bytes(pdf_bytes) -> List[Dict]:
    """
    Parseaza un extras de cont PDF din bytes (pentru upload Streamlit).

    Args:
        pdf_bytes: Continutul PDF ca bytes sau file-like object

    Returns:
        Lista de tranzactii
    """
    import io

    if hasattr(pdf_bytes, 'read'):
        pdf_bytes = pdf_bytes.read()

    transactions = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    transactions = extract_transactions_from_text(full_text)

    return transactions


def extract_transactions_from_text(text: str) -> List[Dict]:
    """
    Extrage tranzactiile din textul extras din PDF.

    Cauta pattern-uri pentru:
    - Incasare OP (GLS, Sameday/Delivery Solutions, Netopia)
    - Data, suma, referinta
    """
    transactions = []
    lines = text.split('\n')

    current_date = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detecteaza data (format DD/MM/YYYY la inceputul liniei)
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', line)
        if date_match:
            current_date = date_match.group(1)

        # Cauta "Incasare OP" - acestea sunt tranzactiile de interes
        if 'Incasare OP' in line and current_date:
            # Colecteaza toate liniile pana la urmatoarea tranzactie sau data
            transaction_text = line
            j = i + 1

            while j < len(lines):
                next_line = lines[j].strip()
                # Stop daca gasim o noua data sau RULAJ ZI
                if re.match(r'^(\d{2}/\d{2}/\d{4})', next_line) or 'RULAJ ZI' in next_line:
                    break
                # Stop daca gasim alta tranzactie (Plata, Incasare, Comision)
                if any(x in next_line for x in ['Plata la POS', 'Plata OP', 'Plata Instant', 'Comision']):
                    break
                transaction_text += " " + next_line
                j += 1

            # Parseaza tranzactia
            trans = parse_incasare_op(transaction_text, current_date)
            if trans:
                transactions.append(trans)

        i += 1

    return transactions


def parse_incasare_op(text: str, date_str: str) -> Optional[Dict]:
    """
    Parseaza o tranzactie de tip "Incasare OP".

    Extrage:
    - Sursa (GLS, Sameday, Netopia)
    - Suma
    - Referinta OP
    - BatchID (pentru Netopia)
    """
    # Converteste data
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        transaction_date = date_obj.strftime('%Y-%m-%d')
    except:
        transaction_date = date_str

    # Extrage referinta (REF: XXXXXXXXX)
    ref_match = re.search(r'REF:\s*(\S+)', text)
    op_reference = ref_match.group(1) if ref_match else ''

    # Extrage suma - cauta numere mari cu virgula (ex: 744.58 sau 744,58)
    # In PDF-ul BT, suma apare in coloana Credit pentru incasari
    amount = 0.0

    # Pattern pentru suma: numar cu punct sau virgula ca separator zecimal
    # Suma apare de obicei la sfarsitul descrierii sau dupa un spatiu mare
    amount_patterns = [
        r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*$',  # La sfarsitul textului
        r'(\d+[.,]\d{2})\s*$',  # Numar simplu la sfarsit
    ]

    for pattern in amount_patterns:
        amount_match = re.search(pattern, text)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '.')
            # Daca are mai multe puncte, elimina-le pe cele de mii
            if amount_str.count('.') > 1:
                parts = amount_str.split('.')
                amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
            try:
                amount = float(amount_str)
                break
            except:
                pass

    # Daca nu am gasit suma in text, incearca sa o extragi din context
    if amount == 0:
        # Cauta pattern-uri specifice pentru sume
        sum_match = re.search(r'[\s;](\d+[.,]\d{2})[\s;]', text)
        if sum_match:
            amount_str = sum_match.group(1).replace(',', '.')
            try:
                amount = float(amount_str)
            except:
                pass

    # Determina sursa
    source = determine_source(text)

    # Daca nu e o sursa de interes, ignora
    if not source:
        return None

    # Extrage BatchID pentru Netopia
    batch_id = None
    if source == 'Netopia':
        batch_match = re.search(r'BATCHID\s*(\d+)', text, re.IGNORECASE)
        if batch_match:
            batch_id = batch_match.group(1)

    return {
        'transaction_date': transaction_date,
        'amount': amount,
        'source': source,
        'op_reference': op_reference,
        'batch_id': batch_id,
        'details': text[:500],  # Primele 500 caractere pentru referinta
        'transaction_type': 'credit'
    }


def determine_source(text: str) -> Optional[str]:
    """
    Determina sursa tranzactiei din textul descriptiv.
    """
    text_upper = text.upper()

    if 'GLS' in text_upper or 'GENERAL LOGISTICS' in text_upper:
        return 'GLS'

    if 'DELIVERY SOLUTIONS' in text_upper or 'SAMEDAY' in text_upper:
        return 'Sameday'

    if 'NETOPIA' in text_upper or 'BATCHID' in text_upper:
        return 'Netopia'

    if 'EMAG' in text_upper:
        return 'eMag'

    # Nu e o sursa de interes pentru reconciliere
    return None


def save_pdf_transactions_to_supabase(transactions: List[Dict], file_name: str = None) -> Dict:
    """
    Salveaza tranzactiile din PDF in Supabase.
    Ignora duplicatele (verificare dupa op_reference).

    Args:
        transactions: Lista de tranzactii parsate
        file_name: Numele fisierului sursa (optional)

    Returns:
        Dict cu statistici (inserted, skipped, errors)
    """
    from .supabase_client import get_client

    stats = {
        'processed': len(transactions),
        'inserted': 0,
        'skipped': 0,
        'errors': []
    }

    client = get_client()
    if not client:
        stats['errors'].append("Nu s-a putut conecta la Supabase")
        return stats

    # Obtine referintele existente pentru a evita duplicatele
    try:
        existing = client.table('bank_transactions').select('op_reference').execute()
        existing_refs = {row['op_reference'] for row in existing.data if row.get('op_reference')}
    except Exception as e:
        stats['errors'].append(f"Eroare la citirea tranzactiilor existente: {e}")
        existing_refs = set()

    for trans in transactions:
        op_ref = trans.get('op_reference', '')

        # Verifica duplicat
        if op_ref and op_ref in existing_refs:
            stats['skipped'] += 1
            continue

        # Ignora tranzactiile fara suma
        if not trans.get('amount') or trans['amount'] == 0:
            stats['skipped'] += 1
            continue

        try:
            data = {
                'transaction_date': trans.get('transaction_date'),
                'amount': str(trans.get('amount', 0)),
                'source': trans.get('source', ''),
                'op_reference': op_ref,
                'batch_id': trans.get('batch_id'),
                'details': trans.get('details', ''),
                'transaction_type': trans.get('transaction_type', 'credit'),
                'file_name': file_name,
                'synced_at': datetime.now().isoformat()
            }

            result = client.table('bank_transactions').insert(data).execute()

            if result.data:
                stats['inserted'] += 1
                existing_refs.add(op_ref)  # Adauga la set pentru a evita duplicate in acelasi batch

        except Exception as e:
            stats['errors'].append(f"Eroare la inserare {op_ref}: {str(e)}")

    return stats


def test_pdf_parser(pdf_path: str):
    """
    Functie de test pentru parser.
    """
    print(f"Parsare PDF: {pdf_path}")
    print("-" * 50)

    transactions = parse_bt_pdf_extract(pdf_path)

    print(f"Total tranzactii gasite: {len(transactions)}")
    print()

    for i, trans in enumerate(transactions, 1):
        print(f"{i}. {trans['transaction_date']} | {trans['source']} | {trans['amount']:.2f} RON | REF: {trans['op_reference']}")
        if trans.get('batch_id'):
            print(f"   BatchID: {trans['batch_id']}")

    return transactions


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_pdf_parser(sys.argv[1])
    else:
        print("Usage: python pdf_parser.py <path_to_pdf>")
