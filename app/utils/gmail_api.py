"""
Gmail API Integration for OBSID Facturi
Extrage automat BatchId-urile Netopia din email-uri
"""

import os
import re
import pickle
import base64
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes necesare - doar citire email
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Paths
CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials')
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'gmail_credentials.json')
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, 'gmail_token.pickle')


def get_gmail_service():
    """
    Autentifica si returneaza serviciul Gmail API.
    La prima rulare, va deschide browser-ul pentru autorizare.
    """
    creds = None

    # Verifica daca avem token salvat
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # Daca nu avem credentiale valide, autentifica
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Fisierul credentials nu exista: {CREDENTIALS_FILE}\n"
                    "Descarca credentials.json din Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Salveaza token-ul pentru viitor
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def is_gmail_authenticated() -> bool:
    """Verifica daca Gmail API e autentificat."""
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
        return creds and creds.valid
    except:
        return False


def search_netopia_emails(
    service,
    days_back: int = 30,
    max_results: int = 100
) -> List[Dict]:
    """
    Cauta email-uri de la Netopia cu rapoarte de decontare.

    Args:
        service: Gmail API service
        days_back: Cate zile in urma sa caute
        max_results: Numar maxim de rezultate

    Returns:
        Lista de dict-uri cu informatii despre email-uri
    """
    # Query pentru email-uri Netopia cu rapoarte de decontare
    # Email-urile vin de la: NETOPIA Payments <contact@netopia.ro>
    # Subject contine: "Detalii decontare" si "BatchId"
    after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    query = f'from:contact@netopia.ro subject:"Detalii decontare" subject:BatchId after:{after_date}'

    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    return messages


def extract_batch_id_from_email(service, message_id: str) -> Optional[Dict]:
    """
    Extrage BatchId si alte informatii dintr-un email Netopia.

    Args:
        service: Gmail API service
        message_id: ID-ul mesajului Gmail

    Returns:
        Dict cu batch_id, date, subject sau None
    """
    message = service.users().messages().get(
        userId='me',
        id=message_id,
        format='full'
    ).execute()

    # Extrage headers
    headers = message.get('payload', {}).get('headers', [])
    subject = ''
    date = ''
    for header in headers:
        if header['name'] == 'Subject':
            subject = header['value']
        elif header['name'] == 'Date':
            date = header['value']

    # Extrage body-ul email-ului
    body = ''
    payload = message.get('payload', {})

    # Incearca sa gaseasca body-ul in diferite formate
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                if part.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
            elif part.get('mimeType') == 'text/html':
                if part.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

    # Cauta BatchId in body
    # Pattern: "BatchId: 55315140" sau "identificatorul BatchId: 55315140"
    batch_id_patterns = [
        r'BatchId[:\s]+(\d+)',
        r'batch[_-]?id[:\s]+(\d+)',
        r'/report/(\d+)/download',
    ]

    batch_id = None
    for pattern in batch_id_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            batch_id = match.group(1)
            break

    if not batch_id:
        # Incearca si in subject
        for pattern in batch_id_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                batch_id = match.group(1)
                break

    if batch_id:
        return {
            'batch_id': batch_id,
            'subject': subject,
            'date': date,
            'message_id': message_id
        }

    return None


def get_all_netopia_batch_ids(days_back: int = 30) -> List[Dict]:
    """
    Obtine toate BatchId-urile Netopia din ultimele N zile.

    Args:
        days_back: Cate zile in urma sa caute

    Returns:
        Lista de dict-uri cu batch_id, date, subject
    """
    service = get_gmail_service()
    messages = search_netopia_emails(service, days_back=days_back)

    batch_ids = []
    seen_ids = set()

    for msg in messages:
        result = extract_batch_id_from_email(service, msg['id'])
        if result and result['batch_id'] not in seen_ids:
            seen_ids.add(result['batch_id'])
            batch_ids.append(result)

    # Sorteaza dupa data (cele mai recente primele)
    batch_ids.sort(key=lambda x: x['date'], reverse=True)

    return batch_ids


def test_gmail_connection() -> bool:
    """Testeaza conexiunea la Gmail API."""
    try:
        service = get_gmail_service()
        # Incearca sa obtina profilul
        profile = service.users().getProfile(userId='me').execute()
        return True
    except Exception as e:
        print(f"Gmail connection error: {e}")
        return False
