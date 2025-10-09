"""
Script pentru verificarea overlap-ului de Order ID-uri între fișierele eMag
Scopul: Să vedem dacă Order ID-urile din DP se regăsesc în DC, DV, etc.
"""
import pandas as pd
import os

folder_emag = "9 septembrie/eMag"

print("=" * 100)
print("ANALIZA OVERLAP ORDER ID-URI ÎNTRE FIȘIERE eMag")
print("=" * 100)

# ====================================================================================
# Funcție pentru extragerea Order ID-urilor din fișier
# ====================================================================================
def extract_order_ids(file_path, file_type):
    """Extrage Order ID-urile dintr-un fișier"""
    try:
        df = pd.read_excel(file_path, dtype=str)
        
        # DP folosește "Order ID", altele folosesc "ID comanda"
        order_col = 'Order ID' if 'Order ID' in df.columns else 'ID comanda' if 'ID comanda' in df.columns else None
        
        if not order_col:
            print(f"  ⚠️  Fișierul nu are coloana 'Order ID' sau 'ID comanda'")
            return set(), None
        
        order_ids = set(df[order_col].dropna().unique())
        
        # Extrage și perioada de referință dacă e DP
        period_info = None
        if file_type == 'DP' and 'Reference period start' in df.columns and 'Reference period end' in df.columns:
            period_start = df['Reference period start'].iloc[0]
            period_end = df['Reference period end'].iloc[0]
            period_info = f"{period_start} → {period_end}"
        
        # Extrage Luna pentru alte tipuri
        if 'Luna' in df.columns:
            luna = df['Luna'].iloc[0]
            period_info = f"Luna: {luna}"
        
        return order_ids, period_info
        
    except Exception as e:
        print(f"  ❌ EROARE: {e}")
        return set(), None

# ====================================================================================
# Colectează toate fișierele
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
# Analizează fiecare fișier DP și caută match-uri
# ====================================================================================
print("\n" + "=" * 100)
print("MAPARE FIȘIERE BAZATĂ PE ORDER ID")
print("=" * 100)

# Procesează fișierele DP
dp_data = []
for dp_file in sorted(files_by_type['DP']):
    file_path = os.path.join(folder_emag, dp_file)
    print(f"\n{'='*100}")
    print(f"📄 DP FILE: {dp_file}")
    print(f"{'='*100}")
    
    order_ids_dp, period_info = extract_order_ids(file_path, 'DP')
    print(f"  Perioada: {period_info}")
    print(f"  Order ID-uri: {len(order_ids_dp)}")
    
    dp_data.append({
        'file': dp_file,
        'order_ids': order_ids_dp,
        'period': period_info
    })

print("\n" + "=" * 100)
print("VERIFICARE OVERLAP CU ALTE TIPURI DE FIȘIERE")
print("=" * 100)

# Pentru fiecare tip de fișier (DC, DV, etc.), verifică overlap cu fiecare DP
for file_type in ['DC', 'DV', 'DVS', 'DY', 'DCS', 'DCCO', 'DCCD', 'DED']:
    if not files_by_type[file_type]:
        continue
    
    print(f"\n{'='*100}")
    print(f"📊 ANALIZA FIȘIERE {file_type}")
    print(f"{'='*100}")
    
    for filename in sorted(files_by_type[file_type]):
        file_path = os.path.join(folder_emag, filename)
        print(f"\n  📄 {filename}")
        
        order_ids_file, period_info = extract_order_ids(file_path, file_type)
        print(f"     Info: {period_info}")
        print(f"     Order ID-uri: {len(order_ids_file)}")
        
        if not order_ids_file:
            continue
        
        # Verifică overlap cu fiecare DP
        print(f"\n     🔍 Overlap cu fișierele DP:")
        best_match = None
        best_overlap = 0
        
        for dp in dp_data:
            overlap = order_ids_file & dp['order_ids']
            overlap_percent = (len(overlap) / len(order_ids_file) * 100) if len(order_ids_file) > 0 else 0
            
            if overlap_percent > 0:
                print(f"        ├─ {dp['file'][:50]:50s} → {len(overlap):4d} match ({overlap_percent:5.1f}%) - Perioada: {dp['period']}")
            
            if overlap_percent > best_overlap:
                best_overlap = overlap_percent
                best_match = dp
        
        if best_match:
            print(f"        └─ ✅ BEST MATCH: {best_match['file']} ({best_overlap:.1f}% overlap)")
        else:
            print(f"        └─ ❌ Niciun overlap găsit!")

# ====================================================================================
# Creare matrice de overlap
# ====================================================================================
print("\n" + "=" * 100)
print("MATRICE DE COMPATIBILITATE (Order ID Overlap)")
print("=" * 100)

# Colectează toate fișierele cu Order ID-uri
all_files_data = {}

# DP files
for dp in dp_data:
    all_files_data[dp['file']] = {
        'order_ids': dp['order_ids'],
        'type': 'DP',
        'period': dp['period']
    }

# Alte tipuri
for file_type in ['DC', 'DV', 'DVS', 'DY', 'DCS', 'DCCO', 'DCCD', 'DED']:
    for filename in files_by_type[file_type]:
        file_path = os.path.join(folder_emag, filename)
        order_ids, period_info = extract_order_ids(file_path, file_type)
        all_files_data[filename] = {
            'order_ids': order_ids,
            'type': file_type,
            'period': period_info
        }

# Grupează fișierele care au overlap > 50%
print("\n🎯 GRUPURI SUGERATE (overlap > 50%):\n")

processed_files = set()
group_num = 1

for dp in dp_data:
    if dp['file'] in processed_files:
        continue
    
    print(f"\n{'='*100}")
    print(f"GRUP {group_num}: Perioada {dp['period']}")
    print(f"{'='*100}")
    print(f"  DP: {dp['file']} ({len(dp['order_ids'])} Order IDs)")
    
    group_files = [dp['file']]
    
    # Caută fișiere compatibile
    for file_type in ['DC', 'DV', 'DVS', 'DY', 'DCS', 'DCCO', 'DCCD', 'DED']:
        for filename in files_by_type[file_type]:
            if filename in processed_files:
                continue
            
            file_data = all_files_data.get(filename)
            if not file_data or not file_data['order_ids']:
                continue
            
            overlap = dp['order_ids'] & file_data['order_ids']
            overlap_percent = (len(overlap) / len(file_data['order_ids']) * 100) if len(file_data['order_ids']) > 0 else 0
            
            if overlap_percent > 50:
                print(f"  {file_type:4s}: {filename} ({len(file_data['order_ids'])} Order IDs, {overlap_percent:.1f}% overlap)")
                group_files.append(filename)
                processed_files.add(filename)
    
    processed_files.add(dp['file'])
    group_num += 1

print("\n" + "=" * 100)
print("ANALIZA COMPLETĂ")
print("=" * 100)
