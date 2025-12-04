"""
GLS Romania API Integration for OBSID Facturi
Descarca coletele si statusurile direct din MyGLS API
"""

import os
import hashlib
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# GLS API config
GLS_API_URL = "https://api.mygls.ro/ParcelService.svc/json"
GLS_CLIENT_NUMBER = os.getenv('GLS_CLIENT_NUMBER', '')
GLS_USERNAME = os.getenv('GLS_USERNAME', '')
GLS_PASSWORD = os.getenv('GLS_PASSWORD', '')


def set_gls_credentials(client_number: str, username: str, password: str):
    """Seteaza credentialele GLS."""
    global GLS_CLIENT_NUMBER, GLS_USERNAME, GLS_PASSWORD
    GLS_CLIENT_NUMBER = client_number
    GLS_USERNAME = username
    GLS_PASSWORD = password


def _get_password_hash(password: str) -> List[int]:
    """Genereaza hash-ul SHA512 al parolei ca lista de bytes."""
    password_hash = hashlib.sha512(password.encode('utf-8')).digest()
    return list(password_hash)


def _to_wcf_date(dt: datetime) -> str:
    """Converteste datetime la format WCF JSON (/Date(milliseconds)/)."""
    return "/Date(%d)/" % int(dt.timestamp() * 1000)


def _from_wcf_date(wcf_date: str) -> Optional[datetime]:
    """Converteste format WCF JSON la datetime."""
    if not wcf_date:
        return None
    try:
        # Format: /Date(1762853951000+0100)/
        import re
        match = re.search(r'/Date\((\d+)', wcf_date)
        if match:
            timestamp_ms = int(match.group(1))
            return datetime.fromtimestamp(timestamp_ms / 1000)
    except Exception:
        pass
    return None


