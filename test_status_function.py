#!/usr/bin/env python3
# Test pentru verificarea funcției de status Canceled

import pandas as pd
import sys
import os

print("=== TEST VERIFICARE STATUS CANCELED ===")

# Testez citirea fișierului easySales
try:
    path_easysales = "8 August/Comenzi easySales.xlsx"
    print(f"Citesc fișierul: {path_easysales}")
    
    easysales = pd.read_excel(path_easysales, dtype=str)
    easysales.columns = easysales.columns.str.strip()
    
    print(f"Fișier citit cu succes. Shape: {easysales.shape}")
    print(f"Coloane: {list(easysales.columns)}")
    
    # Verific dacă coloanele necesare există
    if 'ID comandă' in easysales.columns and 'Status' in easysales.columns:
        print("✓ Coloanele 'ID comandă' și 'Status' găsite")
        
        # Afișez câteva exemple
        print("\nPrimele 5 comenzi cu statusurile lor:")
        sample_data = easysales[['ID comandă', 'Status']].head(5)
        for idx, row in sample_data.iterrows():
            print(f"  ID: {row['ID comandă']} - Status: {row['Status']}")
        
        # Testez comenzile anulate
        canceled_orders = easysales[easysales['Status'].str.strip() == 'Canceled']
        print(f"\nComenzi cu status 'Canceled': {len(canceled_orders)}")
        
        if len(canceled_orders) > 0:
            print("Primele comenzi anulate:")
            for idx, row in canceled_orders.head(3).iterrows():
                print(f"  ID: {row['ID comandă']} - Status: {row['Status']}")
        
        # Test funcționalitate
        def test_verifica_status(order_id):
            easysales['ID comandă'] = easysales['ID comandă'].astype(str).str.strip()
            order_id_str = str(order_id).strip()
            
            comanda_row = easysales[easysales['ID comandă'] == order_id_str]
            
            if not comanda_row.empty:
                status = comanda_row.iloc[0]['Status'].strip() if pd.notna(comanda_row.iloc[0]['Status']) else ''
                print(f"Order ID {order_id} găsit cu status: '{status}'")
                
                if status == 'Canceled':
                    return 'Canceled'
            else:
                print(f"Order ID {order_id} nu a fost găsit")
                
            return None
        
        print("\n=== TESTEZ FUNCȚIA ===")
        
        # Test cu o comandă anulată
        if len(canceled_orders) > 0:
            test_id = canceled_orders.iloc[0]['ID comandă']
            print(f"\nTest cu comanda anulată {test_id}:")
            result = test_verifica_status(test_id)
            print(f"Rezultat: {result}")
        
        # Test cu o comandă completată
        completed_orders = easysales[easysales['Status'].str.strip() == 'Completed']
        if len(completed_orders) > 0:
            test_id = completed_orders.iloc[0]['ID comandă']
            print(f"\nTest cu comanda completată {test_id}:")
            result = test_verifica_status(test_id)
            print(f"Rezultat: {result}")
        
        # Test cu ID inexistent
        print(f"\nTest cu ID inexistent 999999999:")
        result = test_verifica_status('999999999')
        print(f"Rezultat: {result}")
        
    else:
        print("✗ Coloanele 'ID comandă' sau 'Status' nu sunt găsite")
        print(f"Coloane disponibile: {list(easysales.columns)}")
        
except Exception as e:
    print(f"Eroare la testare: {e}")

print("\n=== TEST COMPLET ===")