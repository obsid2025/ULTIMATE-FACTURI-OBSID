"""
Script de test pentru debugging calculelor eMag
"""
import sys
import os

# Importă clasa principală
sys.path.insert(0, os.path.dirname(__file__))

# Creează o instanță minimă pentru a testa procesarea eMag
class MockApp:
    def __init__(self):
        self.path_borderouri_gls = ""
        self.path_borderouri_sameday = ""
        self.path_netopia = ""
        self.path_emag = "c:\\Development\\Python\\Ultimate_FACTURI\\9 septembrie\\eMag"
        self.path_gomag = "c:\\Development\\Python\\Ultimate_FACTURI\\9 septembrie\\Comenzi Gomag.xlsx"
        self.path_easysales = "c:\\Development\\Python\\Ultimate_FACTURI\\9 septembrie\\Comenzi easySales.xlsx"
        self.path_oblio = "c:\\Development\\Python\\Ultimate_FACTURI\\9 septembrie\\Facturi_Oblio.xlsx"
        self.path_extras = "c:\\Development\\Python\\Ultimate_FACTURI\\9 septembrie\\20251007_165152_extras_1165197_2025-09-01-2025-10-07.xml"
        self.progress_var = None
        self.progress_text = None
        self.erori = []
        
    def get(self):
        return self.path_emag

# Importă funcția de procesare
exec(open("grupare facturi.py", encoding="utf-8").read())

# Creează instanța mock
app = MockApp()

# Rulează procesarea eMag
print("Începe procesarea eMag...")
print("="*100)

# Apelează funcția de procesare
try:
    # Aici trebuie să apelăm funcția corectă din script
    print("Test finalizat!")
except Exception as e:
    print(f"Eroare: {e}")
    import traceback
    traceback.print_exc()
