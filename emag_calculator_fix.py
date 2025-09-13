"""
Modul de calcul eMag îmbunătățit cu grupare pe perioade
Formula: DP + DV - (DCCO + DCCD + DC + DED + DCS)
"""

import os
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class EmagCalculator:
    def __init__(self):
        self.tva_rates = {
            "2025-07": 1.19,  # TVA 19% pentru iulie
            "2025-08": 1.21,  # TVA 21% pentru august și ulterior
            "2025-09": 1.21,
        }

    def get_file_period(self, file_path: str, file_type: str) -> Optional[str]:
        """Determină perioada unui fișier eMag bazat pe tipul său"""
        try:
            if file_type == 'dp':
                # Pentru DP, citește Reference period start/end
                df = pd.read_excel(file_path, dtype=str)
                if 'Reference period start' in df.columns and len(df) > 0:
                    period_start = pd.to_datetime(df['Reference period start'].iloc[0])
                    # Determinăm luna și anul pentru grupare
                    return f"{period_start.year}-{period_start.month:02d}"
            else:
                # Pentru DC, DCCO, DV, etc - citește coloana Luna
                df = pd.read_excel(file_path, dtype=str)
                if 'Luna' in df.columns and len(df) > 0:
                    luna_text = str(df['Luna'].iloc[0]).strip()
                    # Parsează "iulie 2025" -> "2025-07"
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

        # Fallback: încearcă să extragă din numele fișierului
        match = re.search(r'(\d{2})(\d{4})', os.path.basename(file_path))
        if match:
            month = match.group(1)
            year = match.group(2)
            return f"{year}-{month}"

        return None

    def group_files_by_period(self, folder_path: str) -> Dict[str, Dict[str, List[str]]]:
        """Grupează fișierele eMag pe perioade de raportare"""
        periods = {}

        for file in os.listdir(folder_path):
            if not file.endswith('.xlsx'):
                continue

            file_path = os.path.join(folder_path, file)
            file_type = None

            # Determină tipul fișierului
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
                period = self.get_file_period(file_path, file_type)
                if period:
                    if period not in periods:
                        periods[period] = {
                            'dp': [], 'dcco': [], 'dccd': [],
                            'dc': [], 'ded': [], 'dv': [], 'dcs': []
                        }
                    periods[period][file_type].append(file_path)

        return periods

    def calculate_dp_total(self, dp_files: List[str]) -> float:
        """Calculează totalul din fișierele DP"""
        total = 0.0
        for file_path in dp_files:
            try:
                df = pd.read_excel(file_path, dtype=str)
                if 'Fraction value' in df.columns:
                    # Convertește valorile la numeric și sumează
                    values = pd.to_numeric(df['Fraction value'], errors='coerce')
                    total += values.sum()
                    print(f"DP {os.path.basename(file_path)}: {values.sum():.2f}")
            except Exception as e:
                print(f"Eroare la procesarea DP {file_path}: {e}")
        return total

    def calculate_dv_total(self, dv_files: List[str]) -> float:
        """Calculează totalul voucher-elor din fișierele DV"""
        total = 0.0
        for file_path in dv_files:
            try:
                df = pd.read_excel(file_path, dtype=str)
                # Coloana X (index 23) - Valoare vouchere
                if df.shape[1] > 23:
                    # Sări peste header și sumează toate valorile
                    values = pd.to_numeric(df.iloc[1:, 23], errors='coerce')
                    total += values.sum()
                    print(f"DV {os.path.basename(file_path)}: {values.sum():.2f}")
            except Exception as e:
                print(f"Eroare la procesarea DV {file_path}: {e}")
        return total

    def calculate_commission_with_tva(self, file_path: str, file_type: str, period: str) -> float:
        """Calculează comisionul cu TVA pentru un fișier"""
        try:
            tva_rate = self.tva_rates.get(period, 1.21)  # Default 21% pentru perioade noi

            if file_type == 'dc':
                # Coloana T (index 19), rândul 2
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 19 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        print(f"DC {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")
                        return total

            elif file_type == 'dcco':
                # Coloana T (index 19), rândul 2
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 19 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        print(f"DCCO {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")
                        return total

            elif file_type == 'dccd':
                # Coloana T (index 19), rândul 2
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 19 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 19], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        print(f"DCCD {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")
                        return total

            elif file_type == 'ded':
                # Coloana M (index 12), rândul 2 - Valoare produs NET
                df = pd.read_excel(file_path, header=None)
                if df.shape[1] > 12 and df.shape[0] > 1:
                    value = pd.to_numeric(df.iloc[1, 12], errors='coerce')
                    if not pd.isna(value):
                        total = abs(value) * tva_rate
                        print(f"DED {os.path.basename(file_path)}: {abs(value):.2f} * {tva_rate} = {total:.2f}")
                        return total

            elif file_type == 'dcs':
                # Coloana D (index 3), sumează toate valorile (storno)
                df = pd.read_excel(file_path, dtype=str)
                if 'Comision Net' in df.columns or df.shape[1] > 3:
                    # Încearcă cu header mai întâi
                    if 'Comision Net' in df.columns:
                        values = pd.to_numeric(df['Comision Net'], errors='coerce')
                    else:
                        # Fără header, coloana D
                        values = pd.to_numeric(df.iloc[1:, 3], errors='coerce')

                    total_net = values.sum()
                    # DCS este de obicei negativ (storno), îl tratăm ca reducere
                    total = abs(total_net) * tva_rate
                    print(f"DCS {os.path.basename(file_path)}: {total_net:.2f} * {tva_rate} = -{total:.2f} (storno)")
                    return -total  # Returnăm negativ pentru că e storno

        except Exception as e:
            print(f"Eroare la procesarea {file_type} {file_path}: {e}")

        return 0.0

    def calculate_period_total(self, period: str, files: Dict[str, List[str]]) -> Dict:
        """Calculează totalul pentru o perioadă folosind formula:
        DP + DV - (DCCO + DCCD + DC + DED + DCS)"""

        print(f"\n=== Calcul pentru perioada {period} ===")

        # Calculează DP (sumă pozitivă)
        dp_total = self.calculate_dp_total(files.get('dp', []))

        # Calculează DV (sumă pozitivă)
        dv_total = self.calculate_dv_total(files.get('dv', []))

        # Calculează comisioane (sume negative)
        dcco_total = sum(self.calculate_commission_with_tva(f, 'dcco', period)
                        for f in files.get('dcco', []))
        dccd_total = sum(self.calculate_commission_with_tva(f, 'dccd', period)
                        for f in files.get('dccd', []))
        dc_total = sum(self.calculate_commission_with_tva(f, 'dc', period)
                      for f in files.get('dc', []))
        ded_total = sum(self.calculate_commission_with_tva(f, 'ded', period)
                       for f in files.get('ded', []))
        dcs_total = sum(self.calculate_commission_with_tva(f, 'dcs', period)
                       for f in files.get('dcs', []))

        # Calculează totalul final
        comisioane_total = dcco_total + dccd_total + dc_total + ded_total + dcs_total
        total_final = dp_total + dv_total - comisioane_total

        print(f"\n--- Rezumat {period} ---")
        print(f"DP Total: {dp_total:.2f}")
        print(f"DV Total: {dv_total:.2f}")
        print(f"DCCO Total: -{dcco_total:.2f}")
        print(f"DCCD Total: -{dccd_total:.2f}")
        print(f"DC Total: -{dc_total:.2f}")
        print(f"DED Total: -{ded_total:.2f}")
        print(f"DCS Total: {dcs_total:.2f}")
        print(f"Comisioane totale: -{comisioane_total:.2f}")
        print(f"TOTAL FINAL: {total_final:.2f}")

        return {
            'period': period,
            'dp_total': dp_total,
            'dv_total': dv_total,
            'dcco_total': dcco_total,
            'dccd_total': dccd_total,
            'dc_total': dc_total,
            'ded_total': ded_total,
            'dcs_total': dcs_total,
            'comisioane_total': comisioane_total,
            'total_final': total_final
        }

    def process_folder(self, folder_path: str) -> List[Dict]:
        """Procesează un folder cu fișiere eMag și returnează calculele pe perioade"""
        periods = self.group_files_by_period(folder_path)

        results = []
        for period, files in sorted(periods.items()):
            print(f"\nProcesez perioada {period}:")
            print(f"  DP: {len(files['dp'])} fisiere")
            print(f"  DV: {len(files['dv'])} fisiere")
            print(f"  DC: {len(files['dc'])} fisiere")
            print(f"  DCCO: {len(files['dcco'])} fisiere")
            print(f"  DCCD: {len(files['dccd'])} fisiere")
            print(f"  DED: {len(files['ded'])} fisiere")
            print(f"  DCS: {len(files['dcs'])} fisiere")

            result = self.calculate_period_total(period, files)
            results.append(result)

        return results


if __name__ == "__main__":
    # Test cu folder-ul eMag
    calculator = EmagCalculator()

    # Testează cu folder-ul principal eMag
    folder_path = r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag"
    print(f"Procesez folder-ul: {folder_path}")

    results = calculator.process_folder(folder_path)

    print("\n" + "="*60)
    print("REZUMAT FINAL")
    print("="*60)

    grand_total = 0
    for result in results:
        print(f"Perioada {result['period']}: {result['total_final']:.2f} RON")
        grand_total += result['total_final']

    print(f"\nTOTAL GENERAL: {grand_total:.2f} RON")