# -*- coding: utf-8 -*-
"""
Processor pentru comenzi decanturi - Migrat din aplicația Flask pregatire_decanturi
Procesează fișiere Excel cu comenzi și generează rapoarte de producție
"""

import pandas as pd
import re
import requests
import io
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from utils.supabase_client import get_supabase_client

# Configurare logging
logger = logging.getLogger(__name__)

# URL Google Sheets pentru baza de date produse
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/17FhRBDaknpXgsoTXOkpEWcMf2o55uOjDymlaGiiKUwU/export?format=csv&gid=1884124540"

# Cache pentru baza de date produse
_product_db_cache: Optional[Dict[str, str]] = None
_product_db_cache_time: Optional[datetime] = None
_product_db_reverse_cache: Optional[Dict[str, str]] = None  # SKU -> Nume


def normalize_name(text: str) -> str:
    """
    Normalizează numele produsului pentru matching:
    - lowercase
    - elimină 'parfum'
    - elimină caractere non-alfanumerice
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = text.replace('parfum', '')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text


def load_product_db() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Încarcă baza de date produse din Google Sheets
    Returns: (dict normalizat -> SKU, dict SKU -> nume)
    """
    product_db = {}
    reverse_db = {}

    try:
        logger.info("Downloading product database from Google Sheets...")
        response = requests.get(GOOGLE_SHEET_URL, timeout=10)
        response.raise_for_status()

        df_db = pd.read_csv(io.BytesIO(response.content))

        for _, row in df_db.iterrows():
            nume = str(row.get('Denumire Produs', ''))
            sku = str(row.get('Cod Produs (SKU)', '')).strip()
            if nume and sku and sku.lower() != 'nan':
                norm_nume = normalize_name(nume)
                product_db[norm_nume] = sku
                reverse_db[sku] = nume

        logger.info(f"Loaded {len(product_db)} products from database")

    except Exception as e:
        logger.error(f"Error loading product database: {e}")

    return product_db, reverse_db


