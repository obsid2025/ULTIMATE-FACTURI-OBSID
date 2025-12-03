"""
Netopia API Integration for OBSID Facturi
Descarca rapoartele de decontare si parseaza tranzactiile
"""

import os
import csv
import re
import zipfile
import requests
from io import StringIO, BytesIO
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Netopia API config
NETOPIA_API_KEY = os.getenv('NETOPIA_API_KEY', '')
NETOPIA_REPORT_URL = "https://admin.netopia-payments.com/api/report/{batch_id}/download"


def set_netopia_api_key(api_key: str):
    """Seteaza API key-ul Netopia."""
    global NETOPIA_API_KEY
    NETOPIA_API_KEY = api_key


def download_netopia_report(batch_id: str, api_key: str = None) -> Optional[bytes]:
    """
    Descarca raportul Netopia pentru un BatchId.

    Args:
        batch_id: ID-ul batch-ului de descarcat
        api_key: API key Netopia (optional, foloseste env var daca nu e specificat)

    Returns:
        Continutul raportului ca bytes sau None daca eroare
    """
    key = api_key or NETOPIA_API_KEY
    if not key:
        raise ValueError("Netopia API key nu este configurat")

    url = NETOPIA_REPORT_URL.format(batch_id=batch_id)
    headers = {
        'Authorization': key
    }

    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        return response.content
    except requests.exceptions.HTTPError as e:
        print(f"Netopia API HTTP Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Netopia API Request Error: {e}")
        return None


def parse_netopia_report(report_content: bytes) -> List[Dict]:
    """
    Parseaza raportul Netopia (ZIP cu CSV inauntru) si extrage tranzactiile.

    Args:
        report_content: Continutul raportului ca bytes (ZIP file)

    Returns:
        Lista de tranzactii ca dict-uri
    """
    transactions = []
    csv_content = None

    # Raportul vine ca ZIP - trebuie extras CSV-ul
    try:
        with zipfile.ZipFile(BytesIO(report_content), 'r') as zip_file:
            # Gaseste fisierul CSV in ZIP
            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
            if csv_files:
                csv_content = zip_file.read(csv_files[0]).decode('utf-8', errors='ignore')
    except zipfile.BadZipFile:
        # Nu e ZIP, poate e direct CSV
        csv_content = report_content.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Eroare la extragere ZIP: {e}")
        # Incearca direct ca text
        csv_content = report_content.decode('utf-8', errors='ignore')

    if not csv_content:
        return transactions

    # Parseaza CSV-ul
    try:
        # Detecteaza delimitatorul
        if '\t' in csv_content[:1000]:
            delimiter = '\t'
        elif ';' in csv_content[:1000]:
            delimiter = ';'
        else:
            delimiter = ','

        reader = csv.DictReader(StringIO(csv_content), delimiter=delimiter)

        for row in reader:
            transaction = parse_netopia_row(row)
            if transaction:
                transactions.append(transaction)

    except Exception as csv_error:
        # Daca CSV nu merge, incearca Excel (pentru cazuri exceptionale)
        try:
            import pandas as pd
            df = pd.read_excel(BytesIO(report_content))

            for _, row in df.iterrows():
                transaction = parse_netopia_row(row.to_dict())
                if transaction:
                    transactions.append(transaction)

        except Exception as excel_error:
            print(f"Nu s-a putut parsa raportul: CSV error: {csv_error}, Excel error: {excel_error}")

    return transactions


