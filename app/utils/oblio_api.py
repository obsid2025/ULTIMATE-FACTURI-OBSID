"""
Oblio API integration pentru sincronizare facturi
"""

import requests
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date

# Oblio credentials
OBLIO_EMAIL = os.getenv('OBLIO_EMAIL', 'obsidparfume@gmail.com')
OBLIO_SECRET = os.getenv('OBLIO_SECRET', '6c5b7d83148b5324d548f68ed7f4da207402ea38')
OBLIO_CIF = os.getenv('OBLIO_CIF', '52168342')

OBLIO_API_BASE = 'https://www.oblio.eu/api'

_access_token: Optional[str] = None
_token_expires: Optional[datetime] = None


def _get_access_token() -> str:
    """Get or refresh Oblio access token."""
    global _access_token, _token_expires

    # Check if token is still valid (with 5 min buffer)
    if _access_token and _token_expires and datetime.now() < _token_expires:
        return _access_token

    # Get new token
    response = requests.post(
        f'{OBLIO_API_BASE}/authorize/token',
        data={
            'client_id': OBLIO_EMAIL,
            'client_secret': OBLIO_SECRET,
            'grant_type': 'client_credentials'
        }
    )

    if response.status_code != 200:
        raise Exception(f"Oblio auth failed: {response.text}")

    data = response.json()
    _access_token = data['access_token']
    # Token expires in 1 hour, we'll refresh after 55 minutes
    from datetime import timedelta
    _token_expires = datetime.now() + timedelta(minutes=55)

    return _access_token


def _get_headers() -> Dict:
    """Get authorization headers."""
    return {'Authorization': f'Bearer {_get_access_token()}'}


def get_invoices(
    issued_after: Optional[date] = None,
    issued_before: Optional[date] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[Dict], int]:
    """
    Get invoices from Oblio API.

    Returns:
        Tuple of (invoices list, total count)
    """
    params = {
        'cif': OBLIO_CIF,
        'limitPerPage': limit,
        'offset': offset
    }

    if issued_after:
        params['issuedAfter'] = issued_after.strftime('%Y-%m-%d')
    if issued_before:
        params['issuedBefore'] = issued_before.strftime('%Y-%m-%d')

    response = requests.get(
        f'{OBLIO_API_BASE}/docs/invoice/list',
        headers=_get_headers(),
        params=params
    )

    if response.status_code != 200:
        raise Exception(f"Oblio API error: {response.text}")

    data = response.json()
    invoices = data.get('data', [])

    return invoices, len(invoices)


def get_all_invoices(
    issued_after: Optional[date] = None,
    issued_before: Optional[date] = None
) -> List[Dict]:
    """Get all invoices with pagination."""
    all_invoices = []
    offset = 0
    limit = 100

    while True:
        invoices, count = get_invoices(
            issued_after=issued_after,
            issued_before=issued_before,
            limit=limit,
            offset=offset
        )

        all_invoices.extend(invoices)

        if count < limit:
            break

        offset += limit

    return all_invoices


def parse_invoice_type(invoice: Dict) -> str:
    """Determine invoice type from API response."""
    if invoice.get('storno') == '1':
        return 'Storno'
    elif invoice.get('stornoed') == '1':
        return 'Stornata'
    else:
        return 'Normala'


def transform_invoice_for_db(invoice: Dict) -> Dict:
    """Transform Oblio API invoice to database format."""
    client = invoice.get('client', {})

    return {
        'oblio_id': invoice.get('id'),
        'series_name': invoice.get('seriesName'),
        'invoice_number': invoice.get('number'),
        'issue_date': invoice.get('issueDate'),
        'due_date': invoice.get('dueDate'),
        'currency': invoice.get('currency', 'RON'),
        'total': float(invoice.get('total', 0)),
        'invoice_type': parse_invoice_type(invoice),
        'is_canceled': invoice.get('canceled') == '1',
        'is_collected': invoice.get('collected') == '1',
        'client_name': client.get('name'),
        'client_cif': client.get('cif'),
        'client_address': client.get('address'),
        'client_city': client.get('city'),
        'client_state': client.get('state'),
        'client_country': client.get('country', 'Romania'),
        'client_phone': client.get('phone'),
        'client_email': client.get('email'),
        'pdf_link': invoice.get('link'),
        'einvoice_link': invoice.get('einvoice')
    }


def get_series_info() -> List[Dict]:
    """Get available invoice series."""
    response = requests.get(
        f'{OBLIO_API_BASE}/nomenclature/series',
        headers=_get_headers(),
        params={'cif': OBLIO_CIF}
    )

    if response.status_code != 200:
        raise Exception(f"Oblio API error: {response.text}")

    return response.json().get('data', [])


def test_connection() -> bool:
    """Test Oblio API connection."""
    try:
        _get_access_token()
        return True
    except Exception as e:
        print(f"Oblio connection error: {e}")
        return False
