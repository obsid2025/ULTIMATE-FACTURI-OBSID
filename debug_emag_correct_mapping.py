"""
Script pentru a arăta maparea corectă între fișierele DP și celelalte fișiere
"""
import pandas as pd
import os
import re
from datetime import datetime

def get_dp_period(file_path):
    """Extrage perioada de referință din fișierul DP"""
    try:
        df = pd.read_excel(file_path, dtype=str)
        if 'Reference period start' in df.columns and len(df) > 0:
            period_start = pd.to_datetime(df['Reference period start'].iloc[0])
            period_end = pd.to_datetime(df['Reference period end'].iloc[0])
            return period_start, period_end
    except Exception as e:
        print(f"Eroare: {e}")
    return None, None

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

folder_emag = "9 septembrie/eMag"

# Colectează fișierele DP
dp_files = []
for file in os.listdir(folder_emag):
    if file.startswith('nortia_dp_') and file.endswith('.xlsx'):
        dp_files.append(os.path.join(folder_emag, file))

# Grupează DP pe perioade
dp_by_period = {}
for dp_file in sorted(dp_files):
    start, end = get_dp_period(dp_file)
    if start and end:
        period_key = f"{start.strftime('%Y-%m-%d')} - {end.strftime('%Y-%m-%d')}"
        if period_key not in dp_by_period:
            dp_by_period[period_key] = {
                'start': start,
                'end': end,
                'dp_files': [],
                'dp_total': 0.0
            }
        dp_by_period[period_key]['dp_files'].append(dp_file)
        
        # Calculează totalul DP
        try:
            df = pd.read_excel(dp_file, dtype=str)
            if 'Fraction value' in df.columns:
                values = pd.to_numeric(df['Fraction value'], errors='coerce')
                dp_by_period[period_key]['dp_total'] += values.sum()
        except:
            pass

# Colectează celelalte fișiere
other_files = {
    'dc': [], 'dcco': [], 'dccd': [], 'ded': [], 
    'dv': [], 'dvs': [], 'dy': [], 'dcs': []
}

for file in os.listdir(folder_emag):
    if not file.endswith('.xlsx'):
        continue
    
    file_path = os.path.join(folder_emag, file)
    
    if file.startswith('nortia_dc_') and not file.startswith('nortia_dccd_') and not file.startswith('nortia_dcco_'):
        other_files['dc'].append(file_path)
    elif file.startswith('nortia_dcco_'):
        other_files['dcco'].append(file_path)
    elif file.startswith('nortia_dccd_'):
        other_files['dccd'].append(file_path)
    elif file.startswith('nortia_ded_'):
        other_files['ded'].append(file_path)
    elif file.startswith('nortia_dv_'):
        other_files['dv'].append(file_path)
    elif file.startswith('nortia_dvs_'):
        other_files['dvs'].append(file_path)
    elif file.startswith('nortia_dy_'):
        other_files['dy'].append(file_path)
    elif file.startswith('nortia_dcs_'):
        other_files['dcs'].append(file_path)

print("=" * 80)
print("MAPARE CORECTĂ: FIȘIERE PE PERIOADA DP")
print("=" * 80)