def parse_netopia_row(row: Dict) -> Optional[Dict]:
    """
    Parseaza un rand din raportul Netopia.

    Coloane din CSV-ul Netopia:
    - # (numar rand)
    - Comerciant
    - Id (ID tranzactie Netopia)
    - Data platii (data tranzactiei)
    - Data operatiei
    - Procesat (suma procesata)
    - Creditat (suma creditata)
    - Comision (taxa Netopia)
    - TVA
    - Moneda
    - Descriere (contine referinta comanda)
    """
    # Normalizeaza cheile (lowercase, fara spatii)
    normalized = {}
    for key, value in row.items():
        if key:
            norm_key = str(key).lower().strip().replace(' ', '_')
            normalized[norm_key] = value

    # Cauta campurile relevante
    transaction = {}

    # ID tranzactie - prioritate pentru 'id' (coloana Netopia)
    for key in ['id', 'transaction_id', 'tranzactie', 'ntpid', 'ntp_id']:
        if key in normalized and normalized[key]:
            transaction['transaction_id'] = str(normalized[key]).strip()
            break

    # Data - prioritate pentru 'data_platii' (coloana Netopia)
    for key in ['data_platii', 'data_operatiei', 'date', 'data', 'transaction_date', 'data_tranzactie', 'created']:
        if key in normalized and normalized[key]:
            transaction['date'] = str(normalized[key]).strip()
            break

    # Suma - prioritate pentru 'procesat' (coloana Netopia)
    for key in ['procesat', 'creditat', 'amount', 'suma', 'valoare', 'total', 'sum']:
        if key in normalized and normalized[key]:
            try:
                amount_str = str(normalized[key]).replace(',', '.').replace(' ', '')
                amount_str = ''.join(c for c in amount_str if c.isdigit() or c == '.' or c == '-')
                if amount_str:
                    transaction['amount'] = float(amount_str)
            except:
                pass
            break

    # Comision - exact 'comision' in Netopia
    for key in ['comision', 'fee', 'commission', 'taxa']:
        if key in normalized and normalized[key]:
            try:
                fee_str = str(normalized[key]).replace(',', '.').replace(' ', '')
                fee_str = ''.join(c for c in fee_str if c.isdigit() or c == '.' or c == '-')
                if fee_str:
                    transaction['fee'] = float(fee_str)
                else:
                    transaction['fee'] = 0
            except:
                transaction['fee'] = 0
            break

    # Order ID / Referinta - din 'descriere' (Netopia pune referinta acolo)
    for key in ['descriere', 'description', 'order_id', 'orderid', 'referinta', 'reference', 'comanda']:
        if key in normalized and normalized[key]:
            desc = str(normalized[key]).strip()
            # Extrage numarul comenzii din descriere (ex: "Comanda #12345" sau "Order 12345")
            order_match = re.search(r'(?:comanda|order|#)\s*#?(\d+)', desc, re.IGNORECASE)
            if order_match:
                transaction['order_id'] = order_match.group(1)
            else:
                transaction['order_id'] = desc
            break

    # Status
    for key in ['status', 'stare']:
        if key in normalized and normalized[key]:
            transaction['status'] = str(normalized[key]).strip()
            break

    # Moneda
    for key in ['moneda', 'currency']:
        if key in normalized and normalized[key]:
            transaction['currency'] = str(normalized[key]).strip()
            break

    # Suma neta (dupa comision)
    if 'amount' in transaction:
        fee = transaction.get('fee', 0)
        transaction['net_amount'] = transaction['amount'] - fee

    # Extrage luna din data pentru clasificare
    if 'date' in transaction:
        transaction['report_month'] = extract_month_from_date(transaction['date'])

    # Returneaza doar daca avem date esentiale
    if 'amount' in transaction or 'transaction_id' in transaction:
        transaction['source'] = 'Netopia'
        return transaction

    return None


