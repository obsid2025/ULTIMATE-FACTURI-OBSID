"""
Script pentru compararea metodei de mapare: Period Reference vs Order ID Overlap
Scopul: Să decidem care metodă este mai precisă pentru gruparea fișierelor
"""
import pandas as pd
import os
import re
from datetime import datetime

folder_emag = "9 septembrie/eMag"

print("=" * 100)
print("COMPARAȚIE METODE DE MAPARE: PERIOD REFERENCE vs ORDER ID OVERLAP")
print("=" * 100)

# ====================================================================================
# Funcții helper
# ====================================================================================
def extract_order_ids(file_path):
    """Extrage Order ID-urile dintr-un fișier"""
    try:
        df = pd.read_excel(file_path, dtype=str)
        # DP folosește "Order ID", altele folosesc "ID comanda"
        order_col = 'Order ID' if 'Order ID' in df.columns else 'ID comanda' if 'ID comanda' in df.columns else None
        if order_col:
            return set(df[order_col].dropna().unique())
        return set()
    except:
        return set()

def get_reference_period(file_path):
    """Extrage perioada de referință din fișierul DP"""
    try:
        df = pd.read_excel(file_path, dtype=str)
        if 'Reference period start' in df.columns and 'Reference period end' in df.columns:
            start = df['Reference period start'].iloc[0]
            end = df['Reference period end'].iloc[0]
            return (start, end)
        return None
    except:
        return None

def get_luna(file_path):
    """Extrage Luna din fișier"""
    try:
        df = pd.read_excel(file_path, dtype=str)
        if 'Luna' in df.columns and len(df) > 0:
            return df['Luna'].iloc[0]
        return None
    except:
        return None

def extract_period_from_filename(filename):
    """Extrage perioada MMYYYY din numele fișierului"""
    match = re.search(r'_(\d{6})_', filename)
    if match:
        period = match.group(1)
        month = period[:2]
        year = period[2:]
        return f"{month}/{year}"
    return None

# ====================================================================================
# Colectează fișierele
# ====================================================================================
files_by_type = {
    'DP': [],
    'DC': [],
    'DV': [],
    'DVS': [],
    'DY': [],
    'DCS': [],
    'DCCO': [],
    'DCCD': [],
    'DED': []
}

for filename in os.listdir(folder_emag):
    if not filename.endswith('.xlsx'):
        continue
    
    if filename.startswith('nortia_dp_'):
        files_by_type['DP'].append(filename)
    elif filename.startswith('nortia_dccd_'):
        files_by_type['DCCD'].append(filename)
    elif filename.startswith('nortia_dcco_'):
        files_by_type['DCCO'].append(filename)
    elif filename.startswith('nortia_dc_'):
        files_by_type['DC'].append(filename)
    elif filename.startswith('nortia_dvs_'):
        files_by_type['DVS'].append(filename)
    elif filename.startswith('nortia_dv_'):
        files_by_type['DV'].append(filename)
    elif filename.startswith('nortia_dy_'):
        files_by_type['DY'].append(filename)
    elif filename.startswith('nortia_dcs_'):
        files_by_type['DCS'].append(filename)
    elif filename.startswith('nortia_ded_'):
        files_by_type['DED'].append(filename)

# ====================================================================================
# METODA 1: Mapare după Reference Period din DP
# ====================================================================================
print("\n" + "=" * 100)
print("METODA 1: MAPARE DUPĂ REFERENCE PERIOD (din fișierele DP)")
print("=" * 100)

dp_periods = []
for dp_file in sorted(files_by_type['DP']):
    file_path = os.path.join(folder_emag, dp_file)
    period = get_reference_period(file_path)
    order_ids = extract_order_ids(file_path)
    
    if period:
        dp_periods.append({
            'file': dp_file,
            'period_start': period[0],
            'period_end': period[1],
            'order_ids': order_ids
        })
        print(f"\n📄 {dp_file}")
        print(f"   Perioadă: {period[0]} → {period[1]}")
        print(f"   Order IDs: {len(order_ids)}")

# Verifică dacă alte fișiere au "Luna" care se potrivește cu perioada DP
print("\n" + "-" * 100)
print("Verificare match după Luna în alte fișiere:")
print("-" * 100)

