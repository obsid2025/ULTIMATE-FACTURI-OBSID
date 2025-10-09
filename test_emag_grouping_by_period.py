"""
Test script pentru gruparea corecta a fisierelor eMag bazata pe perioade de referinta
Folosim "Data finalizare comanda" pentru a determina in ce perioada DP apartine fiecare inregistrare
"""
import pandas as pd
import os
import sys
from datetime import datetime
from collections import defaultdict

# Forteaza encoding UTF-8
sys.stdout.reconfigure(encoding='utf-8')

folder_emag = "9 septembrie/eMag"

print("=" * 100)
print("TEST GRUPARE FISIERE eMag DUPA PERIOADA DE REFERINTA")
print("=" * 100)

# ====================================================================================
# PASUL 1: Citim toate fișierele DP și extragem perioadele de referință
# ====================================================================================
print("\n" + "=" * 100)
print("PASUL 1: IDENTIFICARE PERIOADE DP")
print("=" * 100)

dp_files = [f for f in os.listdir(folder_emag) if f.startswith('nortia_dp_') and f.endswith('.xlsx')]

# Grupăm DP-urile după perioadă
periods = defaultdict(lambda: {'dp_files': [], 'dp_total': 0, 'start': None, 'end': None})

for dp_file in sorted(dp_files):
    file_path = os.path.join(folder_emag, dp_file)
    print(f"\n📄 {dp_file}")
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        
        # Extrage perioada de referință
        if 'Reference period start' in df.columns and 'Reference period end' in df.columns:
            period_start = df['Reference period start'].iloc[0]
            period_end = df['Reference period end'].iloc[0]
            period_key = f"{period_start}_{period_end}"
            
            print(f"   Perioadă: {period_start} → {period_end}")
            
            # Calculează totalul DP
            if 'Fraction value' in df.columns:
                total = pd.to_numeric(df['Fraction value'], errors='coerce').sum()
                print(f"   Total DP: {total:.2f} RON")
                
                periods[period_key]['dp_files'].append(dp_file)
                periods[period_key]['dp_total'] += total
                periods[period_key]['start'] = period_start
                periods[period_key]['end'] = period_end
            
    except Exception as e:
        print(f"   ❌ EROARE: {e}")

print("\n" + "-" * 100)
print("PERIOADE IDENTIFICATE:")
print("-" * 100)

for period_key, data in periods.items():
    print(f"\n🗓️  Perioadă: {data['start']} → {data['end']}")
    print(f"   Fișiere DP: {len(data['dp_files'])}")
    print(f"   Total DP: {data['dp_total']:.2f} RON")
    for dp_file in data['dp_files']:
        print(f"      - {dp_file}")

# ====================================================================================
# PASUL 2: Pentru fiecare tip de fișier, citim înregistrările și le mapăm la perioade
# ====================================================================================
print("\n" + "=" * 100)
print("PASUL 2: MAPARE FIȘIERE LA PERIOADE BAZATĂ PE DATA FINALIZARE")
print("=" * 100)

def parse_date(date_str):
    """Convertește string-ul de dată în obiect datetime"""
    try:
        if pd.isna(date_str) or date_str == '':
            return None
        # Format: 2025-09-01 12:34:56 sau 2025-09-01
        return pd.to_datetime(str(date_str).split()[0])
    except:
        return None

def find_period_for_date(date_obj, periods_dict):
    """Găsește perioada DP în care se încadrează o dată"""
    if not date_obj:
        return None
    
    for period_key, data in periods_dict.items():
        start = parse_date(data['start'])
        end = parse_date(data['end'])
        
        if start and end and start <= date_obj <= end:
            return period_key
    
    return None

# Procesăm fiecare tip de fișier
file_types = {
    'DC': 'nortia_dc_',
    'DV': 'nortia_dv_',
    'DVS': 'nortia_dvs_',
    'DY': 'nortia_dy_',
    'DCS': 'nortia_dcs_',
    'DCCO': 'nortia_dcco_',
    'DCCD': 'nortia_dccd_',
    'DED': 'nortia_ded_'
}

# Structură pentru a stoca maparea
period_mapping = defaultdict(lambda: {
    'DC': [], 'DV': [], 'DVS': [], 'DY': [], 'DCS': [], 
    'DCCO': [], 'DCCD': [], 'DED': []
})

