"""
Email Sender Module for OBSID Facturi
Trimite emailuri catre curierii GLS si Sameday pentru colete nelivrate
"""

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# SMTP Configuration
SMTP_SERVER = os.getenv('OBSID_SMTP_SERVER', 'mail.obsid.ro')
SMTP_PORT = int(os.getenv('OBSID_SMTP_PORT', '465'))
SMTP_USERNAME = os.getenv('OBSID_SMTP_USERNAME', 'comenzi@obsid.ro')
SMTP_PASSWORD = os.getenv('OBSID_SMTP_PASSWORD', '')

# Courier email addresses
COURIER_EMAILS = {
    'GLS': {
        'support': 'relatii.clienti@gls-romania.ro',
        'claims': 'reclamatii@gls-romania.ro'
    },
    'SAMEDAY': {
        'support': 'suport@sameday.ro',
        'claims': 'reclamatii@sameday.ro'
    }
}

# Email templates
EMAIL_TEMPLATES = {
    'retry_delivery': {
        'subject': 'Solicitare reincercare livrare - AWB {awb}',
        'body': """Buna ziua,

Va rog sa programati o noua incercare de livrare pentru coletul cu AWB: {awb}

Detalii colet:
- Destinatar: {recipient_name}
- Telefon: {recipient_phone}
- Oras: {city}
- Valoare COD: {cod_amount} RON

Va rugam sa contactati clientul inainte de livrare.

Cu multumiri,
OBSID SRL
comenzi@obsid.ro
"""
    },
    'wrong_address': {
        'subject': 'Adresa gresita - AWB {awb}',
        'body': """Buna ziua,

Am fost informati ca adresa de livrare pentru coletul AWB: {awb} este incorecta.

Detalii colet:
- Destinatar: {recipient_name}
- Telefon: {recipient_phone}
- Oras actual: {city}
- Valoare COD: {cod_amount} RON

Va rugam sa contactati clientul la numarul de telefon pentru a obtine adresa corecta.

Cu multumiri,
OBSID SRL
comenzi@obsid.ro
"""
    },
    'cancel_return': {
        'subject': 'Anulare retur / Reincercare livrare - AWB {awb}',
        'body': """Buna ziua,

Va rog sa anulati returul pentru coletul AWB: {awb} si sa programati o noua incercare de livrare.

Detalii colet:
- Destinatar: {recipient_name}
- Telefon: {recipient_phone}
- Oras: {city}
- Valoare COD: {cod_amount} RON

Clientul a confirmat ca doreste sa primeasca coletul.

Cu multumiri,
OBSID SRL
comenzi@obsid.ro
"""
    },
    'refused_parcel': {
        'subject': 'Colet refuzat - AWB {awb} - Solicitare informatii',
        'body': """Buna ziua,

Va rog sa ne furnizati informatii despre motivul refuzului pentru coletul AWB: {awb}

Detalii colet:
- Destinatar: {recipient_name}
- Telefon: {recipient_phone}
- Oras: {city}
- Valoare COD: {cod_amount} RON

De asemenea, va rog sa ne confirmati cand va ajunge coletul inapoi la depozitul nostru.

Cu multumiri,
OBSID SRL
comenzi@obsid.ro
"""
    },
    'custom': {
        'subject': 'Referitor la colet AWB {awb}',
        'body': """Buna ziua,

AWB: {awb}
Destinatar: {recipient_name}
Telefon: {recipient_phone}
Oras: {city}
COD: {cod_amount} RON

{custom_message}

Cu multumiri,
OBSID SRL
comenzi@obsid.ro
"""
    }
}


def get_template_list() -> List[Dict]:
    """Returneaza lista de template-uri disponibile."""
    return [
        {'id': 'retry_delivery', 'name': 'Reincercare livrare'},
        {'id': 'wrong_address', 'name': 'Adresa gresita'},
        {'id': 'cancel_return', 'name': 'Anulare retur'},
        {'id': 'refused_parcel', 'name': 'Colet refuzat - info'},
        {'id': 'custom', 'name': 'Mesaj personalizat'}
    ]