def extract_month_from_date(date_str: str) -> Optional[str]:
    """
    Extrage luna din data in format YYYY-MM.

    Args:
        date_str: Data in diferite formate (DD.MM.YYYY, YYYY-MM-DD, etc.)

    Returns:
        Luna in format YYYY-MM sau None
    """
    if not date_str:
        return None

    # Incearca diferite formate de data
    formats = [
        '%d.%m.%Y',      # 15.11.2024
        '%d/%m/%Y',      # 15/11/2024
        '%Y-%m-%d',      # 2024-11-15
        '%d-%m-%Y',      # 15-11-2024
        '%Y/%m/%d',      # 2024/11/15
        '%d.%m.%Y %H:%M',  # 15.11.2024 14:30
        '%d.%m.%Y %H:%M:%S',  # 15.11.2024 14:30:00
        '%Y-%m-%d %H:%M:%S',  # 2024-11-15 14:30:00
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m')
        except ValueError:
            continue

    # Incearca sa extraga manual YYYY-MM
    match = re.search(r'(\d{4})[/-](\d{2})', date_str)
    if match:
        return f"{match.group(1)}-{match.group(2)}"

    match = re.search(r'(\d{2})[./](\d{2})[./](\d{4})', date_str)
    if match:
        return f"{match.group(3)}-{match.group(2)}"

    return None


def sync_netopia_batch(batch_id: str, api_key: str = None) -> Dict:
    """
    Sincronizeaza un batch Netopia complet.

    Args:
        batch_id: ID-ul batch-ului
        api_key: API key (optional)

    Returns:
        Dict cu statistici: transactions, total_amount, etc.
    """
    result = {
        'batch_id': batch_id,
        'success': False,
        'transactions': [],
        'count': 0,
        'total_amount': 0,
        'total_fees': 0,
        'net_amount': 0,
        'error': None
    }

    # Descarca raportul
    report_content = download_netopia_report(batch_id, api_key)
    if not report_content:
        result['error'] = 'Nu s-a putut descarca raportul'
        return result

    # Parseaza tranzactiile
    transactions = parse_netopia_report(report_content)
    if not transactions:
        result['error'] = 'Nu s-au gasit tranzactii in raport'
        return result

    result['success'] = True
    result['transactions'] = transactions
    result['count'] = len(transactions)
    result['total_amount'] = sum(t.get('amount', 0) for t in transactions)
    result['total_fees'] = sum(t.get('fee', 0) for t in transactions)
    result['net_amount'] = sum(t.get('net_amount', 0) for t in transactions)

    return result


def save_netopia_transactions_to_supabase(transactions: List[Dict], batch_id: str, report_month: str = None) -> Dict:
    """
    Salveaza tranzactiile Netopia in Supabase.

    Args:
        transactions: Lista de tranzactii
        batch_id: ID-ul batch-ului
        report_month: Luna raportului in format YYYY-MM (pentru clasificare)

    Returns:
        Dict cu statistici de import
    """
    from .supabase_client import get_client

    stats = {
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }

    client = get_client()
    if not client:
        stats['errors'].append('Nu s-a putut conecta la Supabase')
        return stats

    for tx in transactions:
        try:
            # Determina luna din tranzactie sau foloseste cea din parametru
            tx_month = tx.get('report_month') or report_month

            data = {
                'batch_id': batch_id,
                'transaction_id': tx.get('transaction_id', ''),
                'transaction_date': tx.get('date', ''),
                'amount': tx.get('amount', 0),
                'fee': tx.get('fee', 0),
                'net_amount': tx.get('net_amount', 0),
                'order_id': tx.get('order_id', ''),
                'status': tx.get('status', ''),
                'currency': tx.get('currency', 'RON'),
                'report_month': tx_month,
                'source': 'Netopia',
                'synced_at': datetime.now().isoformat()
            }

            # Upsert pe transaction_id
            result = client.table('netopia_transactions').upsert(
                data,
                on_conflict='transaction_id'
            ).execute()

            if result.data:
                stats['inserted'] += 1

        except Exception as e:
            stats['errors'].append(f"Eroare la tranzactia {tx.get('transaction_id')}: {str(e)}")

    return stats


def save_netopia_batch_to_supabase(batch_info: Dict) -> bool:
    """
    Salveaza informatiile despre un batch Netopia in Supabase.

    Args:
        batch_info: Dict cu batch_id, report_id, report_month, etc.

    Returns:
        True daca salvarea a reusit
    """
    from .supabase_client import get_client

    client = get_client()
    if not client:
        return False

    try:
        data = {
            'batch_id': batch_info.get('batch_id', ''),
            'report_id': batch_info.get('report_id', ''),
            'email_date': batch_info.get('date', ''),
            'email_subject': batch_info.get('subject', ''),
            'report_month': batch_info.get('report_month', ''),
            'transactions_count': batch_info.get('count', 0),
            'total_amount': batch_info.get('total_amount', 0),
            'total_fees': batch_info.get('total_fees', 0),
            'net_amount': batch_info.get('net_amount', 0),
            'synced_at': datetime.now().isoformat()
        }

        # Upsert pe batch_id
        result = client.table('netopia_batches').upsert(
            data,
            on_conflict='batch_id'
        ).execute()

        return bool(result.data)

    except Exception as e:
        print(f"Eroare la salvare batch: {e}")
        return False


def is_batch_already_synced(batch_id: str) -> bool:
    """
    Verifica daca un batch a fost deja sincronizat.

    Args:
        batch_id: ID-ul batch-ului de verificat

    Returns:
        True daca batch-ul exista deja in Supabase
    """
    from .supabase_client import get_client

    client = get_client()
    if not client:
        return False

    try:
        result = client.table('netopia_batches').select('id').eq('batch_id', batch_id).execute()
        return bool(result.data and len(result.data) > 0)
    except Exception:
        return False


def get_synced_batches_for_month(report_month: str) -> List[str]:
    """
    Obtine lista de batch-uri deja sincronizate pentru o luna.

    Args:
        report_month: Luna in format YYYY-MM

    Returns:
        Lista de batch_id-uri sincronizate
    """
    from .supabase_client import get_client

    client = get_client()
    if not client:
        return []

    try:
        result = client.table('netopia_batches').select('batch_id').eq('report_month', report_month).execute()
        return [r['batch_id'] for r in result.data] if result.data else []
    except Exception:
        return []


def test_netopia_connection(api_key: str = None) -> bool:
    """
    Testeaza conexiunea la Netopia API.
    Nu putem testa fara un batch_id valid, deci doar verificam API key-ul.
    """
    key = api_key or NETOPIA_API_KEY
    return bool(key and len(key) > 10)