for file_type, prefix in file_types.items():
    print(f"\n{'='*100}")
    print(f"PROCESARE FIȘIERE {file_type}")
    print(f"{'='*100}")
    
    files = [f for f in os.listdir(folder_emag) if f.startswith(prefix) and f.endswith('.xlsx')]
    
    # Filtrare specială pentru DC (exclude DCCD și DCCO)
    if file_type == 'DC':
        files = [f for f in files if not f.startswith('nortia_dccd_') and not f.startswith('nortia_dcco_')]
    
    for filename in sorted(files):
        file_path = os.path.join(folder_emag, filename)
        print(f"\n📄 {filename}")
        
        try:
            df = pd.read_excel(file_path, dtype=str)
            
            # Verifică ce coloane are - diferite tipuri au coloane diferite
            date_col = None
            if 'Data finalizare comanda' in df.columns:
                date_col = 'Data finalizare comanda'
            elif 'Data stornare comanda' in df.columns:
                date_col = 'Data stornare comanda'
            elif 'Data finalizare retur' in df.columns:
                date_col = 'Data finalizare retur'
            elif 'Data anulare comanda' in df.columns:
                date_col = 'Data anulare comanda'
            
            if not date_col:
                print(f"   ⚠️  Nu am găsit coloana de dată!")
                continue
            
            print(f"   Folosim coloana: {date_col}")
            
            # Grupăm înregistrările după perioadă
            period_counts = defaultdict(lambda: {'count': 0, 'records': []})
            
            for idx, row in df.iterrows():
                date_str = row.get(date_col)
                date_obj = parse_date(date_str)
                
                if date_obj:
                    period_key = find_period_for_date(date_obj, periods)
                    if period_key:
                        period_counts[period_key]['count'] += 1
                        period_counts[period_key]['records'].append(row)
            
            # Afișează distribuția
            if period_counts:
                print(f"   Distribuție pe perioade:")
                for period_key, data in period_counts.items():
                    period_info = periods[period_key]
                    print(f"      → {period_info['start']} → {period_info['end']}: {data['count']} înregistrări")
                    
                    # Adaugă fișierul la mapare
                    period_mapping[period_key][file_type].append({
                        'file': filename,
                        'records': data['records'],
                        'count': data['count']
                    })
            else:
                print(f"   ⚠️  Nicio înregistrare mapată la perioade!")
            
        except Exception as e:
            print(f"   ❌ EROARE: {e}")

# ====================================================================================
# PASUL 3: Calculăm sumele pentru fiecare perioadă
# ====================================================================================
print("\n" + "=" * 100)
print("PASUL 3: CALCUL SUME PENTRU FIECARE PERIOADĂ")
print("=" * 100)

TVA_FACTOR = 1.21  # Pentru septembrie 2025

