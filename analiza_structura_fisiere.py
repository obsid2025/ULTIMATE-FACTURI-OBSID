"""
Script pentru analiza structurii fișierelor eMag și găsirea metodei optime de mapare
"""
import pandas as pd
import os
from datetime import datetime

folder_emag = "9 septembrie/eMag"

print("=" * 100)
print("ANALIZA STRUCTURII FIȘIERELOR eMag")
print("=" * 100)

# ====================================================================================
# 1. ANALIZA FIȘIERELOR DP (Plăți)
# ====================================================================================
print("\n" + "=" * 100)
print("1. STRUCTURA FIȘIERELOR DP (Desfășurător Plată)")
print("=" * 100)

dp_files = [f for f in os.listdir(folder_emag) if f.startswith('nortia_dp_') and f.endswith('.xlsx')]

for dp_file in sorted(dp_files)[:2]:  # Analizăm primele 2 fișiere
    print(f"\n--- Fișier: {dp_file} ---")
    file_path = os.path.join(folder_emag, dp_file)
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        print(f"Coloane disponibile ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\nNumăr de rânduri: {len(df)}")
        print(f"\nPrimele 3 rânduri (valori selectate):")
        cols_to_show = ['Order ID', 'Reference period start', 'Reference period end', 'Fraction value']
        available_cols = [c for c in cols_to_show if c in df.columns]
        if available_cols:
            print(df[available_cols].head(3).to_string(index=False))
        
        # Verifică Order ID-uri unice
        if 'Order ID' in df.columns:
            unique_orders = df['Order ID'].nunique()
            total_orders = len(df)
            print(f"\nOrder ID-uri unice: {unique_orders} din {total_orders} rânduri")
            print(f"Primele 5 Order ID-uri: {df['Order ID'].head(5).tolist()}")
        
        # Verifică perioada de referință
        if 'Reference period start' in df.columns and 'Reference period end' in df.columns:
            period_start = df['Reference period start'].iloc[0]
            period_end = df['Reference period end'].iloc[0]
            print(f"\nPerioadă de referință: {period_start} până la {period_end}")
        
    except Exception as e:
        print(f"EROARE la citirea fișierului: {e}")

# ====================================================================================
# 2. ANALIZA FIȘIERELOR DC (Comision)
# ====================================================================================
print("\n" + "=" * 100)
print("2. STRUCTURA FIȘIERELOR DC (Comision)")
print("=" * 100)

dc_files = [f for f in os.listdir(folder_emag) 
            if f.startswith('nortia_dc_') and not f.startswith('nortia_dccd_') 
            and not f.startswith('nortia_dcco_') and f.endswith('.xlsx')]