for file_type in ['DC', 'DV', 'DVS', 'DY', 'DCS', 'DCCO', 'DCCD', 'DED']:
    if not files_by_type[file_type]:
        continue
    
    print(f"\n{file_type}:")
    for filename in sorted(files_by_type[file_type]):
        file_path = os.path.join(folder_emag, filename)
        luna = get_luna(file_path)
        period_from_name = extract_period_from_filename(filename)
        
        print(f"  {filename}")
        print(f"    Luna din fișier: {luna}")
        print(f"    Perioadă din nume: {period_from_name}")
        
        # Încearcă să potrivească cu perioade DP
        order_ids_file = extract_order_ids(file_path)
        if order_ids_file:
            print(f"    Order IDs: {len(order_ids_file)}")
            for dp in dp_periods:
                overlap = order_ids_file & dp['order_ids']
                if overlap:
                    overlap_percent = (len(overlap) / len(order_ids_file) * 100)
                    print(f"      → Match cu {dp['file'][:40]}: {len(overlap)} IDs ({overlap_percent:.1f}%)")

# ====================================================================================
# METODA 2: Mapare după Order ID Overlap
# ====================================================================================
print("\n" + "=" * 100)
print("METODA 2: MAPARE DUPĂ ORDER ID OVERLAP")
print("=" * 100)

print("\nGRUPURI BAZATE PE ORDER ID OVERLAP (>50%):\n")

for idx, dp in enumerate(dp_periods, 1):
    print(f"\n{'='*100}")
    print(f"GRUP {idx}: DP {dp['file']}")
    print(f"Perioadă: {dp['period_start']} → {dp['period_end']}")
    print(f"{'='*100}")
    
    # Pentru fiecare tip de fișier, găsește cel mai bun match
    for file_type in ['DC', 'DV', 'DVS', 'DY', 'DCS', 'DCCO', 'DCCD', 'DED']:
        matches = []
        
        for filename in files_by_type[file_type]:
            file_path = os.path.join(folder_emag, filename)
            order_ids_file = extract_order_ids(file_path)
            
            if not order_ids_file:
                continue
            
            overlap = dp['order_ids'] & order_ids_file
            overlap_percent = (len(overlap) / len(order_ids_file) * 100) if len(order_ids_file) > 0 else 0
            
            if overlap_percent > 50:
                matches.append({
                    'file': filename,
                    'overlap': len(overlap),
                    'overlap_percent': overlap_percent,
                    'total_ids': len(order_ids_file)
                })
        
        if matches:
            # Sortează după overlap percent
            matches.sort(key=lambda x: x['overlap_percent'], reverse=True)
            best_match = matches[0]
            print(f"  {file_type:4s}: {best_match['file']}")
            print(f"        → {best_match['overlap']}/{best_match['total_ids']} IDs ({best_match['overlap_percent']:.1f}%)")
            
            if len(matches) > 1:
                print(f"        ⚠️  ATENȚIE: {len(matches)} fișiere au overlap > 50%!")
                for m in matches[1:]:
                    print(f"           - {m['file']} ({m['overlap_percent']:.1f}%)")

# ====================================================================================
# RECOMANDARE FINALĂ
# ====================================================================================
print("\n" + "=" * 100)
print("RECOMANDARE METODĂ DE IMPLEMENTARE")
print("=" * 100)

print("""
📊 ANALIZĂ:

METODA 1 - Reference Period din DP:
  ✅ Avantaje:
    - Perioadă explicită definită de eMag în fișierul DP
    - Nu depinde de overlap-uri care pot varia
    - Logică clară: toate fișierele din aceeași lună calendaristică aparțin împreună
  
  ❌ Dezavantaje:
    - Alte fișiere (DC, DV, etc.) nu au "Reference period", doar "Luna"
    - Trebuie să facem match între perioada DP și Luna din alte fișiere
    - Poate exista ambiguitate dacă eMag emite rapoarte pentru aceeași lună în momente diferite

METODA 2 - Order ID Overlap:
  ✅ Avantaje:
    - Match exact bazat pe comenzile reale procesate
    - Nu depinde de interpretarea perioadelor calendaristice
    - Poate identifica asocieri chiar dacă denumirile sunt inconsistente
  
  ❌ Dezavantaje:
    - Mai complexă de implementat
    - Poate avea cazuri ambigue (același Order ID în multiple rapoarte)
    - Calculul overlap-ului necesită citirea tuturor fișierelor

🎯 RECOMANDARE:

Implementează METODA HIBRIDĂ:
  1. Folosește Reference Period din DP ca perioadă principală
  2. Căută fișierele DC, DV, etc. care au:
     - Luna == perioada DP (potrivire calendaristică)
     SAU
     - Order ID overlap > 80% (confirmare prin date)
  
  3. În caz de conflict, prioritizează Order ID overlap

Această abordare combină claritatea perioadei de referință cu siguranța
verificării Order ID-urilor pentru cazurile ambigue.
""")

print("\n" + "=" * 100)
print("ANALIZA COMPLETĂ")
print("=" * 100)
