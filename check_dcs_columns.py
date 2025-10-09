import pandas as pd

df = pd.read_excel('9 septembrie/eMag/nortia_dcs_092025_1758102265_v1.xlsx', header=None)
print('=== Index pentru coloanele cu Comision ===')
for i, val in enumerate(df.iloc[0]):
    if 'Comision' in str(val):
        print(f'Coloana {i}: {val}')

print('\n=== Valorile din rândul 1 pentru coloanele relevante ===')
print(f'Coloana 19 (Comision Net): {df.iloc[1, 19]}')
print(f'Coloana 20 (Procent Comision Net): {df.iloc[1, 20]}')
print(f'Coloana 22 (Total vouchere cadou): {df.iloc[1, 22]}')

print('\n=== Verificare cu header ===')
df_with_header = pd.read_excel('9 septembrie/eMag/nortia_dcs_092025_1758102265_v1.xlsx', header=0)
print(f'Prima linie Comision Net (după header): {df_with_header.iloc[0]["Comision Net"]}')
