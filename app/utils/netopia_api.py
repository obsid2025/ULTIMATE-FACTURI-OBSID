"""
Netopia API Integration for OBSID Facturi
Descarca rapoartele de decontare si parseaza tranzactiile
"""

import os
import csv
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
    Parseaza raportul Netopia (CSV/Excel) si extrage tranzactiile.

    Args:
        report_content: Continutul raportului ca bytes

    Returns:
        Lista de tranzactii ca dict-uri
    """
    transactions = []

    # Incearca sa determine formatul (CSV sau Excel)
    try:
        # Incearca CSV mai intai
        content_str = report_content.decode('utf-8', errors='ignore')

        # Detecteaza delimitatorul
        if '\t' in content_str[:1000]:
            delimiter = '\t'
        elif ';' in content_str[:1000]:
            delimiter = ';'
        else:
            delimiter = ','

        reader = csv.DictReader(StringIO(content_str), delimiter=delimiter)

        for row in reader:
            transaction = parse_netopia_row(row)
            if transaction:
                transactions.append(transaction)

    except Exception as csv_error:
        # Daca CSV nu merge, incearca Excel
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

    Campuri asteptate (pot varia):
    - ID tranzactie / Transaction ID
    - Data / Date
    - Suma / Amount
    - Comision / Fee
    - Status
    - Order ID / Referinta
    """
    # Normalizeaza cheile (lowercase, fara spatii)
    normalized = {}
    for key, value in row.items():
        if key:
            norm_key = str(key).lower().strip().replace(' ', '_')
            normalized[norm_key] = value

    # Cauta campurile relevante
    transaction = {}

    # ID tranzactie
    for key in ['transaction_id', 'id', 'tranzactie', 'ntpid', 'ntp_id']:
        if key in normalized and normalized[key]:
            transaction['transaction_id'] = str(normalized[key]).strip()
            break

    # Data
    for key in ['date', 'data', 'transaction_date', 'data_tranzactie', 'created']:
        if key in normalized and normalized[key]:
            transaction['date'] = str(normalized[key]).strip()
            break

    # Suma
    for key in ['amount', 'suma', 'valoare', 'total', 'sum']:
        if key in normalized and normalized[key]:
            try:
                # Curata si converteste la float
                amount_str = str(normalized[key]).replace(',', '.').replace(' ', '')
                amount_str = ''.join(c for c in amount_str if c.isdigit() or c == '.' or c == '-')
                transaction['amount'] = float(amount_str)
            except:
                pass
            break

    # Comision
    for key in ['fee', 'comision', 'commission', 'taxa']:
        if key in normalized and normalized[key]:
            try:
                fee_str = str(normalized[key]).replace(',', '.').replace(' ', '')
                fee_str = ''.join(c for c in fee_str if c.isdigit() or c == '.' or c == '-')
                transaction['fee'] = float(fee_str)
            except:
                transaction['fee'] = 0
            break

    # Order ID / Referinta
    for key in ['order_id', 'orderid', 'referinta', 'reference', 'comanda']:
        if key in normalized and normalized[key]:
            transaction['order_id'] = str(normalized[key]).strip()
            break

    # Status
    for key in ['status', 'stare']:
        if key in normalized and normalized[key]:
            transaction['status'] = str(normalized[key]).strip()
            break

    # Suma neta (dupa comision)
    if 'amount' in transaction:
        fee = transaction.get('fee', 0)
        transaction['net_amount'] = transaction['amount'] - fee

    # Returneaza doar daca avem date esentiale
    if 'amount' in transaction or 'transaction_id' in transaction:
        transaction['source'] = 'Netopia'
        return transaction

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


def save_netopia_transactions_to_supabase(transactions: List[Dict], batch_id: str) -> Dict:
    """
    Salveaza tranzactiile Netopia in Supabase.

    Args:
        transactions: Lista de tranzactii
        batch_id: ID-ul batch-ului

    Returns:
        Dict cu statistici de import
    """
    from .supabase_client import get_client

    stats = {
        'inserted': 0,
        'updated': 0,
        'errors': []
    }

    client = get_client()
    if not client:
        stats['errors'].append('Nu s-a putut conecta la Supabase')
        return stats

    for tx in transactions:
        try:
            data = {
                'batch_id': batch_id,
                'transaction_id': tx.get('transaction_id', ''),
                'transaction_date': tx.get('date', ''),
                'amount': tx.get('amount', 0),
                'fee': tx.get('fee', 0),
                'net_amount': tx.get('net_amount', 0),
                'order_id': tx.get('order_id', ''),
                'status': tx.get('status', ''),
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


def test_netopia_connection(api_key: str = None) -> bool:
    """
    Testeaza conexiunea la Netopia API.
    Nu putem testa fara un batch_id valid, deci doar verificam API key-ul.
    """
    key = api_key or NETOPIA_API_KEY
    return bool(key and len(key) > 10)