def get_product_database() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Returnează baza de date de produse, cu cache de 1 oră
    """
    global _product_db_cache, _product_db_cache_time, _product_db_reverse_cache

    if _product_db_cache is not None and _product_db_cache_time is not None:
        if datetime.now() - _product_db_cache_time < timedelta(hours=1):
            return _product_db_cache, _product_db_reverse_cache

    _product_db_cache, _product_db_reverse_cache = load_product_db()
    _product_db_cache_time = datetime.now()
    return _product_db_cache, _product_db_reverse_cache


def extrage_info_produs(text_produs: str) -> Optional[Tuple[str, int, int]]:
    """
    Extrage informații din textul produsului
    Returns: (nume_parfum, cantitate_ml, numar_bucati) sau None dacă nu e decant
    """
    if 'Decant' not in text_produs:
        return None

    match_ml = re.search(r'Decant (\d+) ml parfum (.+?),', text_produs)
    if not match_ml:
        return None

    cantitate_ml = int(match_ml.group(1))
    nume_parfum = match_ml.group(2).strip()

    match_bucati = re.search(r'(\d+\.\d+)$', text_produs.strip())
    if match_bucati:
        numar_bucati = float(match_bucati.group(1))
    else:
        numar_bucati = 1.0

    return (nume_parfum, cantitate_ml, int(numar_bucati))


def extrage_info_produs_intreg(text_produs: str) -> Optional[Tuple[str, int]]:
    """
    Extrage informații pentru produse întregi (non-decanturi)
    Returns: (nume_produs, numar_bucati) sau None
    """
    if 'Decant' in text_produs:
        return None

    match_bucati = re.search(r'(\d+\.\d+)$', text_produs.strip())
    if match_bucati:
        numar_bucati = float(match_bucati.group(1))
        nume_produs = text_produs.rsplit(',', 1)[0].strip()
    else:
        numar_bucati = 1.0
        nume_produs = text_produs.strip()

    return (nume_produs, int(numar_bucati))


def detecteaza_coloane(df: pd.DataFrame) -> Tuple[str, str]:
    """
    Detectează automat coloanele necesare din Excel
    Returns: (coloana_status, coloana_produse)
    """
    coloane = df.columns.tolist()

    coloana_status = None
    for col in coloane:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in ['status', 'stare', 'statu']):
            coloana_status = col
            break

    coloana_produse = None
    for col in coloane:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in ['produse', 'produs', 'articol', 'item']):
            coloana_produse = col
            break

    if not coloana_status:
        raise ValueError('Nu s-a găsit coloana cu statusul comenzii (trebuie să conțină "Status" în nume)')

    if not coloana_produse:
        raise ValueError('Nu s-a găsit coloana cu produsele comandate (trebuie să conțină "Produse" în nume)')

    return coloana_status, coloana_produse


def proceseaza_comenzi(file_content: bytes) -> Tuple[Dict, Dict, int, int]:
    """
    Procesează fișierul cu comenzi și returnează raportul de producție

    Args:
        file_content: Conținutul fișierului Excel ca bytes

    Returns:
        (raport_decanturi, raport_intregi, comenzi_finalizate, total_comenzi)
    """
    product_db, reverse_db = get_product_database()

    df = pd.read_excel(io.BytesIO(file_content))
    coloana_status, coloana_produse = detecteaza_coloane(df)

    df_finalizate = df[df[coloana_status].astype(str).str.contains('Finalizata|Confirmata', case=False, na=False)]

    raport = defaultdict(lambda: {'nume': '', 'cantitate_ml': 0, 'bucati': 0})
    raport_intregi = defaultdict(lambda: {'nume': '', 'bucati': 0, 'sku': 'N/A'})

    for idx, row in df_finalizate.iterrows():
        produse_text = str(row[coloana_produse])
        produse = produse_text.split(' | ')

        for produs in produse:
            info = extrage_info_produs(produs.strip())
            if info:
                nume_parfum, cantitate_ml, numar_bucati = info

                produs_clean = re.sub(r', \d+\.\d+$', '', produs.strip())
                produs_norm = normalize_name(produs_clean)

                sku = product_db.get(produs_norm, 'N/A')

                if sku != 'N/A' and not re.search(r'-\d+$', sku):
                    continue

                raport[sku]['nume'] = nume_parfum
                raport[sku]['cantitate_ml'] = cantitate_ml
                raport[sku]['bucati'] += numar_bucati
            else:
                info_intreg = extrage_info_produs_intreg(produs.strip())
                if info_intreg:
                    nume_produs, numar_bucati = info_intreg

                    produs_clean = re.sub(r', \d+\.\d+$', '', produs.strip())
                    produs_norm = normalize_name(produs_clean)

                    sku = product_db.get(produs_norm, 'N/A')

                    key = sku if sku != 'N/A' else nume_produs
                    raport_intregi[key]['nume'] = nume_produs
                    raport_intregi[key]['bucati'] += numar_bucati
                    raport_intregi[key]['sku'] = sku

    return dict(raport), dict(raport_intregi), len(df_finalizate), len(df)


def proceseaza_bonuri_productie(file_content: bytes, statuses: List[str] = None) -> List[Dict]:
    """
    Procesează fișierul și extrage bonuri de producție NEAGREGATE (per comandă)

    Args:
        file_content: Conținutul fișierului Excel ca bytes
        statuses: Lista de statusuri de comenzi de procesat

    Returns:
        Lista de bonuri cu SKU, nume produs, cantitate, order_id, order_number
    """
    if statuses is None:
        statuses = ['Finalizata', 'Confirmata']

    product_db, reverse_db = get_product_database()

    df = pd.read_excel(io.BytesIO(file_content))
    coloana_status, coloana_produse = detecteaza_coloane(df)

    # Detectare coloana Order ID
    coloana_order_id = None
    coloana_order_number = None
    for col in df.columns:
        col_lower = str(col).lower()
        if 'order_id' in col_lower or 'orderid' in col_lower or col_lower == 'id':
            coloana_order_id = col
        if 'order_number' in col_lower or 'ordernumber' in col_lower or 'numar' in col_lower:
            coloana_order_number = col

    # Filtrare după status
    status_pattern = '|'.join(statuses)
    df_filtrate = df[df[coloana_status].astype(str).str.contains(status_pattern, case=False, na=False)]

    bonuri = []

    for idx, row in df_filtrate.iterrows():
        order_id = int(row[coloana_order_id]) if coloana_order_id and pd.notna(row.get(coloana_order_id)) else idx
        order_number = int(row[coloana_order_number]) if coloana_order_number and pd.notna(row.get(coloana_order_number)) else order_id

        produse_text = str(row[coloana_produse])
        produse = produse_text.split(' | ')

        for produs in produse:
            info = extrage_info_produs(produs.strip())
            if info:
                nume_parfum, cantitate_ml, numar_bucati = info

                produs_clean = re.sub(r', \d+\.\d+$', '', produs.strip())
                produs_norm = normalize_name(produs_clean)

                sku = product_db.get(produs_norm, 'N/A')

                if sku != 'N/A' and not re.search(r'-\d+$', sku):
                    continue

                # Obține numele corect din baza de date
                nume_corect = reverse_db.get(sku, nume_parfum)

                bonuri.append({
                    'sku': sku,
                    'nume': nume_corect,
                    'cantitate': numar_bucati,
                    'cantitate_ml': cantitate_ml,
                    'order_id': order_id,
                    'order_number': order_number
                })

    return bonuri


# ============ SUPABASE DATABASE FUNCTIONS ============

def get_bonuri_procesate_pentru_comenzi(order_numbers: List[int]) -> Set[Tuple[str, int]]:
    """
    Returnează toate bonurile procesate pentru o listă de comenzi.
    Util pentru Smart Resume - verifică ce s-a procesat deja.

    Returns:
        Set de tuple (sku, order_number) deja procesate
    """
    if not order_numbers:
        return set()

    try:
        client = get_supabase_client()
        response = client.table('bonuri_procesate').select('sku, order_number').in_('order_number', order_numbers).execute()

        return {(row['sku'], row['order_number']) for row in response.data}
    except Exception as e:
        logger.error(f"Error reading from Supabase: {e}")
        return set()


def adauga_bon(sku: str, nume: str, cantitate: float, order_id: int = None, order_number: int = None) -> bool:
    """
    Salvează un bon procesat cu succes în Supabase.

    Returns:
        True dacă salvarea a reușit, False altfel
    """
    try:
        client = get_supabase_client()
        today = datetime.now().strftime('%Y-%m-%d')

        data = {
            'sku': sku,
            'nume_produs': nume,
            'cantitate': cantitate,
            'order_id': order_id,
            'order_number': order_number,
            'data_procesare': today
        }

        # Upsert pentru a evita duplicate
        client.table('bonuri_procesate').upsert(
            data,
            on_conflict='sku,order_number'
        ).execute()

        logger.info(f"Bon saved: {sku} (order #{order_number})")
        return True
    except Exception as e:
        logger.error(f"Error saving to Supabase: {e}")
        return False


def verificare_bon_exista(sku: str, order_number: int) -> bool:
    """
    Verifică dacă un bon pentru un SKU și o comandă specifică există deja.
    """
    try:
        client = get_supabase_client()
        response = client.table('bonuri_procesate').select('id').eq('sku', sku).eq('order_number', order_number).execute()

        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Error checking Supabase: {e}")
        return False


def get_bonuri_azi() -> List[Dict]:
    """Returnează lista de bonuri procesate astăzi"""
    try:
        client = get_supabase_client()
        today = datetime.now().strftime('%Y-%m-%d')

        response = client.table('bonuri_procesate').select('*').eq('data_procesare', today).execute()

        return response.data
    except Exception as e:
        logger.error(f"Error reading from Supabase: {e}")
        return []


def get_statistici_azi() -> Dict:
    """Returnează statistici pentru ziua curentă"""
    try:
        client = get_supabase_client()
        today = datetime.now().strftime('%Y-%m-%d')

        response = client.table('bonuri_procesate').select('*').eq('data_procesare', today).execute()

        bonuri = response.data

        return {
            'total_bonuri': len(bonuri),
            'total_comenzi': len(set(b.get('order_number') for b in bonuri if b.get('order_number'))),
            'total_cantitate': sum(float(b.get('cantitate', 0)) for b in bonuri)
        }
    except Exception as e:
        logger.error(f"Error getting stats from Supabase: {e}")
        return {'total_bonuri': 0, 'total_comenzi': 0, 'total_cantitate': 0}


def genereaza_tabel_raport(raport: Dict) -> List[Dict]:
    """
    Generează datele pentru tabel în format optimizat
    """
    parfumuri = {}
    for sku, info in raport.items():
        nume_parfum = info['nume']
        cantitate_ml = info['cantitate_ml']
        bucati = info['bucati']

        if nume_parfum not in parfumuri:
            parfumuri[nume_parfum] = {}
        if cantitate_ml not in parfumuri[nume_parfum]:
            parfumuri[nume_parfum][cantitate_ml] = []

        parfumuri[nume_parfum][cantitate_ml].append({
            'sku': sku,
            'bucati': bucati
        })

    randuri = []
    for nume_parfum in sorted(parfumuri.keys()):
        cantitati = parfumuri[nume_parfum]
        total_bucati = sum(sum(item['bucati'] for item in items) for items in cantitati.values())

        cantitati_sortate = sorted(cantitati.items())

        primul_rand = True
        for ml, items in cantitati_sortate:
            for item in items:
                randuri.append({
                    'parfum': nume_parfum if primul_rand else '',
                    'sku': item['sku'],
                    'cantitate_ml': ml,
                    'bucati': item['bucati'],
                    'total': total_bucati if primul_rand else '',
                    'este_prim': primul_rand
                })
                primul_rand = False

    return randuri


def genereaza_export_excel(raport: Dict, raport_intregi: Dict) -> bytes:
    """
    Generează un fișier Excel cu raportul de producție
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Decanturi
        if raport:
            rows = []
            for sku, info in sorted(raport.items(), key=lambda x: x[1]['bucati'], reverse=True):
                rows.append({
                    'SKU': sku,
                    'Nume Produs': info['nume'],
                    'Cantitate (ml)': info['cantitate_ml'],
                    'Bucăți': info['bucati']
                })
            df_decanturi = pd.DataFrame(rows)
            df_decanturi.to_excel(writer, sheet_name='Decanturi', index=False)

        # Sheet 2: Produse Întregi
        if raport_intregi:
            rows = []
            for key, info in sorted(raport_intregi.items(), key=lambda x: x[1]['bucati'], reverse=True):
                rows.append({
                    'SKU': info.get('sku', 'N/A'),
                    'Nume Produs': info['nume'],
                    'Bucăți': info['bucati']
                })
            df_intregi = pd.DataFrame(rows)
            df_intregi.to_excel(writer, sheet_name='Produse Intregi', index=False)

    output.seek(0)
    return output.getvalue()
