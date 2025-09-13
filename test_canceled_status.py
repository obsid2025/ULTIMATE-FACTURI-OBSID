#!/usr/bin/env python3
# Test script pentru funcția de verificare status Canceled

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import din modulul principal
from tkinter import Tk
exec(open('grupare facturi.py').read())

# Testez funcția
app = FacturiApp()

print("=== TEST VERIFICARE STATUS CANCELED ===")
print("Testing Order ID 437692700 (ar trebui să fie Canceled)...")

result = app.verifica_status_comanda_easysales('437692700', '8 August/Comenzi easySales.xlsx')
print(f"Rezultat pentru comanda 437692700: {result}")

print("\nTesting Order ID 437676406 (ar trebui să fie Completed - nu Canceled)...")
result2 = app.verifica_status_comanda_easysales('437676406', '8 August/Comenzi easySales.xlsx')
print(f"Rezultat pentru comanda 437676406: {result2}")

print("\nTesting Order ID inexistent...")
result3 = app.verifica_status_comanda_easysales('999999999', '8 August/Comenzi easySales.xlsx')
print(f"Rezultat pentru comanda inexistentă: {result3}")

print("\n=== TEST COMPLET ===")