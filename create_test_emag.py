#!/usr/bin/env python3
import pandas as pd

# Creez un fișier eMag de test
data = {
    'Order ID': ['437692700', '437676406', '999999999'],
    'Transaction type': ['sale', 'sale', 'sale'],
    'Client name': ['Test Client Canceled', 'Test Client Completed', 'Test Client Inexistent'],
    'Fraction value': [100.50, 50.75, 25.00]
}

df = pd.DataFrame(data)
df.to_excel('eMag/test_dp_072025.xlsx', index=False)

print("Fișier test creat: eMag/test_dp_072025.xlsx")
print("Comandă 437692700 - ar trebui să fie marcată ca 'Canceled'")
print("Comandă 437676406 - ar trebui să rămână fără factură")
print("Comandă 999999999 - ar trebui să rămână fără factură (nu există în easySales)")