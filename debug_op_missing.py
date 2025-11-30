import xml.etree.ElementTree as ET
import re
from datetime import datetime

# Parsează XML-ul
tree = ET.parse('9 septembrie/20251007_165152_extras_1165197_2025-09-01-2025-10-07.xml')
root = tree.getroot()

print("=" * 80)
print("ANALIZA OP LIPSĂ - OLP1.5420122 (2125.86 RON)")
print("=" * 80)

# Extrage toate OP-urile
all_ops = []
for movement in root.findall('.//movement'):
    ref_elem = movement.find('ref')
    credit_elem = movement.find('credit')
    date_elem = movement.find('booking_date')
    details_elem = movement.find('details')
    
    if ref_elem is not None and credit_elem is not None:
        ref = ref_elem.text.strip() if ref_elem.text else ''
        credit = float(credit_elem.text) if credit_elem.text else 0.0
        date = date_elem.text if date_elem is not None and date_elem.text else ''
        details = details_elem.text if details_elem is not None and details_elem.text else ''
        
        if credit > 0:
            # Caută BatchId în detalii
            batch_match = re.search(r'batchId\.?(\d+)', details, re.IGNORECASE)
            batch_id = batch_match.group(1) if batch_match else None
            
            all_ops.append({
                'ref': ref,
                'credit': credit,
                'date': date,
                'batch_id': batch_id,
                'details': details
            })

print(f"\nTotal OP-uri cu credit > 0: {len(all_ops)}")

# Caută OP-ul specific
target_op = None
for op in all_ops:
    if '5420122' in op['ref']:
        target_op = op
        break

if target_op:
    print(f"\n✓ OP găsit în XML:")
    print(f"  Ref: {target_op['ref']}")
    print(f"  Credit: {target_op['credit']}")
    print(f"  Date: {target_op['date']}")
    print(f"  BatchId: {target_op['batch_id']}")
    print(f"  Details: {target_op['details'][:100]}...")
    
    # Verifică dacă data este în septembrie
    try:
        op_date = datetime.strptime(target_op['date'], '%Y-%m-%d')
        print(f"\n  Data parsată: {op_date}")
        print(f"  Luna: {op_date.month}")
        print(f"  Este în octombrie: {op_date.month == 10}")
    except Exception as e:
        print(f"  EROARE parsare dată: {e}")
else:
    print("\n✗ OP NU găsit în XML!")

# Verifică câte OP-uri sunt în octombrie
october_ops = [op for op in all_ops if op['date'].startswith('2025-10')]
september_ops = [op for op in all_ops if op['date'].startswith('2025-09')]

print(f"\n\nStatistici OP-uri:")
print(f"  Septembrie (2025-09-*): {len(september_ops)}")
print(f"  Octombrie (2025-10-*): {len(october_ops)}")

print(f"\n\nPrimele 5 OP-uri din octombrie:")
for op in october_ops[:5]:
    print(f"  {op['ref']}: {op['credit']} RON - {op['date']}")
