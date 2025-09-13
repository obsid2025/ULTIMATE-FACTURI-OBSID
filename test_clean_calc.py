"""
Test cu calculul curat pentru perioada 2025-07
folosind doar fișierele din folder-ul principal eMag
"""
import importlib.util
import pandas as pd
import os

# Încarcă modulul cu spațiu în nume
spec = importlib.util.spec_from_file_location("grupare_facturi", "grupare facturi.py")
grupare_facturi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grupare_facturi)

FacturiApp = grupare_facturi.FacturiApp

def test_clean_emag_calculation():
    print("=== TEST CALCULULUI CURAT EMAG (DOAR FOLDER PRINCIPAL) ===")

    app = FacturiApp()

    # Modificăm temporar metoda pentru a exclude folder-ul eMag 2
    original_method = app._calculeaza_emag_pe_perioade

    def calcul_doar_folder_principal(folder_emag, erori):
        """Calculează doar cu fișierele din folder-ul principal"""

        tva_rates = {
            "2025-07": 1.19,
            "2025-08": 1.21,
            "2025-09": 1.21,
        }

        def get_file_period(file_path, file_type):
            try:
                if file_type == 'dp':
                    df = pd.read_excel(file_path, dtype=str)
                    if 'Reference period start' in df.columns and len(df) > 0:
                        period_start = pd.to_datetime(df['Reference period start'].iloc[0])
                        return f"{period_start.year}-{period_start.month:02d}"
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
                                    return f"{year.group()}-{month_num}"
            except Exception as e:
                print(f"Eroare la determinarea perioadei pentru {file_path}: {e}")

            import re
            match = re.search(r'(\d{2})(\d{4})', os.path.basename(file_path))
            if match:
                month = match.group(1)
                year = match.group(2)
                return f"{year}-{month}"
            return None

        # Procesează DOAR folder-ul principal
        periods = {}
        for file in os.listdir(folder_emag):
            if not file.endswith('.xlsx'):
                continue

            file_path = os.path.join(folder_emag, file)
            file_type = None

            if file.startswith('nortia_dp_'):
                file_type = 'dp'
            elif file.startswith('nortia_dcco_'):
                file_type = 'dcco'
            elif file.startswith('nortia_dccd_'):
                file_type = 'dccd'
            elif file.startswith('nortia_dc_') and not file.startswith('nortia_dccd_') and not file.startswith('nortia_dcco_'):
                file_type = 'dc'
            elif file.startswith('nortia_ded_'):
                file_type = 'ded'
            elif file.startswith('nortia_dv_'):
                file_type = 'dv'
            elif file.startswith('nortia_dcs_'):
                file_type = 'dcs'

            if file_type:
                period = get_file_period(file_path, file_type)
                if period:
                    if period not in periods:
                        periods[period] = {
                            'dp': [], 'dcco': [], 'dccd': [],
                            'dc': [], 'ded': [], 'dv': [], 'dcs': []
                        }
                    periods[period][file_type].append(file_path)
                    print(f"  Adaugat {file_type.upper()}: {file} -> perioada {period}")

        results = []
        for period, files in sorted(periods.items()):
            if period != "2025-07":  # Testez doar perioada 2025-07
                continue

            print(f"\n=== CALCUL PERIOADA {period} (DOAR FOLDER PRINCIPAL) ===")

            # DP Total
            dp_total = 0
            for file_path in files.get('dp', []):
                df = pd.read_excel(file_path, dtype=str)
                if 'Fraction value' in df.columns:
                    values = pd.to_numeric(df['Fraction value'], errors='coerce')
                    file_total = values.sum()
                    dp_total += file_total
                    print(f"DP {os.path.basename(file_path)}: {file_total:.2f}")

            # DV Total
            dv_total = 0
            for file_path in files.get('dv', []):
                df = pd.read_excel(file_path, dtype=str)
                if 'Valoare vouchere' in df.columns:
                    values = pd.to_numeric(df['Valoare vouchere'], errors='coerce')
                    file_total = values.sum()
                    dv_total += file_total
                    print(f"DV {os.path.basename(file_path)}: {file_total:.2f}")

            tva_rate = tva_rates.get(period, 1.21)

            # Comisioane
            dcco_total = 0
            for file_path in files.get('dcco', []):
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 19 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        dcco_total += total
                        print(f"DCCO {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")

            dccd_total = 0
            for file_path in files.get('dccd', []):
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 19 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        dccd_total += total
                        print(f"DCCD {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")

            dc_total = 0
            for file_path in files.get('dc', []):
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 19 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        dc_total += total
                        print(f"DC {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")

            ded_total = 0
            for file_path in files.get('ded', []):
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 12 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 12], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        ded_total += total
                        print(f"DED {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")

            dcs_total = 0
            for file_path in files.get('dcs', []):
                df = pd.read_excel(file_path, dtype=str)
                if 'Comision Net' in df.columns:
                    values = pd.to_numeric(df['Comision Net'], errors='coerce')
                    if len(values) > 0:
                        first_value = values.iloc[0] if not pd.isna(values.iloc[0]) else 0
                        total = abs(first_value) * tva_rate
                        dcs_total += total
                        print(f"DCS {os.path.basename(file_path)}: {first_value:.2f} * {tva_rate} = -{total:.2f} (primul rand)")

            # Formula: DP + DV - (DCCO + DCCD + DC + DED) + DCS
            comisioane_fara_dcs = dcco_total + dccd_total + dc_total + ded_total
            total_final = dp_total + dv_total - comisioane_fara_dcs + dcs_total

            print(f"\n--- REZULTAT FINAL {period} ---")
            print(f"DP Total: {dp_total:.2f}")
            print(f"DV Total: {dv_total:.2f}")
            print(f"Comisioane (fara DCS): -{comisioane_fara_dcs:.2f}")
            print(f"DCS (se aduna): +{dcs_total:.2f}")
            print(f"Formula: {dp_total:.2f} + {dv_total:.2f} - {comisioane_fara_dcs:.2f} + {dcs_total:.2f}")
            print(f"TOTAL FINAL: {total_final:.2f}")

            expected = 6051.51
            if abs(total_final - expected) < 0.1:
                print(f"REZULTAT CORECT! (asteptat: {expected:.2f})")
            else:
                print(f"REZULTAT DIFERIT! (asteptat: {expected:.2f}, obtinut: {total_final:.2f})")

        return results

    # Testează cu calculul modificat
    folder_emag = r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag"
    erori = []
    rezultate = calcul_doar_folder_principal(folder_emag, erori)

if __name__ == "__main__":
    test_clean_emag_calculation()