for period_key in sorted(dp_by_period.keys()):
    period_data = dp_by_period[period_key]
    start = period_data['start']
    end = period_data['end']
    
    print(f"\nPERIOADA: {period_key}")
    print(f"DP Total: {period_data['dp_total']:.2f} RON")
    print(f"Fișiere DP ({len(period_data['dp_files'])}):")
    for dp_file in period_data['dp_files']:
        print(f"  - {os.path.basename(dp_file)}")
    
    # Pentru fiecare tip de fișier, găsește cele care aparțin acestei perioade
    # Logica ar trebui să fie: fișierele cu data de emitere în intervalul [start, end]
    # Sau fișierele cu Report ID apropiat de Report ID-ul DP
    
    print("\nClustere găsite:")
    clusters_in_period = set()
    
    # Găsește toate clusterele din această perioadă
    # (de fapt, ar trebui să existe o mapare între Order ID din DP și Order ID din alte fișiere)
    # Pentru simplitate, vom folosi clustere apropiate
    
    dp_cluster = extract_cluster_key(period_data['dp_files'][0])
    print(f"  Cluster DP: {dp_cluster}")
    
    # Caută fișierele cu clustere similare (diferență de max 1000)
    dp_cluster_num = int(dp_cluster)
    
    for file_type, files in other_files.items():
        matching_files = []
        for file in files:
            file_cluster = extract_cluster_key(file)
            file_cluster_num = int(file_cluster)
            
            # Cluster apropiat (diferență de max 1000)
            if abs(file_cluster_num - dp_cluster_num) < 1000:
                matching_files.append((file, file_cluster))
        
        if matching_files:
            print(f"\n  {file_type.upper()} ({len(matching_files)} fișier(e)):")
            for file, cluster in matching_files:
                print(f"    - {os.path.basename(file)} (cluster: {cluster})")
                
                # Afișează și valoarea
                if file_type == 'dc':
                    try:
                        df = pd.read_excel(file, header=None)
                        if df.shape[1] > 19 and df.shape[0] > 1:
                            value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                            if not pd.isna(value):
                                print(f"      Valoare: {abs(value):.2f} RON (cu TVA: {abs(value) * 1.21:.2f})")
                    except:
                        pass
                elif file_type == 'dv':
                    try:
                        df = pd.read_excel(file, dtype=str)
                        if 'Valoare vouchere' in df.columns:
                            values = pd.to_numeric(df['Valoare vouchere'], errors='coerce')
                            print(f"      Total: {values.sum():.2f} RON")
                    except:
                        pass
                elif file_type == 'dvs':
                    try:
                        df = pd.read_excel(file, dtype=str)
                        if 'Valoare vouchere' in df.columns:
                            values = pd.to_numeric(df['Valoare vouchere'], errors='coerce')
                            print(f"      Total: {values.sum():.2f} RON")
                    except:
                        pass
                elif file_type == 'dy':
                    try:
                        df = pd.read_excel(file, header=None)
                        if df.shape[1] > 22 and df.shape[0] > 1:
                            value = pd.to_numeric(df.iloc[1, 22], errors='coerce')
                            if not pd.isna(value):
                                print(f"      Valoare (W2): {value:.2f} RON")
                    except:
                        pass
                elif file_type == 'dcs':
                    try:
                        df = pd.read_excel(file, dtype=str)
                        if 'Comision Net' in df.columns:
                            values = pd.to_numeric(df['Comision Net'], errors='coerce')
                            if len(values) > 0:
                                first_value = values.iloc[0] if not pd.isna(values.iloc[0]) else 0
                                print(f"      Valoare: {first_value:.2f} RON (cu TVA: {first_value * 1.21:.2f})")
                    except:
                        pass
                elif file_type == 'dcco':
                    try:
                        df = pd.read_excel(file, header=None)
                        if df.shape[1] > 19 and df.shape[0] > 1:
                            value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                            if not pd.isna(value):
                                print(f"      Valoare: {abs(value):.2f} RON (cu TVA: {abs(value) * 1.21:.2f})")
                    except:
                        pass
                elif file_type == 'dccd':
                    try:
                        df = pd.read_excel(file, header=None)
                        if df.shape[1] > 19 and df.shape[0] > 1:
                            value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                            if not pd.isna(value):
                                print(f"      Valoare: {abs(value):.2f} RON (cu TVA: {abs(value) * 1.21:.2f})")
                    except:
                        pass
                elif file_type == 'ded':
                    try:
                        df = pd.read_excel(file, header=None)
                        if df.shape[1] > 12 and df.shape[0] > 1:
                            value = pd.to_numeric(df.iloc[1, 12], errors='coerce')
                            if not pd.isna(value):
                                print(f"      Valoare: {abs(value):.2f} RON (cu TVA: {abs(value) * 1.21:.2f})")
                    except:
                        pass
    
    # Calculează totalul pentru această perioadă
    print("\n" + "-" * 80)
    print("CALCUL PENTRU ACEASTĂ PERIOADĂ:")
    print("-" * 80)
