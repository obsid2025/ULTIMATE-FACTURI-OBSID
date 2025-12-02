"""
Procesoare pentru borderouri GLS, Sameday si Netopia
"""

import pandas as pd
import os
import re
from typing import List, Dict, Tuple, Optional


def proceseaza_borderouri_gls(folder_gls: str, gomag_df: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
    """
    Proceseaza borderourile GLS si potriveste AWB-urile cu facturile din Gomag.

    Returns:
        Tuple: (rezultate, erori)
    """
    rezultate = []
    erori = []

    if not folder_gls or not os.path.isdir(folder_gls):
        return [], []

    # Normalizeaza coloanele Gomag
    gomag_df.columns = gomag_df.columns.str.strip().str.lower()
    if 'awb' not in gomag_df.columns or 'numar factura' not in gomag_df.columns:
        erori.append("Gomag: Lipsesc coloanele 'AWB' sau 'Numar Factura'")
        return [], erori

    gomag_df['awb_normalizat'] = gomag_df['awb'].astype(str).str.replace(' ', '').str.lstrip('0')

    for file in os.listdir(folder_gls):
        if not file.endswith('.xlsx'):
            continue

        path = os.path.join(folder_gls, file)
        try:
            borderou = pd.read_excel(path, header=7, dtype={'Numar colet': str})

            if not {'Numar colet', 'Suma ramburs'}.issubset(borderou.columns):
                # Incearca cu diacritice
                if not {'Număr colet', 'Sumă ramburs'}.issubset(borderou.columns):
                    erori.append(f"GLS {file}: Coloane lipsa")
                    continue
                awb_col = 'Număr colet'
                suma_col = 'Sumă ramburs'
            else:
                awb_col = 'Numar colet'
                suma_col = 'Suma ramburs'

            borderou['AWB_normalizat'] = borderou[awb_col].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(' ', '').str.lstrip('0')

            # Merge cu Gomag
            potrivite = borderou.merge(
                gomag_df[['awb_normalizat', 'numar factura']],
                left_on='AWB_normalizat',
                right_on='awb_normalizat',
                how='left'
            )

            potrivite['suma'] = pd.to_numeric(potrivite[suma_col], errors='coerce').fillna(0)
            potrivite['curier'] = 'GLS'
            potrivite['fisier'] = file

            # Calculeaza totalul
            suma_total = potrivite['suma'].sum()

            rezultate.append({
                'borderou': file,
                'curier': 'GLS',
                'potrivite': potrivite,
                'suma_total': suma_total,
                'numar_awb': len(potrivite)
            })

        except Exception as e:
            erori.append(f"GLS {file}: {str(e)}")

    return rezultate, erori


def proceseaza_borderouri_sameday(folder_sameday: str, gomag_df: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
    """
    Proceseaza borderourile Sameday si potriveste AWB-urile cu facturile din Gomag.
    """
    rezultate = []
    erori = []

    if not folder_sameday or not os.path.isdir(folder_sameday):
        return [], []

    # Normalizeaza coloanele Gomag
    gomag_df.columns = gomag_df.columns.str.strip().str.lower()
    if 'awb' not in gomag_df.columns or 'numar factura' not in gomag_df.columns:
        erori.append("Gomag: Lipsesc coloanele 'AWB' sau 'Numar Factura'")
        return [], erori

    gomag_df['awb_normalizat'] = gomag_df['awb'].astype(str).str.strip()

    for file in os.listdir(folder_sameday):
        if not file.endswith('.xlsx'):
            continue

        path = os.path.join(folder_sameday, file)
        try:
            xls = pd.ExcelFile(path)

            # Extrage totalul din sheet-ul 'client'
            suma_total = None
            if 'client' in xls.sheet_names:
                client_sheet = pd.read_excel(xls, sheet_name='client')
                client_sheet.columns = client_sheet.columns.str.strip()
                if 'Suma totala' in client_sheet.columns:
                    try:
                        suma_total = pd.to_numeric(client_sheet['Suma totala'].iloc[1], errors='coerce')
                    except:
                        pass

            # Citeste sheet-ul 'expeditii'
            if 'expeditii' not in xls.sheet_names:
                erori.append(f"Sameday {file}: Lipseste sheet-ul 'expeditii'")
                continue

            borderou = pd.read_excel(xls, sheet_name='expeditii')

            if not {'AWB', 'Suma ramburs'}.issubset(borderou.columns):
                erori.append(f"Sameday {file}: Coloane lipsa")
                continue

            borderou['AWB_normalizat'] = borderou['AWB'].astype(str).str.strip()

            # Merge cu Gomag
            potrivite = borderou.merge(
                gomag_df[['awb_normalizat', 'numar factura']],
                left_on='AWB_normalizat',
                right_on='awb_normalizat',
                how='left'
            )

            potrivite['suma'] = pd.to_numeric(potrivite['Suma ramburs'], errors='coerce').fillna(0)
            potrivite['curier'] = 'Sameday'
            potrivite['fisier'] = file

            if suma_total is None:
                suma_total = potrivite['suma'].sum()

            rezultate.append({
                'borderou': file,
                'curier': 'Sameday',
                'potrivite': potrivite,
                'suma_total': suma_total,
                'numar_awb': len(potrivite)
            })

        except Exception as e:
            erori.append(f"Sameday {file}: {str(e)}")

    return rezultate, erori


def proceseaza_netopia(folder_netopia: str, gomag_df: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
    """
    Proceseaza fisierele CSV Netopia si potriveste tranzactiile cu facturile din Gomag.
    """
    rezultate = []
    erori = []

    if not folder_netopia or not os.path.isdir(folder_netopia):
        return [], []

    # Normalizeaza coloanele Gomag
    gomag_df.columns = gomag_df.columns.str.strip().str.lower()
    if 'numar comanda' not in gomag_df.columns:
        erori.append("Gomag: Lipseste coloana 'Numar Comanda'")
        return [], erori

    gomag_df['numar comanda'] = gomag_df['numar comanda'].astype(str).str.strip()

    for file in os.listdir(folder_netopia):
        if not file.endswith('.csv'):
            continue

        path = os.path.join(folder_netopia, file)
        try:
            netopia_df = pd.read_csv(path, sep=',', encoding='utf-8', dtype=str)
            netopia_df.columns = netopia_df.columns.str.strip().str.replace('"', '').str.replace("'", "")

            # Extrage batchId din numele fisierului
            batch_match = re.search(r'batchId\.(\d+)', file)
            batchid = batch_match.group(1) if batch_match else None

            # Cauta coloana cu numarul comenzii
            order_col = None
            for col in netopia_df.columns:
                if 'order' in col.lower() or 'comanda' in col.lower():
                    order_col = col
                    break

            if order_col:
                netopia_df['numar_comanda_norm'] = netopia_df[order_col].astype(str).str.strip()

                # Merge cu Gomag
                potrivite = netopia_df.merge(
                    gomag_df[['numar comanda', 'numar factura']],
                    left_on='numar_comanda_norm',
                    right_on='numar comanda',
                    how='left'
                )
            else:
                potrivite = netopia_df.copy()
                potrivite['numar factura'] = None

            potrivite['curier'] = 'Netopia'
            potrivite['fisier'] = file
            potrivite['batchid'] = batchid

            # Calculeaza suma
            suma_col = None
            for col in potrivite.columns:
                if 'suma' in col.lower() or 'amount' in col.lower() or 'procesat' in col.lower():
                    suma_col = col
                    break

            if suma_col:
                potrivite['suma'] = pd.to_numeric(potrivite[suma_col].str.replace(',', '.'), errors='coerce').fillna(0)
                suma_total = potrivite['suma'].sum()
            else:
                suma_total = 0

            rezultate.append({
                'borderou': file,
                'curier': 'Netopia',
                'batchid': batchid,
                'potrivite': potrivite,
                'suma_total': suma_total,
                'numar_tranzactii': len(potrivite)
            })

        except Exception as e:
            erori.append(f"Netopia {file}: {str(e)}")

    return rezultate, erori
