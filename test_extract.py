# -*- coding: utf-8 -*-
import pandas as pd
import os
import glob

print("="*70)
print("VERIFICARE EXTRAGERE DATE DIN FISIERE EMAG - PERIOADA 01-15 SEPTEMBRIE")
print("="*70)

# TVA 21% pentru septembrie 2025
TVA = 1.21

# 1. DV - Vouchere
print("\n1. DV - VOUCHERE")
print("-" * 70)
dv_file = r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_dv_092025_1758102020_v1.xlsx'
df = pd.read_excel(dv_file)
filename = os.path.basename(dv_file)
print(f"Fisier: {filename}")

if 'Valoare vouchere' in df.columns:
    valori = df['Valoare vouchere'].dropna()
    print(f"Valori individuale din coloana 'Valoare vouchere':")
    for v in valori:
        if pd.notna(v) and str(v).strip():
            print(f"  {v}")
    dv_total = valori.sum()
    print(f"\nTOTAL DV: {dv_total:.2f} RON")
else:
    print("EROARE: Coloana 'Valoare vouchere' nu exista!")
    dv_total = 0

# 2. DVS - Vouchere Storno
print("\n2. DVS - VOUCHERE STORNO")
print("-" * 70)
dvs_file = r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_dvs_092025_1758102393_v1.xlsx'
df = pd.read_excel(dvs_file)
filename = os.path.basename(dvs_file)
print(f"Fisier: {filename}")

if 'Valoare vouchere' in df.columns:
    valori = df['Valoare vouchere'].dropna()
    print(f"Valori individuale din coloana 'Valoare vouchere':")
    for v in valori:
        if pd.notna(v) and str(v).strip():
            print(f"  {v}")
    dvs_total = valori.sum()
    print(f"\nTOTAL DVS: {dvs_total:.2f} RON")
else:
    print("EROARE: Coloana 'Valoare vouchere' nu exista!")
    dvs_total = 0

