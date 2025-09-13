"""
Test pentru noul calcul eMag îmbunătățit
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import importlib.util

# Încarcă modulul cu spațiu în nume
spec = importlib.util.spec_from_file_location("grupare_facturi", "grupare facturi.py")
grupare_facturi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grupare_facturi)

FacturiApp = grupare_facturi.FacturiApp

def test_emag_calculation():
    print("=== TEST CALCUL EMAG IMBUNATATIT ===")

    app = FacturiApp()

    # Configurează căile
    folder_emag = r"C:\Development\Python\Ultimate_FACTURI\8_August\eMag"
    path_easysales = r"C:\Development\Python\Ultimate_FACTURI\8_August\Comenzi easySales.xlsx"

    print(f"Folder eMag: {folder_emag}")
    print(f"EasySales: {path_easysales}")

    if not os.path.exists(folder_emag):
        print("EROARE: Folder-ul eMag nu există!")
        return

    if not os.path.exists(path_easysales):
        print("EROARE: Fișierul easySales nu există!")
        return

    try:
        # Testează doar calculul pe perioade
        erori = []
        rezultate = app._calculeaza_emag_pe_perioade(folder_emag, erori)

        print("\n" + "="*60)
        print("REZULTATE FINALE")
        print("="*60)

        total_general = 0
        for rezultat in rezultate:
            print(f"Perioada {rezultat['period']}: {rezultat['total_final']:.2f} RON")
            total_general += rezultat['total_final']

        print(f"\nTOTAL GENERAL: {total_general:.2f} RON")

        if erori:
            print(f"\nErori găsite: {len(erori)}")
            for eroare in erori:
                print(f"  - {eroare}")

    except Exception as e:
        print(f"EXCEPTIE in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_emag_calculation()