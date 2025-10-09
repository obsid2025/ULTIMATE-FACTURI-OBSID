"""
Script de debugging pentru a înțelege cum se grupează fișierele eMag
"""
import pandas as pd
import os
import re
from datetime import datetime

def extract_cluster_key(file_path):
    """Extrage cheia de cluster din numele fișierului"""
    base = os.path.basename(file_path)
    m = re.search(r'_\d{6}_(\d{6,})', base)
    if m:
        digits = m.group(1)
        return digits[:7]
    m2 = re.search(r'(\d{7,})', base)
    if m2:
        return m2.group(1)[:7]
    return 'default'

def get_file_period(file_path, file_type):
    """Determină perioada unui fișier eMag"""
    try:
        if file_type == 'dp':
            df = pd.read_excel(file_path, dtype=str)
            if 'Reference period start' in df.columns and len(df) > 0:
                period_start = pd.to_datetime(df['Reference period start'].iloc[0])
                period_end = pd.to_datetime(df['Reference period end'].iloc[0])
                return f"{period_start.year}-{period_start.month:02d}", period_start, period_end
        else:
            df = pd.read_excel(file_path, dtype=str)
            if 'Luna' in df.columns and len(df) > 0:
                luna_text = str(df['Luna'].iloc[0]).strip()
                month_map = {
                    'ianuarie': '01', 'februarie': '02', 'martie': '03',
                    'aprilie': '04', 'mai': '05', 'iunie': '06',
                    'iulie': '07', 'august': '08', 'septembrie': '09',
                    'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'
                }
                for month_name, month_num in month_map.items():
                    if month_name in luna_text.lower():
                        year = re.search(r'\d{4}', luna_text)
                        if year:
                            return f"{year.group()}-{month_num}", None, None
    except Exception as e:
        print(f"Eroare la determinarea perioadei pentru {file_path}: {e}")
    
    # Fallback: extrage din numele fișierului
    match = re.search(r'(\d{2})(\d{4})', os.path.basename(file_path))
    if match:
        month = match.group(1)
        year = match.group(2)
        return f"{year}-{month}", None, None
    return None, None, None

# Caută fișierele eMag din septembrie
folder_emag = "9 septembrie/eMag"

print("=" * 80)
print("ANALIZA FIȘIERELOR eMag - SEPTEMBRIE 2025")
print("=" * 80)

files_by_type = {
    'dp': [], 'dc': [], 'dcco': [], 'dccd': [], 
    'ded': [], 'dv': [], 'dvs': [], 'dy': [], 'dcs': []
}

# Colectează toate fișierele
for file in os.listdir(folder_emag):
    if not file.endswith('.xlsx'):
        continue
    
    file_path = os.path.join(folder_emag, file)
    
    if file.startswith('nortia_dp_'):
        files_by_type['dp'].append(file_path)
    elif file.startswith('nortia_dcco_'):
        files_by_type['dcco'].append(file_path)
    elif file.startswith('nortia_dccd_'):
        files_by_type['dccd'].append(file_path)
    elif file.startswith('nortia_dc_') and not file.startswith('nortia_dccd_') and not file.startswith('nortia_dcco_'):
        files_by_type['dc'].append(file_path)
    elif file.startswith('nortia_ded_'):
        files_by_type['ded'].append(file_path)
    elif file.startswith('nortia_dv_'):
        files_by_type['dv'].append(file_path)
    elif file.startswith('nortia_dvs_'):
        files_by_type['dvs'].append(file_path)
    elif file.startswith('nortia_dy_'):
        files_by_type['dy'].append(file_path)
    elif file.startswith('nortia_dcs_'):
        files_by_type['dcs'].append(file_path)

# Analizează fiecare tip de fișier
print("\n1. FIȘIERE DP (Plăți):")
print("-" * 80)
for dp_file in sorted(files_by_type['dp']):
    period, start, end = get_file_period(dp_file, 'dp')
    cluster = extract_cluster_key(dp_file)
    print(f"  {os.path.basename(dp_file)}")
    print(f"    Perioadă: {period}")
    if start and end:
        print(f"    Start: {start.strftime('%Y-%m-%d')}, End: {end.strftime('%Y-%m-%d')}")
    print(f"    Cluster: {cluster}")
    print()