for dc_file in sorted(dc_files)[:2]:
    print(f"\n--- Fișier: {dc_file} ---")
    file_path = os.path.join(folder_emag, dc_file)
    
    try:
        # Citește cu header
        df_header = pd.read_excel(file_path, dtype=str)
        print(f"Coloane cu header ({len(df_header.columns)}):")
        for i, col in enumerate(df_header.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\nNumăr de rânduri: {len(df_header)}")
        
        # Verifică dacă are Order ID
        if 'Order ID' in df_header.columns:
            print(f"\nAre coloana 'Order ID'!")
            unique_orders = df_header['Order ID'].nunique()
            print(f"Order ID-uri unice: {unique_orders}")
            print(f"Primele 5 Order ID-uri: {df_header['Order ID'].head(5).tolist()}")
        
        # Verifică Luna
        if 'Luna' in df_header.columns:
            luna = df_header['Luna'].iloc[0] if len(df_header) > 0 else 'N/A'
            print(f"\nLuna: {luna}")
        
        # Arată primele 3 rânduri complet
        print(f"\nPrimele 3 rânduri:")
        cols_to_show = ['Order ID', 'Luna', 'Comision Net'] if all(c in df_header.columns for c in ['Order ID', 'Luna', 'Comision Net']) else df_header.columns[:5]
        print(df_header[cols_to_show].head(3).to_string(index=False))
        
    except Exception as e:
        print(f"EROARE la citirea fișierului: {e}")

# ====================================================================================
# 3. ANALIZA FIȘIERELOR DV (Voucher)
# ====================================================================================
print("\n" + "=" * 100)
print("3. STRUCTURA FIȘIERELOR DV (Voucher)")
print("=" * 100)

dv_files = [f for f in os.listdir(folder_emag) if f.startswith('nortia_dv_') and f.endswith('.xlsx')]

for dv_file in sorted(dv_files)[:2]:
    print(f"\n--- Fișier: {dv_file} ---")
    file_path = os.path.join(folder_emag, dv_file)
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        print(f"Coloane disponibile ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\nNumăr de rânduri: {len(df)}")
        
        # Verifică Order ID
        if 'Order ID' in df.columns:
            print(f"\nAre coloana 'Order ID'!")
            unique_orders = df['Order ID'].nunique()
            print(f"Order ID-uri unice: {unique_orders}")
            print(f"Primele 5 Order ID-uri: {df['Order ID'].head(5).tolist()}")
        
        # Verifică Luna
        if 'Luna' in df.columns:
            luna = df['Luna'].iloc[0] if len(df) > 0 else 'N/A'
            print(f"\nLuna: {luna}")
        
        # Arată primele 3 rânduri
        cols_to_show = ['Order ID', 'Luna', 'Valoare vouchere'] if all(c in df.columns for c in ['Order ID', 'Luna', 'Valoare vouchere']) else df.columns[:5]
        print(f"\nPrimele 3 rânduri:")
        print(df[cols_to_show].head(3).to_string(index=False))
        
    except Exception as e:
        print(f"EROARE la citirea fișierului: {e}")

# ====================================================================================
# 4. ANALIZA FIȘIERELOR DVS (Voucher Stornat)
# ====================================================================================
print("\n" + "=" * 100)
print("4. STRUCTURA FIȘIERELOR DVS (Voucher Stornat)")
print("=" * 100)

dvs_files = [f for f in os.listdir(folder_emag) if f.startswith('nortia_dvs_') and f.endswith('.xlsx')]

for dvs_file in sorted(dvs_files):
    print(f"\n--- Fișier: {dvs_file} ---")
    file_path = os.path.join(folder_emag, dvs_file)
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        print(f"Coloane disponibile ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\nNumăr de rânduri: {len(df)}")
        
        # Verifică Order ID
        if 'Order ID' in df.columns:
            print(f"\nOrder ID-uri: {df['Order ID'].tolist()}")
        
        # Verifică Luna
        if 'Luna' in df.columns:
            luna = df['Luna'].iloc[0] if len(df) > 0 else 'N/A'
            print(f"Luna: {luna}")
        
        # Arată toate rândurile (ar trebui să fie puține)
        cols_to_show = ['Order ID', 'Luna', 'Valoare vouchere', 'Comision Net'] if all(c in df.columns for c in ['Order ID', 'Luna', 'Valoare vouchere', 'Comision Net']) else df.columns[:6]
        print(f"\nToate rândurile:")
        print(df[cols_to_show].to_string(index=False))
        
    except Exception as e:
        print(f"EROARE la citirea fișierului: {e}")

# ====================================================================================
# 5. ANALIZA FIȘIERELOR DY (Discount Voucher)
# ====================================================================================
print("\n" + "=" * 100)
print("5. STRUCTURA FIȘIERELOR DY (Discount Voucher)")
print("=" * 100)

dy_files = [f for f in os.listdir(folder_emag) if f.startswith('nortia_dy_') and f.endswith('.xlsx')]

for dy_file in sorted(dy_files):
    print(f"\n--- Fișier: {dy_file} ---")
    file_path = os.path.join(folder_emag, dy_file)
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        print(f"Coloane disponibile ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\nNumăr de rânduri: {len(df)}")
        
        # Verifică Order ID
        if 'Order ID' in df.columns:
            print(f"\nOrder ID-uri: {df['Order ID'].tolist()}")
        
        # Verifică Luna
        if 'Luna' in df.columns:
            luna = df['Luna'].iloc[0] if len(df) > 0 else 'N/A'
            print(f"Luna: {luna}")
        
        # Arată toate rândurile
        cols_to_show = ['Order ID', 'Luna', 'Valoare vouchere'] if all(c in df.columns for c in ['Order ID', 'Luna', 'Valoare vouchere']) else df.columns[:6]
        print(f"\nToate rândurile:")
        print(df[cols_to_show].to_string(index=False))
        
        # Verifică celula W2
        print(f"\nValoare din celula W2 (coloana 22, rând 1):")
        df_no_header = pd.read_excel(file_path, header=None)
        if df_no_header.shape[1] > 22 and df_no_header.shape[0] > 1:
            print(f"  W2 = {df_no_header.iloc[1, 22]}")
        
    except Exception as e:
        print(f"EROARE la citirea fișierului: {e}")

# ====================================================================================
# 6. ANALIZA FIȘIERELOR DCS (Comision Stornat)
# ====================================================================================
print("\n" + "=" * 100)
print("6. STRUCTURA FIȘIERELOR DCS (Comision Stornat)")
print("=" * 100)

dcs_files = [f for f in os.listdir(folder_emag) if f.startswith('nortia_dcs_') and f.endswith('.xlsx')]

for dcs_file in sorted(dcs_files):
    print(f"\n--- Fișier: {dcs_file} ---")
    file_path = os.path.join(folder_emag, dcs_file)
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        print(f"Coloane disponibile ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\nNumăr de rânduri: {len(df)}")
        
        # Verifică Order ID
        if 'Order ID' in df.columns:
            print(f"\nOrder ID-uri: {df['Order ID'].tolist()}")
        
        # Verifică Luna
        if 'Luna' in df.columns:
            luna = df['Luna'].iloc[0] if len(df) > 0 else 'N/A'
            print(f"Luna: {luna}")
        
        # Arată toate rândurile
        cols_to_show = ['Order ID', 'Luna', 'Comision Net'] if all(c in df.columns for c in ['Order ID', 'Luna', 'Comision Net']) else df.columns[:6]
        print(f"\nToate rândurile:")
        print(df[cols_to_show].to_string(index=False))
        
    except Exception as e:
        print(f"EROARE la citirea fișierului: {e}")

print("\n" + "=" * 100)
print("ANALIZA COMPLETĂ")
print("=" * 100)