def get_gls_parcels(days_back: int = 30, username: str = None, password: str = None,
                    client_number: str = None) -> List[Dict]:
    """
    Obtine lista de colete GLS din ultimele N zile.

    Args:
        days_back: Cate zile in urma sa caute
        username: Username GLS (optional, foloseste env var)
        password: Password GLS (optional, foloseste env var)
        client_number: Client number GLS (optional, foloseste env var)

    Returns:
        Lista de colete cu detalii COD
    """
    user = username or GLS_USERNAME
    pwd = password or GLS_PASSWORD
    client = client_number or GLS_CLIENT_NUMBER

    if not all([user, pwd, client]):
        raise ValueError("GLS credentials not configured")

    date_from = datetime.now() - timedelta(days=days_back)
    date_to = datetime.now()

    payload = {
        "Username": user,
        "Password": _get_password_hash(pwd),
        "PrintDateFrom": _to_wcf_date(date_from),
        "PrintDateTo": _to_wcf_date(date_to),
    }

    try:
        response = requests.post(
            f"{GLS_API_URL}/GetParcelList",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        parcels = []
        for item in data.get("PrintDataInfoList", []):
            parcel_data = item.get("Parcel", {})
            delivery_addr = parcel_data.get("DeliveryAddress", {})

            parcel = {
                "parcel_number": str(item.get("ParcelNumber", "")),
                "cod_amount": parcel_data.get("CODAmount", 0) or 0,
                "cod_currency": parcel_data.get("CODCurrency", "RON"),
                "cod_reference": parcel_data.get("CODReference", ""),
                "client_reference": parcel_data.get("ClientReference", ""),
                "recipient_name": delivery_addr.get("Name", ""),
                "recipient_city": delivery_addr.get("City", ""),
                "recipient_phone": delivery_addr.get("ContactPhone", ""),
                "content": parcel_data.get("Content", ""),
            }
            parcels.append(parcel)

        return parcels

    except requests.exceptions.RequestException as e:
        print(f"GLS API Error: {e}")
        return []


def get_parcel_status(parcel_number: str, username: str = None, password: str = None) -> Dict:
    """
    Obtine statusul unui colet GLS.

    Args:
        parcel_number: Numarul coletului
        username: Username GLS (optional)
        password: Password GLS (optional)

    Returns:
        Dict cu statusuri si data livrarii
    """
    user = username or GLS_USERNAME
    pwd = password or GLS_PASSWORD

    if not all([user, pwd]):
        raise ValueError("GLS credentials not configured")

    payload = {
        "Username": user,
        "Password": _get_password_hash(pwd),
        "ParcelNumber": int(parcel_number),
        "ReturnPOD": False,
        "LanguageIsoCode": "RO"
    }

    try:
        response = requests.post(
            f"{GLS_API_URL}/GetParcelStatuses",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        result = {
            "parcel_number": str(data.get("ParcelNumber", "")),
            "client_reference": data.get("ClientReference", ""),
            "statuses": [],
            "is_delivered": False,
            "delivery_date": None
        }

        for status in data.get("ParcelStatusList", []):
            status_info = {
                "code": status.get("StatusCode", ""),
                "description": status.get("StatusDescription", ""),
                "date": _from_wcf_date(status.get("StatusDate", "")),
                "info": status.get("StatusInfo", ""),
                "depot": status.get("DepotCity", "")
            }
            result["statuses"].append(status_info)

            # Check if delivered (StatusCode 05)
            if status.get("StatusCode") == "05":
                result["is_delivered"] = True
                result["delivery_date"] = status_info["date"]

        return result

    except requests.exceptions.RequestException as e:
        print(f"GLS API Error: {e}")
        return {"parcel_number": parcel_number, "error": str(e)}


def get_delivered_parcels_with_cod(days_back: int = 30, username: str = None,
                                    password: str = None, client_number: str = None) -> List[Dict]:
    """
    Obtine lista de colete livrate cu ramburs in ultimele N zile.
    Aceasta este functia principala pentru reconciliere.

    Args:
        days_back: Cate zile in urma sa caute
        username, password, client_number: Credentiale GLS

    Returns:
        Lista de colete livrate cu COD, data livrarii si sume
    """
    # Get all parcels
    parcels = get_gls_parcels(days_back, username, password, client_number)

    user = username or GLS_USERNAME
    pwd = password or GLS_PASSWORD

    delivered = []
    for parcel in parcels:
        # Skip parcels without COD
        if not parcel.get("cod_amount"):
            continue

        # Get status for this parcel
        status = get_parcel_status(parcel["parcel_number"], user, pwd)

        if status.get("is_delivered"):
            parcel["is_delivered"] = True
            parcel["delivery_date"] = status.get("delivery_date")
            parcel["delivery_date_str"] = status["delivery_date"].strftime("%Y-%m-%d") if status.get("delivery_date") else ""
            delivered.append(parcel)

    return delivered


def get_cod_summary_by_date(days_back: int = 30, username: str = None,
                            password: str = None, client_number: str = None) -> Dict:
    """
    Obtine sumar COD grupat pe data livrarii.

    Returns:
        Dict cu date si sume totale COD
    """
    delivered = get_delivered_parcels_with_cod(days_back, username, password, client_number)

    summary = {}
    for parcel in delivered:
        date_str = parcel.get("delivery_date_str", "Unknown")
        if date_str not in summary:
            summary[date_str] = {
                "date": date_str,
                "parcels": [],
                "total_cod": 0,
                "count": 0
            }
        summary[date_str]["parcels"].append(parcel)
        summary[date_str]["total_cod"] += parcel.get("cod_amount", 0)
        summary[date_str]["count"] += 1

    return summary


def get_existing_gls_parcels() -> set:
    """
    Obtine lista de numere de colete GLS deja existente in Supabase.
    Folosit pentru a evita re-descarcarea datelor existente.
    """
    from .supabase_client import get_client

    client = get_client()
    if not client:
        return set()

    try:
        result = client.table("gls_parcels").select("parcel_number").execute()
        return {row['parcel_number'] for row in result.data}
    except Exception as e:
        print(f"Eroare la citirea coletelor GLS existente: {e}")
        return set()


def save_gls_parcels_to_supabase(parcels: List[Dict], sync_month: str = None) -> Dict:
    """
    Salveaza coletele GLS in Supabase.
    Sare peste coletele care exista deja (pe baza parcel_number).

    Args:
        parcels: Lista de colete
        sync_month: Luna sincronizarii (YYYY-MM)

    Returns:
        Dict cu statistici (inserted, skipped, errors)
    """
    from .supabase_client import get_client

    stats = {
        "inserted": 0,
        "skipped": 0,
        "errors": []
    }

    client = get_client()
    if not client:
        stats["errors"].append("Nu s-a putut conecta la Supabase")
        return stats

    # Obtine coletele existente pentru a le sari
    existing = get_existing_gls_parcels()

    for parcel in parcels:
        parcel_number = parcel.get("parcel_number", "")

        # Sari peste coletele existente
        if parcel_number in existing:
            stats["skipped"] += 1
            continue

        try:
            data = {
                "parcel_number": parcel_number,
                "cod_amount": parcel.get("cod_amount", 0),
                "cod_currency": parcel.get("cod_currency", "RON"),
                "cod_reference": parcel.get("cod_reference", ""),
                "client_reference": parcel.get("client_reference", ""),
                "recipient_name": parcel.get("recipient_name", ""),
                "recipient_city": parcel.get("recipient_city", ""),
                "is_delivered": parcel.get("is_delivered", False),
                "delivery_date": parcel.get("delivery_date_str", ""),
                "sync_month": sync_month or datetime.now().strftime("%Y-%m"),
                "source": "GLS",
                "synced_at": datetime.now().isoformat()
            }

            result = client.table("gls_parcels").insert(data).execute()

            if result.data:
                stats["inserted"] += 1

        except Exception as e:
            stats["errors"].append(f"Eroare la colet {parcel_number}: {str(e)}")

    return stats


def test_gls_connection(username: str = None, password: str = None,
                        client_number: str = None) -> bool:
    """Testeaza conexiunea la GLS API."""
    try:
        parcels = get_gls_parcels(days_back=1, username=username, password=password,
                                   client_number=client_number)
        return True
    except Exception as e:
        print(f"GLS connection test failed: {e}")
        return False


def is_gls_configured() -> bool:
    """Verifica daca GLS e configurat."""
    return bool(GLS_USERNAME and GLS_PASSWORD and GLS_CLIENT_NUMBER)