for period_key in sorted(periods.keys()):
    period_info = periods[period_key]
    print(f"\n{'='*100}")
    print(f"📊 PERIOADĂ: {period_info['start']} → {period_info['end']}")
    print(f"{'='*100}")
    
    # DP total
    dp_total = period_info['dp_total']
    print(f"\n💰 DP Total: {dp_total:.2f} RON")
    
    # DC - Comision
    dc_total = 0
    if period_mapping[period_key]['DC']:
        for file_data in period_mapping[period_key]['DC']:
            print(f"\n   DC: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                comision_net = pd.to_numeric(record.get('Comision Net', 0), errors='coerce')
                if pd.notna(comision_net):
                    dc_total += abs(comision_net)
        dc_cu_tva = dc_total * TVA_FACTOR
        print(f"   DC Total (fără TVA): {dc_total:.2f} RON")
        print(f"   DC Total (cu TVA 21%): {dc_cu_tva:.2f} RON")
    
    # DV - Voucher
    dv_total = 0
    if period_mapping[period_key]['DV']:
        for file_data in period_mapping[period_key]['DV']:
            print(f"\n   DV: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                valoare = pd.to_numeric(record.get('Valoare vouchere', 0), errors='coerce')
                if pd.notna(valoare):
                    dv_total += abs(valoare)
        print(f"   DV Total: {dv_total:.2f} RON")
    
    # DVS - Voucher Stornat
    dvs_total = 0
    if period_mapping[period_key]['DVS']:
        for file_data in period_mapping[period_key]['DVS']:
            print(f"\n   DVS: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                valoare = pd.to_numeric(record.get('Valoare vouchere', 0), errors='coerce')
                if pd.notna(valoare):
                    dvs_total += abs(valoare)
        print(f"   DVS Total: {dvs_total:.2f} RON")
    
    # DY - Discount Voucher (din celula W2)
    dy_total = 0
    if period_mapping[period_key]['DY']:
        for file_data in period_mapping[period_key]['DY']:
            print(f"\n   DY: {file_data['file']} ({file_data['count']} înregistrări)")
            # Pentru DY, citim din celula W2
            try:
                for file_info in period_mapping[period_key]['DY']:
                    file_path = os.path.join(folder_emag, file_info['file'])
                    df_no_header = pd.read_excel(file_path, header=None)
                    if df_no_header.shape[1] > 22 and df_no_header.shape[0] > 1:
                        w2_value = pd.to_numeric(df_no_header.iloc[1, 22], errors='coerce')
                        if pd.notna(w2_value):
                            dy_total += abs(w2_value)
            except:
                pass
        if dy_total > 0:
            dy_cu_tva = dy_total * TVA_FACTOR
            print(f"   DY Total (fără TVA): {dy_total:.2f} RON")
            print(f"   DY Total (cu TVA 21%): {dy_cu_tva:.2f} RON")
    
    # DCS - Comision Stornat (valoare negativă)
    dcs_total = 0
    if period_mapping[period_key]['DCS']:
        for file_data in period_mapping[period_key]['DCS']:
            print(f"\n   DCS: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                comision_net = pd.to_numeric(record.get('Comision Net', 0), errors='coerce')
                if pd.notna(comision_net):
                    dcs_total += comision_net  # Păstrăm semnul negativ
        dcs_cu_tva = dcs_total * TVA_FACTOR
        print(f"   DCS Total (fără TVA): {dcs_total:.2f} RON")
        print(f"   DCS Total (cu TVA 21%): {dcs_cu_tva:.2f} RON")
    
    # DCCO - Comenzi Anulate Card Online
    dcco_total = 0
    if period_mapping[period_key]['DCCO']:
        for file_data in period_mapping[period_key]['DCCO']:
            print(f"\n   DCCO: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                comision_net = pd.to_numeric(record.get('Comision Net', 0), errors='coerce')
                if pd.notna(comision_net):
                    dcco_total += abs(comision_net)
        dcco_cu_tva = dcco_total * TVA_FACTOR
        print(f"   DCCO Total (fără TVA): {dcco_total:.2f} RON")
        print(f"   DCCO Total (cu TVA 21%): {dcco_cu_tva:.2f} RON")
    
    # DCCD - Comenzi Anulate Ramburs
    dccd_total = 0
    if period_mapping[period_key]['DCCD']:
        for file_data in period_mapping[period_key]['DCCD']:
            print(f"\n   DCCD: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                comision_net = pd.to_numeric(record.get('Comision Net', 0), errors='coerce')
                if pd.notna(comision_net):
                    dccd_total += abs(comision_net)
        dccd_cu_tva = dccd_total * TVA_FACTOR
        print(f"   DCCD Total (fără TVA): {dccd_total:.2f} RON")
        print(f"   DCCD Total (cu TVA 21%): {dccd_cu_tva:.2f} RON")
    
    # DED - EasyBox (citește din "Valoare produs", nu "Comision Net")
    ded_total = 0
    if period_mapping[period_key]['DED']:
        for file_data in period_mapping[period_key]['DED']:
            print(f"\n   DED: {file_data['file']} ({file_data['count']} înregistrări)")
            for record in file_data['records']:
                # DED folosește "Valoare produs" în loc de "Comision Net"
                valoare = pd.to_numeric(record.get('Valoare produs', 0), errors='coerce')
                if pd.notna(valoare):
                    ded_total += abs(valoare)
        ded_cu_tva = ded_total * TVA_FACTOR
        print(f"   DED Total (fără TVA): {ded_total:.2f} RON")
        print(f"   DED Total (cu TVA 21%): {ded_cu_tva:.2f} RON")
    
    # CALCUL FINAL
    print(f"\n{'='*100}")
    print(f"📈 CALCUL FINAL PENTRU PERIOADA {period_info['start']} → {period_info['end']}")
    print(f"{'='*100}")
    
    dc_cu_tva = dc_total * TVA_FACTOR
    dy_cu_tva = dy_total * TVA_FACTOR
    dcs_cu_tva = dcs_total * TVA_FACTOR
    dcco_cu_tva = dcco_total * TVA_FACTOR
    dccd_cu_tva = dccd_total * TVA_FACTOR
    ded_cu_tva = ded_total * TVA_FACTOR
    
    # Formula: (DP) + (DV - DVS) - (DC + DCCD + DCCO + DY + DED) + DCS
    rezultat = dp_total + (dv_total - dvs_total) - (dc_cu_tva + dccd_cu_tva + dcco_cu_tva + dy_cu_tva + ded_cu_tva) + dcs_cu_tva
    
    print(f"\nFormula: (DP) + (DV - DVS) - (DC + DCCD + DCCO + DY + DED) + DCS")
    print(f"\n  DP:    {dp_total:>10.2f} RON")
    print(f"  DV:    {dv_total:>10.2f} RON")
    print(f"  DVS:  -{dvs_total:>10.2f} RON")
    print(f"  DC:   -{dc_cu_tva:>10.2f} RON (cu TVA)")
    print(f"  DCCD: -{dccd_cu_tva:>10.2f} RON (cu TVA)")
    print(f"  DCCO: -{dcco_cu_tva:>10.2f} RON (cu TVA)")
    print(f"  DY:   -{dy_cu_tva:>10.2f} RON (cu TVA)")
    print(f"  DED:  -{ded_cu_tva:>10.2f} RON (cu TVA)")
    print(f"  DCS:  +{dcs_cu_tva:>10.2f} RON (cu TVA, negativ)")
    print(f"\n  {'='*40}")
    print(f"  REZULTAT: {rezultat:>10.2f} RON")
    print(f"  {'='*40}")

print("\n" + "=" * 100)
print("TEST COMPLET")
print("=" * 100)
