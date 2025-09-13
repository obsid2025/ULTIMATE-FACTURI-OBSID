"""
Test cu fișierele EXACTE specificate de utilizator pentru perioada 2025-07
"""
import pandas as pd
import os

def calculate_exact_period_072025():
    """Calculează perioada 2025-07 cu fișierele exacte specificate"""

    print("=== CALCUL EXACT PENTRU PERIOADA 2025-07 ===")

    # Fișierele exacte specificate
    files = {
        # DP files
        'dp1': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dp_12823661_02_08_2025 (4).xlsx",
        'dp2': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dp_12823666_02_08_2025 (8).xlsx",

        # DV file
        'dv': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dv_072025_1754104697_v1 (2).xlsx",

        # Commission files
        'dcco': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dcco_072025_1754104695_v1 (3).xlsx",
        'dccd': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dccd_072025_1754104695_v1 (2).xlsx",
        'dc': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dc_072025_1754104695_v1 (2).xlsx",
        'ded': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_ded_072025_1754104696_v1 (2).xlsx",
        'dcs': r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag\nortia_dcs_072025_1754104699_v1 (3).xlsx"
    }

    # Verifică existența fișierelor
    for name, path in files.items():
        if not os.path.exists(path):
            print(f"EROARE: Nu exista fisierul {name}: {path}")
            return

    print("Toate fisierele exista. Incepe calculul...")

    # 1. Calculează DP total
    dp_total = 0
    for name in ['dp1', 'dp2']:
        df = pd.read_excel(files[name], dtype=str)
        if 'Fraction value' in df.columns:
            values = pd.to_numeric(df['Fraction value'], errors='coerce')
            file_total = values.sum()
            dp_total += file_total
            print(f"DP {name}: {file_total:.2f}")

    print(f"DP TOTAL: {dp_total:.2f}")

    # 2. Calculează DV (Valoare vouchere - toată coloana X)
    df_dv = pd.read_excel(files['dv'], dtype=str)
    if 'Valoare vouchere' in df_dv.columns:
        dv_values = pd.to_numeric(df_dv['Valoare vouchere'], errors='coerce')
        dv_total = dv_values.sum()
        print(f"DV TOTAL: {dv_total:.2f}")
        print(f"  Valori individuale DV: {dv_values.dropna().tolist()}")
    else:
        dv_total = 0
        print("DV TOTAL: 0.00 (nu am gasit coloana)")

    # 3. Calculează comisioanele (TVA 19% pentru iulie 2025)
    tva_rate = 1.19

    # DCCO - T2
    df_dcco = pd.read_excel(files['dcco'], header=None)
    dcco_net = pd.to_numeric(df_dcco.iloc[1, 19], errors='coerce')  # T2
    dcco_tva = abs(dcco_net) * tva_rate
    print(f"DCCO: {abs(dcco_net):.2f} * {tva_rate} = {dcco_tva:.2f}")

    # DCCD - T2
    df_dccd = pd.read_excel(files['dccd'], header=None)
    dccd_net = pd.to_numeric(df_dccd.iloc[1, 19], errors='coerce')  # T2
    dccd_tva = abs(dccd_net) * tva_rate
    print(f"DCCD: {abs(dccd_net):.2f} * {tva_rate} = {dccd_tva:.2f}")

    # DC - T2
    df_dc = pd.read_excel(files['dc'], header=None)
    dc_net = pd.to_numeric(df_dc.iloc[1, 19], errors='coerce')  # T2
    dc_tva = abs(dc_net) * tva_rate
    print(f"DC: {abs(dc_net):.2f} * {tva_rate} = {dc_tva:.2f}")

    # DED - M2 (Valoare produs)
    df_ded = pd.read_excel(files['ded'], header=None)
    ded_net = pd.to_numeric(df_ded.iloc[1, 12], errors='coerce')  # M2
    ded_tva = abs(ded_net) * tva_rate
    print(f"DED: {abs(ded_net):.2f} * {tva_rate} = {ded_tva:.2f}")

    # DCS - Comision Net (coloana D sau prin header)
    df_dcs = pd.read_excel(files['dcs'], dtype=str)
    print(f"DCS file columns: {df_dcs.columns.tolist()}")
    print(f"DCS file shape: {df_dcs.shape}")
    print(f"DCS first few rows:\n{df_dcs.head()}")

    if 'Comision Net' in df_dcs.columns:
        dcs_values = pd.to_numeric(df_dcs['Comision Net'], errors='coerce')
        dcs_net = dcs_values.sum()
        print(f"DCS values (prin header): {dcs_values.dropna().tolist()}")
    else:
        # Fallback pe coloana D
        dcs_values = pd.to_numeric(df_dcs.iloc[1:, 3], errors='coerce')
        dcs_net = dcs_values.sum()
        print(f"DCS values (prin index D): {dcs_values.dropna().tolist()}")

    dcs_tva = abs(dcs_net) * tva_rate  # e negativ (storno)
    print(f"DCS: {dcs_net:.2f} * {tva_rate} = -{dcs_tva:.2f} (storno)")
    print(f"User expected: -54.87 * 1.19 = -65.30")

    # 4. Calculul final: DP + DV - (DCCO + DCCD + DC + DED + DCS)
    # IMPORTANT: DCS este storno (negativ), deci când îl scădem devine pozitiv
    # Formula: DP + DV - (DCCO + DCCD + DC + DED - DCS)
    # Sau: DP + DV - DCCO - DCCD - DC - DED + DCS

    print(f"\nAnaliza DCS:")
    print(f"  DCS net total: {dcs_net:.2f}")
    print(f"  DCS cu TVA: {dcs_net * tva_rate:.2f}")
    print(f"  Utilizator asteptat doar primul rand: -54.87 * 1.19 = -65.30")

    # Testez ambele variante:
    # Varianta 1: Cu toate valorile DCS
    comisioane_total_v1 = dcco_tva + dccd_tva + dc_tva + ded_tva + dcs_tva
    total_final_v1 = dp_total + dv_total - comisioane_total_v1

    # Varianta 2: Cu doar primul rând DCS
    dcs_first_only = -54.87 * tva_rate
    comisioane_total_v2 = dcco_tva + dccd_tva + dc_tva + ded_tva + abs(dcs_first_only)
    total_final_v2 = dp_total + dv_total - comisioane_total_v2

    # Varianta 3: DCS se adună (conform formulei utilizatorului)
    comisioane_fara_dcs = dcco_tva + dccd_tva + dc_tva + ded_tva
    total_final_v3 = dp_total + dv_total - comisioane_fara_dcs + abs(dcs_net * tva_rate)

    # Varianta 4: Calculul manual exact al utilizatorului
    manual_calc = 4317.64 + 4157.44 + 174.25 - (335.82 + 171.56 + 2139.67 + 16.07 + (-65.30))
    print(f"V4 (calcul manual utilizator): {manual_calc:.2f}")

    # Să verific valorile mele vs. valorile utilizatorului
    print(f"\nComparatie valori:")
    print(f"DED: eu={ded_tva:.2f}, user=16.07 (diferenta: {abs(ded_tva-16.07):.2f})")
    print(f"DCS: eu={abs(dcs_net * tva_rate):.2f}, user=65.30 (diferenta: {abs(abs(dcs_net * tva_rate)-65.30):.2f})")

    print(f"\nTestez 3 variante:")
    print(f"V1 (toate DCS): {total_final_v1:.2f}")
    print(f"V2 (doar primul DCS): {total_final_v2:.2f}")
    print(f"V3 (DCS se aduna): {total_final_v3:.2f}")

    comisioane_total = comisioane_total_v1
    total_final = total_final_v1

    print(f"\n=== REZULTAT FINAL ===")
    print(f"DP Total: {dp_total:.2f}")
    print(f"DV Total: {dv_total:.2f}")
    print(f"DCCO: -{dcco_tva:.2f}")
    print(f"DCCD: -{dccd_tva:.2f}")
    print(f"DC: -{dc_tva:.2f}")
    print(f"DED: -{ded_tva:.2f}")
    print(f"DCS: -{dcs_tva:.2f} (storno)")
    print(f"Comisioane totale: -{comisioane_total:.2f}")
    print(f"")
    print(f"FORMULA: {dp_total:.2f} + {dv_total:.2f} - {comisioane_total:.2f} = {total_final:.2f}")
    print(f"")
    print(f"TOTAL FINAL: {total_final:.2f} RON")

    # Verifică dacă rezultatul e cel așteptat
    expected = 6051.51
    if abs(total_final - expected) < 0.1:
        print(f"REZULTAT CORECT! (asteptat: {expected:.2f})")
    else:
        print(f"REZULTAT DIFERIT! (asteptat: {expected:.2f}, obtinut: {total_final:.2f})")

if __name__ == "__main__":
    calculate_exact_period_072025()