def format_template(template_id: str, parcel_data: Dict, custom_message: str = "") -> Dict:
    """
    Formateaza un template cu datele coletului.

    Args:
        template_id: ID-ul template-ului
        parcel_data: Dict cu datele coletului (awb, recipient_name, recipient_phone, city, cod_amount)
        custom_message: Mesaj custom pentru template-ul 'custom'

    Returns:
        Dict cu 'subject' si 'body' formatate
    """
    template = EMAIL_TEMPLATES.get(template_id, EMAIL_TEMPLATES['custom'])

    # Prepare data
    data = {
        'awb': parcel_data.get('awb', parcel_data.get('awb_number', parcel_data.get('parcel_number', 'N/A'))),
        'recipient_name': parcel_data.get('recipient_name', 'N/A'),
        'recipient_phone': parcel_data.get('recipient_phone', 'N/A'),
        'city': parcel_data.get('city', parcel_data.get('recipient_city', parcel_data.get('county', 'N/A'))),
        'cod_amount': f"{float(parcel_data.get('cod_amount', 0)):,.2f}",
        'custom_message': custom_message
    }

    return {
        'subject': template['subject'].format(**data),
        'body': template['body'].format(**data)
    }


def get_courier_email(courier: str, email_type: str = 'support') -> str:
    """Returneaza adresa de email a curierului."""
    courier_upper = courier.upper() if courier else 'GLS'
    courier_data = COURIER_EMAILS.get(courier_upper, COURIER_EMAILS.get('GLS'))
    return courier_data.get(email_type, courier_data.get('support'))


def send_email(
    to_email: str,
    subject: str,
    body: str,
    cc_email: Optional[str] = None,
    smtp_password: Optional[str] = None
) -> Dict:
    """
    Trimite un email.

    Args:
        to_email: Adresa destinatarului
        subject: Subiectul emailului
        body: Corpul emailului
        cc_email: Adresa CC (optional)
        smtp_password: Parola SMTP (optional, foloseste env var)

    Returns:
        Dict cu status ('success' sau 'error') si 'message'
    """
    password = smtp_password or SMTP_PASSWORD

    if not password:
        return {'status': 'error', 'message': 'SMTP password not configured'}

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject

        if cc_email:
            msg['Cc'] = cc_email

        # Add body
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Create SSL context
        context = ssl.create_default_context()

        # Connect and send
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USERNAME, password)

            # Recipients include CC if present
            recipients = [to_email]
            if cc_email:
                recipients.append(cc_email)

            server.send_message(msg)

        return {
            'status': 'success',
            'message': f'Email trimis cu succes la {to_email}'
        }

    except smtplib.SMTPAuthenticationError:
        return {'status': 'error', 'message': 'Eroare autentificare SMTP - verifica parola'}
    except smtplib.SMTPException as e:
        return {'status': 'error', 'message': f'Eroare SMTP: {str(e)}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Eroare: {str(e)}'}


def send_courier_email(
    courier: str,
    template_id: str,
    parcel_data: Dict,
    custom_message: str = "",
    smtp_password: Optional[str] = None
) -> Dict:
    """
    Trimite email catre curier folosind un template.

    Args:
        courier: 'GLS' sau 'Sameday'
        template_id: ID-ul template-ului
        parcel_data: Datele coletului
        custom_message: Mesaj custom (pentru template 'custom')
        smtp_password: Parola SMTP

    Returns:
        Dict cu status si message
    """
    # Get courier email
    to_email = get_courier_email(courier)

    # Format template
    formatted = format_template(template_id, parcel_data, custom_message)

    # Send email
    result = send_email(
        to_email=to_email,
        subject=formatted['subject'],
        body=formatted['body'],
        cc_email=SMTP_USERNAME,  # CC ourselves for records
        smtp_password=smtp_password
    )

    return result


def test_smtp_connection(smtp_password: Optional[str] = None) -> Dict:
    """Testeaza conexiunea SMTP."""
    password = smtp_password or SMTP_PASSWORD

    if not password:
        return {'status': 'error', 'message': 'SMTP password not configured'}

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USERNAME, password)
        return {'status': 'success', 'message': 'Conexiune SMTP OK'}
    except Exception as e:
        return {'status': 'error', 'message': f'Eroare: {str(e)}'}
