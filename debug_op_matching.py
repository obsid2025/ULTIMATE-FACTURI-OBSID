"""
Debug script pentru a verifica de ce OP-ul 2125.86 nu apare în export
"""

# Simulăm logica din scripturi
rezultate_emag = [
    {'ref_period': '2025-09-01 - 2025-09-15', 'suma_finala_pentru_op': 3786.15},
    {'ref_period': '2025-09-16 - 2025-09-28', 'suma_finala_pentru_op': 5673.23},
    {'ref_period': '2025-09-29 - 2025-09-30', 'suma_finala_pentru_op': 2125.86},
]

referinte_op = [
    ('OLP1.5361310', 3786.15, '2025-09-19', None, 'Incasare OP/ 906311994/193177/DANTE INTERNATIONAL SA/14399840 / RO73INGB0001008199078940/  /ROC/No.438430719/16.9.2025 . .//RFB/'),
    ('OLP1.5401321', 5673.23, '2025-09-30', None, 'Incasare OP/ 908470018/200410/DANTE INTERNATIONAL SA/14399840 / RO73INGB0001008199078940/  /ROC/No.439858483/23.9.2025 . .//RFB/'),
    ('OLP1.5420122', 2125.86, '2025-10-03', None, 'Incasare OP/ 909307657/207580/DANTE INTERNATIONAL SA/14399840 / RO73INGB0001008199078940/  /ROC/No.440665903/1.1.2025 . .//RFB/'),
]

print("=" * 80)
print("SIMULARE MATCHING OP-URI CU PERIOADE eMag")
print("=" * 80)

ops_folosite = []

for idx, rezultat in enumerate(rezultate_emag, 1):
    ref_period = rezultat['ref_period']
    suma_finala_pentru_op = rezultat['suma_finala_pentru_op']
    
    print(f"\n[Perioada {idx}] {ref_period}")
    print(f"  Suma căutată: {suma_finala_pentru_op:.2f} RON")
    
    # Logica actuală din script (cu break!)
    op_gasit = ""
    data_op = ""
    
    for op, suma_op, data, batchid_details, details_text in referinte_op:
        if "DANTE INTERNATIONAL SA" in details_text:
            diff = abs(float(suma_op) - suma_finala_pentru_op)
            print(f"    Testing OP {op}: {suma_op:.2f} RON (diff: {diff:.2f})")
            
            if diff < 1:
                if op in ops_folosite:
                    print(f"      ✗ DEJA FOLOSIT pentru altă perioadă!")
                else:
                    op_gasit = op
                    data_op = data
                    ops_folosite.append(op)
                    print(f"      ✓ MATCH găsit!")
                    break  # ← PROBLEMA: Se oprește aici!
    
    if op_gasit:
        print(f"  → OP final: {op_gasit} ({data_op})")
    else:
        print(f"  → ✗ NU S-A GĂSIT OP potrivit!")

print("\n" + "=" * 80)
print("PROBLEMA IDENTIFICATĂ:")
print("=" * 80)
print("Logica curentă folosește 'break' după primul match, ceea ce înseamnă că")
print("dacă un OP a fost deja folosit, scriptul NU continuă să caute altele!")
print("\nSOLUTIE: Trebuie să marcăm OP-urile deja folosite și să sărim peste ele.")
