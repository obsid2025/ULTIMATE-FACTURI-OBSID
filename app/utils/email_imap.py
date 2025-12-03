"""
IMAP Email Integration for OBSID Facturi
Citeste email-urile Netopia de pe documente@obsid.ro via IMAP
"""

import os
import re
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# IMAP config
IMAP_SERVER = os.getenv('IMAP_SERVER', 'mail.obsid.ro')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
IMAP_USER = os.getenv('IMAP_USER', 'documente@obsid.ro')
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD', '')


def get_imap_connection():
    """
    Conecteaza la serverul IMAP.

    Returns:
        imaplib.IMAP4_SSL connection sau None
    """
    if not IMAP_PASSWORD:
        raise ValueError("IMAP_PASSWORD nu este configurat in .env")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        return mail
    except Exception as e:
        print(f"Eroare conectare IMAP: {e}")
        raise


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


def get_email_body(msg):
    """Extrage body-ul email-ului (text/plain sau text/html)."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
            elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass

    return body


def search_netopia_emails(days_back: int = 30) -> List[Dict]:
    """
    Cauta email-uri de la Netopia cu rapoarte de decontare.

    Args:
        days_back: Cate zile in urma sa caute

    Returns:
        Lista de dict-uri cu batch_id, date, subject
    """
    mail = get_imap_connection()

    try:
        # Selecteaza INBOX
        mail.select('INBOX')

        # Calculeaza data de start
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')

        # Cauta email-uri de la Netopia cu "decontare" in subject
        # IMAP search: FROM "netopia" SINCE date SUBJECT "decontare"
        search_criteria = f'(FROM "netopia" SINCE {since_date} SUBJECT "decontare")'

        status, messages = mail.search(None, search_criteria)

        if status != 'OK':
            return []

        email_ids = messages[0].split()
        results = []
        seen_batch_ids = set()

        for email_id in email_ids:
            try:
                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parse email
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Get subject
                subject = decode_email_subject(msg['Subject'])

                # Verifica daca e email de decontare cu BatchId
                if 'BatchId' not in subject and 'batchid' not in subject.lower():
                    continue

                # Get date
                date_str = msg['Date']

                # Get body
                body = get_email_body(msg)

                # Extract BatchId
                batch_id = extract_batch_id(subject, body)

                if batch_id and batch_id not in seen_batch_ids:
                    seen_batch_ids.add(batch_id)
                    results.append({
                        'batch_id': batch_id,
                        'subject': subject,
                        'date': date_str,
                        'email_id': email_id.decode()
                    })

            except Exception as e:
                print(f"Eroare la procesare email {email_id}: {e}")
                continue

        # Sorteaza dupa data (cele mai recente primele)
        results.sort(key=lambda x: x['date'], reverse=True)

        return results

    finally:
        mail.logout()


def extract_batch_id(subject: str, body: str) -> Optional[str]:
    """
    Extrage BatchId din subject sau body.

    Patterns:
    - Subject: "Detalii decontare netopia-payments.com BatchId: 55086741"
    - Body: "identificatorul BatchId: 55086741"
    - Body: "/report/2496785/download"
    """
    # Pattern-uri pentru BatchId
    patterns = [
        r'BatchId[:\s]+(\d+)',
        r'batch[_-]?id[:\s]+(\d+)',
        r'/report/(\d+)/download',
    ]

    # Cauta mai intai in subject
    for pattern in patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            return match.group(1)

    # Apoi in body
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def get_all_netopia_batch_ids(days_back: int = 30) -> List[Dict]:
    """
    Obtine toate BatchId-urile Netopia din ultimele N zile.

    Args:
        days_back: Cate zile in urma sa caute

    Returns:
        Lista de dict-uri cu batch_id, date, subject
    """
    return search_netopia_emails(days_back=days_back)


def test_imap_connection() -> bool:
    """Testeaza conexiunea IMAP."""
    try:
        mail = get_imap_connection()
        mail.logout()
        return True
    except Exception as e:
        print(f"IMAP connection error: {e}")
        return False


def is_imap_configured() -> bool:
    """Verifica daca IMAP e configurat."""
    return bool(IMAP_PASSWORD and len(IMAP_PASSWORD) > 0)
