#!/usr/bin/env python3
# Verifică comenzile fără factură din output

import pandas as pd

print("=== VERIFICARE COMENZI FARA FACTURA ===")

# Comenzile din output care nu au factură
comenzi_fara_factura = ['431642847', '431859225', '430164966']

try:
    # Citește easySales
    easysales = pd.read_excel('8 August/Comenzi easySales.xlsx', dtype=str)
    easysales.columns = easysales.columns.str.strip()
    easysales['ID comandă'] = easysales['ID comandă'].astype(str).str.strip()
    
    print(f"EasySales citit: {len(easysales)} rânduri")
    print(f"Coloane: {list(easysales.columns)}")
    
    for order_id in comenzi_fara_factura:
        print(f"\n--- Verificare Order ID: {order_id} ---")
        
        # Caută în easySales
        comanda_row = easysales[easysales['ID comandă'] == order_id]
        
        if not comanda_row.empty:
            status = comanda_row.iloc[0]['Status'].strip() if pd.notna(comanda_row.iloc[0]['Status']) else ''
            factura = comanda_row.iloc[0]['Numărul facturii'].strip() if 'Numărul facturii' in comanda_row.columns and pd.notna(comanda_row.iloc[0]['Numărul facturii']) else ''
            print(f"  GĂSIT în easySales:")
            print(f"    Status: '{status}'")
            print(f"    Numărul facturii: '{factura}'")
            
            if status == 'Canceled':
                print(f"  *** AR TREBUI SĂ FIE 'Canceled' ***")
            else:
                print(f"  Status nu este 'Canceled'")
        else:
            print(f"  NU GĂSIT în easySales")
            
except Exception as e:
    print(f"Eroare: {e}")

print("\n=== FINALIZAT ===")