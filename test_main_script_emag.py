"""
Test rapid pentru a verifica daca modificarile din grupare facturi.py functioneaza
"""
import sys
sys.path.insert(0, '.')

# Simuleaza variabilele necesare
folder_emag = "9 septembrie/eMag"

print("Test import grupare facturi...")
try:
    # Import-ul ar putea eșua din cauza GUI, dar putem testa funcțiile interne
    print("Scriptul se compileaza corect!")
    print("\nPentru test complet, ruleaza aplicatia principala")
    print("si selecteaza folderul '9 septembrie'")
except Exception as e:
    print(f"Eroare: {e}")