print("\n2. FIȘIERE DC (Comision):")
print("-" * 80)
for dc_file in sorted(files_by_type['dc']):
    period, _, _ = get_file_period(dc_file, 'dc')
    cluster = extract_cluster_key(dc_file)
    print(f"  {os.path.basename(dc_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(dc_file, header=None)
        if df.shape[1] > 19 and df.shape[0] > 1:
            value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
            if not pd.isna(value):
                print(f"    Valoare (T2): {abs(value):.2f} RON (cu TVA 21%: {abs(value) * 1.21:.2f})")
    except:
        pass
    print()

print("\n3. FIȘIERE DV (Voucher):")
print("-" * 80)
for dv_file in sorted(files_by_type['dv']):
    period, _, _ = get_file_period(dv_file, 'dv')
    cluster = extract_cluster_key(dv_file)
    print(f"  {os.path.basename(dv_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(dv_file, dtype=str)
        if 'Valoare vouchere' in df.columns:
            values = pd.to_numeric(df['Valoare vouchere'], errors='coerce')
            total = values.sum()
            print(f"    Total: {total:.2f} RON")
    except:
        pass
    print()

print("\n4. FIȘIERE DVS (Voucher Stornat):")
print("-" * 80)
for dvs_file in sorted(files_by_type['dvs']):
    period, _, _ = get_file_period(dvs_file, 'dvs')
    cluster = extract_cluster_key(dvs_file)
    print(f"  {os.path.basename(dvs_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(dvs_file, dtype=str)
        if 'Valoare vouchere' in df.columns:
            values = pd.to_numeric(df['Valoare vouchere'], errors='coerce')
            total = values.sum()
            print(f"    Total: {total:.2f} RON")
    except:
        pass
    print()

print("\n5. FIȘIERE DY (Discount Voucher):")
print("-" * 80)
for dy_file in sorted(files_by_type['dy']):
    period, _, _ = get_file_period(dy_file, 'dy')
    cluster = extract_cluster_key(dy_file)
    print(f"  {os.path.basename(dy_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea din W2
    try:
        df = pd.read_excel(dy_file, header=None)
        if df.shape[1] > 22 and df.shape[0] > 1:
            value = pd.to_numeric(df.iloc[1, 22], errors='coerce')
            if not pd.isna(value):
                print(f"    Valoare (W2): {value:.2f} RON")
    except:
        pass
    print()

print("\n6. FIȘIERE DCS (Comision Stornat):")
print("-" * 80)
for dcs_file in sorted(files_by_type['dcs']):
    period, _, _ = get_file_period(dcs_file, 'dcs')
    cluster = extract_cluster_key(dcs_file)
    print(f"  {os.path.basename(dcs_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(dcs_file, dtype=str)
        if 'Comision Net' in df.columns:
            values = pd.to_numeric(df['Comision Net'], errors='coerce')
            if len(values) > 0:
                first_value = values.iloc[0] if not pd.isna(values.iloc[0]) else 0
                print(f"    Valoare (primul rând): {first_value:.2f} RON (cu TVA 21%: {first_value * 1.21:.2f})")
    except:
        pass
    print()

print("\n7. FIȘIERE DCCO (Comision Comenzi Anulate Card Online):")
print("-" * 80)
for dcco_file in sorted(files_by_type['dcco']):
    period, _, _ = get_file_period(dcco_file, 'dcco')
    cluster = extract_cluster_key(dcco_file)
    print(f"  {os.path.basename(dcco_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(dcco_file, header=None)
        if df.shape[1] > 19 and df.shape[0] > 1:
            value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
            if not pd.isna(value):
                print(f"    Valoare (T2): {abs(value):.2f} RON (cu TVA 21%: {abs(value) * 1.21:.2f})")
    except:
        pass
    print()

print("\n8. FIȘIERE DCCD (Comision Comenzi Anulate Ramburs):")
print("-" * 80)
for dccd_file in sorted(files_by_type['dccd']):
    period, _, _ = get_file_period(dccd_file, 'dccd')
    cluster = extract_cluster_key(dccd_file)
    print(f"  {os.path.basename(dccd_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(dccd_file, header=None)
        if df.shape[1] > 19 and df.shape[0] > 1:
            value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
            if not pd.isna(value):
                print(f"    Valoare (T2): {abs(value):.2f} RON (cu TVA 21%: {abs(value) * 1.21:.2f})")
    except:
        pass
    print()

print("\n9. FIȘIERE DED (easybox):")
print("-" * 80)
for ded_file in sorted(files_by_type['ded']):
    period, _, _ = get_file_period(ded_file, 'ded')
    cluster = extract_cluster_key(ded_file)
    print(f"  {os.path.basename(ded_file)}")
    print(f"    Perioadă: {period}")
    print(f"    Cluster: {cluster}")
    
    # Citește și afișează valoarea
    try:
        df = pd.read_excel(ded_file, header=None)
        if df.shape[1] > 12 and df.shape[0] > 1:
            value = pd.to_numeric(df.iloc[1, 12], errors='coerce')
            if not pd.isna(value):
                print(f"    Valoare (M2): {abs(value):.2f} RON (cu TVA 21%: {abs(value) * 1.21:.2f})")
    except:
        pass
    print()

print("\n" + "=" * 80)
print("GRUPARE PE CLUSTERE (așa cum face scriptul)")
print("=" * 80)

# Simulează gruparea pe clustere
clusters = {}
all_files = []
for file_type, files in files_by_type.items():
    if file_type != 'dp':  # DP nu se grupează pe clustere, e per perioadă
        for f in files:
            period, _, _ = get_file_period(f, file_type)
            if period:
                all_files.append((f, file_type, period))

for f, file_type, period in all_files:
    key = extract_cluster_key(f)
    if key not in clusters:
        clusters[key] = {}
    if period not in clusters[key]:
        clusters[key][period] = {}
    if file_type not in clusters[key][period]:
        clusters[key][period][file_type] = []
    clusters[key][period][file_type].append(f)

for cluster_key in sorted(clusters.keys()):
    print(f"\nCluster {cluster_key}:")
    for period in sorted(clusters[cluster_key].keys()):
        print(f"  Perioadă {period}:")
        for file_type in sorted(clusters[cluster_key][period].keys()):
            print(f"    {file_type.upper()}: {len(clusters[cluster_key][period][file_type])} fișier(e)")
            for f in clusters[cluster_key][period][file_type]:
                print(f"      - {os.path.basename(f)}")