# 3. DC - Comision (TOATE fisierele)
print("\n3. DC - COMISION (toate fisierele)")
print("-" * 70)
dc_files = glob.glob(r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_dc_092025_*.xlsx')
dc_total = 0
for dc_file in dc_files:
    df = pd.read_excel(dc_file, header=None)
    filename = os.path.basename(dc_file)
    if df.shape[1] > 19 and df.shape[0] > 1:
        dc_net = pd.to_numeric(df.iloc[1, 19], errors='coerce')
        dc_cu_tva = abs(dc_net) * TVA
        print(f"{filename}: NET={abs(dc_net):.2f}, cu TVA={dc_cu_tva:.2f}")
        dc_total += dc_cu_tva
    else:
        print(f"{filename}: EROARE - nu are suficiente coloane/randuri!")

print(f"\nTOTAL DC (cu TVA 21%): {dc_total:.2f} RON")

# 4. DCCD - Comision Comenzi Anulate (TOATE fisierele)
print("\n4. DCCD - COMISION COMENZI ANULATE (toate fisierele)")
print("-" * 70)
dccd_files = glob.glob(r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_dccd_092025_*.xlsx')
dccd_total = 0
for dccd_file in dccd_files:
    df = pd.read_excel(dccd_file, header=None)
    filename = os.path.basename(dccd_file)
    if df.shape[1] > 19 and df.shape[0] > 1:
        dccd_net = pd.to_numeric(df.iloc[1, 19], errors='coerce')
        dccd_cu_tva = abs(dccd_net) * TVA
        print(f"{filename}: NET={abs(dccd_net):.2f}, cu TVA={dccd_cu_tva:.2f}")
        dccd_total += dccd_cu_tva
    else:
        print(f"{filename}: EROARE - nu are suficiente coloane/randuri!")

print(f"\nTOTAL DCCD (cu TVA 21%): {dccd_total:.2f} RON")

# 5. DCS - Comision Storno
print("\n5. DCS - COMISION STORNO")
print("-" * 70)
dcs_file = r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_dcs_092025_1758102265_v1.xlsx'
df = pd.read_excel(dcs_file, header=None)
filename = os.path.basename(dcs_file)
print(f"Fisier: {filename}")

if df.shape[1] > 19 and df.shape[0] > 1:
    dcs_net = pd.to_numeric(df.iloc[1, 19], errors='coerce')
    dcs_cu_tva = abs(dcs_net) * TVA
    print(f"DCS NET: {abs(dcs_net):.2f} RON")
    print(f"DCS cu TVA (21%): {abs(dcs_net):.2f} * {TVA} = {dcs_cu_tva:.2f} RON")
else:
    print("EROARE: Fisierul nu are suficiente coloane/randuri!")
    dcs_cu_tva = 0

# 6. DY - Discount Voucher (TOATE fisierele)
print("\n6. DY - DISCOUNT VOUCHER (toate fisierele)")
print("-" * 70)
dy_files = glob.glob(r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_dy_092025_*.xlsx')
dy_total = 0
for dy_file in dy_files:
    df = pd.read_excel(dy_file, header=None)
    filename = os.path.basename(dy_file)
    if df.shape[1] > 22 and df.shape[0] > 1:  # W = index 22, deci trebuie > 22
        dy_val = pd.to_numeric(df.iloc[1, 22], errors='coerce')
        print(f"{filename}: valoare W2 = {abs(dy_val):.2f} RON (deja cu TVA)")
        dy_total += abs(dy_val)
    else:
        print(f"{filename}: EROARE - nu are suficiente coloane ({df.shape[1]}) sau randuri ({df.shape[0]})")

print(f"\nTOTAL DY: {dy_total:.2f} RON")

# 7. DED - Alte Facturi
print("\n7. DED - ALTE FACTURI")
print("-" * 70)
ded_file = r'C:\Development\Python\Ultimate_FACTURI\9 septembrie\eMag\nortia_ded_092025_1758101891_v1.xlsx'
df = pd.read_excel(ded_file, header=None)
filename = os.path.basename(ded_file)
print(f"Fisier: {filename}")

if df.shape[1] > 10 and df.shape[0] > 1:  # M = index 12, dar verific 10 pentru siguranta
    # Verific mai multe coloane posibile pentru DED
    print(f"Numar coloane: {df.shape[1]}")
    print(f"Valoare M2 (index [1,12]): {df.iloc[1, 12] if df.shape[1] > 12 else 'N/A'}")

    if df.shape[1] > 12:
        ded_net = pd.to_numeric(df.iloc[1, 12], errors='coerce')
        ded_cu_tva = abs(ded_net) * TVA
        print(f"DED NET: {abs(ded_net):.2f} RON")
        print(f"DED cu TVA (21%): {abs(ded_net):.2f} * {TVA} = {ded_cu_tva:.2f} RON")
    else:
        # Fallback - poate e in alta coloana
        ded_net = pd.to_numeric(df.iloc[1, 10], errors='coerce')
        ded_cu_tva = abs(ded_net) * TVA
        print(f"DED NET (din coloana K): {abs(ded_net):.2f} RON")
        print(f"DED cu TVA (21%): {abs(ded_net):.2f} * {TVA} = {ded_cu_tva:.2f} RON")
else:
    print("EROARE: Fisierul nu are suficiente coloane/randuri!")
    ded_cu_tva = 0

# CALCUL FINAL
print("\n" + "="*70)
print("CALCUL FINAL")
print("="*70)
print(f"DP (din fisierele DP):           5,412.47 RON (manual verificat)")
print(f"DV:                            + {dv_total:.2f} RON")
print(f"DVS:                           - {dvs_total:.2f} RON")
print(f"DC (cu TVA 21%):               - {dc_total:.2f} RON")
print(f"DCCD (cu TVA 21%):             - {dccd_total:.2f} RON")
print(f"DCS (cu TVA 21%):              + {dcs_cu_tva:.2f} RON")
print(f"DY (cu TVA inclus):            - {dy_total:.2f} RON")
print(f"DED (cu TVA 21%):              - {ded_cu_tva:.2f} RON")

print("\n" + "-"*70)
print("Formula: DP + (DV - DVS) - (DC + DCCD - DCS) - (DY + DED)")
print("-"*70)

dp = 5412.47
vouchere_net = dv_total - dvs_total
comision_net = dc_total + dccd_total - dcs_cu_tva
alte_facturi = dy_total + ded_cu_tva

print(f"\nDP:                    {dp:.2f}")
print(f"(DV - DVS):          + {vouchere_net:.2f}")
print(f"(DC + DCCD - DCS):   - {comision_net:.2f}")
print(f"(DY + DED):          - {alte_facturi:.2f}")

total_calculat = dp + vouchere_net - comision_net - alte_facturi

print(f"\n{'='*70}")
print(f"TOTAL CALCULAT:        {total_calculat:.2f} RON")
print(f"TOTAL ASTEPTAT:        3,786.15 RON")
print(f"DIFERENTA:             {abs(total_calculat - 3786.15):.2f} RON")
print(f"{'='*70}")

print("\n\nVerificare cu valorile din mesaj:")
print("(3,542.88 + 1,869.59) + (199.87 - 5.95) - (1,553.68 + 192.18 - 96.84) - (153.07 + 18.15)")
print("= 5,412.47 + 193.92 - 1,649.02 - 171.22")
print("= 3,786.15 RON")
