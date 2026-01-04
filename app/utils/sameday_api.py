"""
Sameday Courier API Integration for OBSID Facturi
Descarca coletele livrate si sumele COD direct din Sameday API
"""

import os
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Sameday API config
SAMEDAY_API_URL = "https://api.sameday.ro"
SAMEDAY_USERNAME = os.getenv('SAMEDAY_USERNAME', '')
SAMEDAY_PASSWORD = os.getenv('SAMEDAY_PASSWORD', '')

# Token cache
_token_cache = {
    'token': None,
    'expires_at': None
}


def set_sameday_credentials(username: str, password: str):
    """Seteaza credentialele Sameday."""
    global SAMEDAY_USERNAME, SAMEDAY_PASSWORD
    SAMEDAY_USERNAME = username
    SAMEDAY_PASSWORD = password
    # Clear token cache when credentials change
    _token_cache['token'] = None
    _token_cache['expires_at'] = None


def _authenticate(username: str = None, password: str = None) -> Optional[str]:
    """
    Autentificare la Sameday API si obtinere token.

    Args:
        username: Username Sameday (optional, foloseste env var)
        password: Password Sameday (optional, foloseste env var)

    Returns:
        Token string sau None daca eroare
    """
    user = username or SAMEDAY_USERNAME
    pwd = password or SAMEDAY_PASSWORD

    if not all([user, pwd]):
        raise ValueError("Sameday credentials not configured")

    # Check cache first
    if _token_cache['token'] and _token_cache['expires_at']:
        if datetime.now() < _token_cache['expires_at']:
            return _token_cache['token']

    try:
        response = requests.post(
            f"{SAMEDAY_API_URL}/api/authenticate",
            headers={
                'X-AUTH-USERNAME': user,
                'X-AUTH-PASSWORD': pwd
            },
            params={'remember_me': 1},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        token = data.get('token')
        expire_str = data.get('expire_at')  # Format: "2025-12-04 08:39"

        if token:
            _token_cache['token'] = token
            if expire_str:
                try:
                    _token_cache['expires_at'] = datetime.strptime(expire_str, '%Y-%m-%d %H:%M')
                except:
                    _token_cache['expires_at'] = datetime.now() + timedelta(hours=11)
            return token

    except requests.exceptions.RequestException as e:
        print(f"Sameday Auth Error: {e}")
        return None

    return None


def _get_status_sync(token: str, start_timestamp: int, end_timestamp: int,
                     page: int = 1, per_page: int = 500) -> Tuple[List[Dict], int]:
    """
    Obtine schimbarile de status intr-un interval de timp.

    IMPORTANT: Intervalul maxim permis este 7200 secunde (2 ore)!

    Args:
        token: Token de autentificare
        start_timestamp: Timestamp start (Unix seconds)
        end_timestamp: Timestamp end (Unix seconds)
        page: Pagina curenta
        per_page: Rezultate per pagina (max 500)

    Returns:
        Tuple (lista de statusuri, total pages)
    """
    try:
        response = requests.get(
            f"{SAMEDAY_API_URL}/api/client/status-sync",
            headers={'X-AUTH-TOKEN': token},
            params={
                'startTimestamp': start_timestamp,
                'endTimestamp': end_timestamp,
                'page': page,
                'countPerPage': per_page
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        items = data.get('data', [])
        current_page = data.get('currentPage', 1)
        per_page_actual = data.get('perPage', per_page)

        # Estimate total pages (API doesn't return total)
        total_pages = 1 if len(items) < per_page_actual else page + 1

        return items, total_pages

    except requests.exceptions.RequestException as e:
        print(f"Sameday Status Sync Error: {e}")
        return [], 0


def _get_awb_details(token: str, awb_number: str) -> Optional[Dict]:
    """
    Obtine detaliile complete ale unui AWB.

    Args:
        token: Token de autentificare
        awb_number: Numarul AWB (fara sufixul de colet)

    Returns:
        Dict cu detalii expeditie sau None
    """
    # Remove parcel suffix if present (e.g., 1ONBLN435950669001 -> 1ONBLN435950669)
    if len(awb_number) > 15 and awb_number[-3:].isdigit():
        awb_number = awb_number[:-3]

    try:
        response = requests.get(
            f"{SAMEDAY_API_URL}/api/client/awb/{awb_number}/status",
            headers={'X-AUTH-TOKEN': token},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Sameday AWB Details Error for {awb_number}: {e}")
        return None


def get_sameday_deliveries_with_cod(days_back: int = 30, username: str = None,
                                     password: str = None) -> List[Dict]:
    """
    Obtine lista de colete livrate cu ramburs in ultimele N zile.

    Foloseste status-sync pentru a gasi coletele cu status
    "Ramburs transferat" (statusId=3) sau "Livrata cu succes" (statusId=9).

    Args:
        days_back: Cate zile in urma sa caute
        username: Username Sameday (optional)
        password: Password Sameday (optional)

    Returns:
        Lista de colete livrate cu COD si detalii
    """
    token = _authenticate(username, password)
    if not token:
        raise ValueError("Nu s-a putut obtine token Sameday")

    delivered = []
    seen_awbs = set()
    now = datetime.now()

    # Scan in 2-hour intervals (API limit)
    interval_seconds = 7000  # Just under 2 hours

    # Calculate total intervals needed
    total_seconds = days_back * 24 * 3600
    intervals = (total_seconds // interval_seconds) + 1

    print(f"Scanare {intervals} intervale de 2 ore pentru {days_back} zile...")

    for i in range(intervals):
        end_time = int((now - timedelta(seconds=i * interval_seconds)).timestamp())
        start_time = end_time - interval_seconds

        # Get all pages for this interval
        page = 1
        while True:
            items, total_pages = _get_status_sync(token, start_time, end_time, page)

            for item in items:
                # Check for delivery-related statuses
                status_id = item.get('statusId')
                awb = item.get('parcelAwbNumber', '')

                # Remove parcel suffix to get base AWB
                base_awb = awb[:-3] if len(awb) > 15 and awb[-3:].isdigit() else awb

                if base_awb and base_awb not in seen_awbs:
                    # Status 3 = "Ramburs transferat", Status 9 = "Livrata cu succes"
                    if status_id in [3, 9]:
                        seen_awbs.add(base_awb)

                        # Get full AWB details
                        details = _get_awb_details(token, base_awb)
                        if details:
                            summary = details.get('expeditionSummary', {})
                            cod_amount = summary.get('cashOnDelivery', 0)

                            # Only include if has COD
                            if cod_amount and cod_amount > 0:
                                delivery_date = summary.get('deliveredAt', '')
                                if delivery_date:
                                    try:
                                        dt = datetime.fromisoformat(delivery_date.replace('+02:00', '').replace('+03:00', ''))
                                        delivery_date_str = dt.strftime('%Y-%m-%d')
                                    except:
                                        delivery_date_str = delivery_date[:10] if delivery_date else ''
                                else:
                                    delivery_date_str = ''

                                delivered.append({
                                    'awb_number': base_awb,
                                    'cod_amount': cod_amount,
                                    'cod_currency': 'RON',
                                    'is_delivered': summary.get('delivered', False),
                                    'delivery_date': delivery_date_str,
                                    'delivery_attempts': summary.get('deliveryAttempts', 0),
                                    'awb_weight': summary.get('awbWeight', 0),
                                    'status': details.get('expeditionStatus', {}).get('status', ''),
                                    'status_label': details.get('expeditionStatus', {}).get('statusLabel', ''),
                                    'county': details.get('expeditionStatus', {}).get('county', '')
                                })

            # Check if more pages
            if len(items) < 500 or page >= total_pages:
                break
            page += 1

    # Sort by delivery date (newest first)
    delivered.sort(key=lambda x: x.get('delivery_date', ''), reverse=True)

    return delivered


def get_cod_summary_by_date(days_back: int = 30, username: str = None,
                            password: str = None) -> Dict:
    """
    Obtine sumar COD grupat pe data livrarii.

    Returns:
        Dict cu date si sume totale COD
    """
    delivered = get_sameday_deliveries_with_cod(days_back, username, password)

    summary = {}
    for parcel in delivered:
        date_str = parcel.get('delivery_date', 'Unknown')
        if date_str not in summary:
            summary[date_str] = {
                'date': date_str,
                'parcels': [],
                'total_cod': 0,
                'count': 0
            }
        summary[date_str]['parcels'].append(parcel)
        summary[date_str]['total_cod'] += parcel.get('cod_amount', 0)
        summary[date_str]['count'] += 1

    return summary


def get_existing_sameday_parcels() -> set:
    """
    Obtine lista de AWB-uri Sameday deja existente in Supabase.
    Folosit pentru a evita re-descarcarea datelor existente.
    """
    from .supabase_client import get_client

    client = get_client()
    if not client:
        return set()

    try:
        result = client.table("sameday_parcels").select("awb_number").execute()
        return {row['awb_number'] for row in result.data}
    except Exception as e:
        print(f"Eroare la citirea AWB-urilor Sameday existente: {e}")
        return set()


def save_sameday_parcels_to_supabase(parcels: List[Dict], sync_month: str = None) -> Dict:
    """
    Salveaza coletele Sameday in Supabase.
    Sare peste coletele care exista deja (pe baza awb_number).

    Args:
        parcels: Lista de colete
        sync_month: Luna sincronizarii (YYYY-MM)

    Returns:
        Dict cu statistici (inserted, skipped, errors)
    """
    from .supabase_client import get_client

    stats = {
        'inserted': 0,
        'skipped': 0,
        'errors': []
    }

    client = get_client()
    if not client:
        stats['errors'].append('Nu s-a putut conecta la Supabase')
        return stats

    # Obtine AWB-urile existente pentru a le sari
    existing = get_existing_sameday_parcels()

    for parcel in parcels:
        awb_number = parcel.get('awb_number', '')

        # Sari peste AWB-urile existente
        if awb_number in existing:
            stats['skipped'] += 1
            continue

        try:
            data = {
                'awb_number': awb_number,
                'cod_amount': parcel.get('cod_amount', 0),
                'cod_currency': parcel.get('cod_currency', 'RON'),
                'is_delivered': parcel.get('is_delivered', False),
                'delivery_date': parcel.get('delivery_date', ''),
                'county': parcel.get('county', ''),
                'status': parcel.get('status', ''),
                'sync_month': sync_month or datetime.now().strftime('%Y-%m'),
                'source': 'Sameday',
                'synced_at': datetime.now().isoformat()
            }

            result = client.table('sameday_parcels').insert(data).execute()

            if result.data:
                stats['inserted'] += 1

        except Exception as e:
            stats['errors'].append(f"Eroare la AWB {awb_number}: {str(e)}")

    return stats


def test_sameday_connection(username: str = None, password: str = None) -> bool:
    """Testeaza conexiunea la Sameday API."""
    try:
        token = _authenticate(username, password)
        return bool(token)
    except Exception as e:
        print(f"Sameday connection test failed: {e}")
        return False


def is_sameday_configured() -> bool:
    """Verifica daca Sameday e configurat."""
    return bool(SAMEDAY_USERNAME and SAMEDAY_PASSWORD)
