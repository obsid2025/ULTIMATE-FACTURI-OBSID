import pandas as pd

df = pd.read_excel('9 septembrie/eMag/nortia_dcs_092025_1758102265_v1.xlsx', header=0)
print('\n=== TOATE LINIILE DCS ===')
for idx, row in df.iterrows():
    print(f"Linia {idx}: Order={row['ID comanda']}, Data={row['Data stornare comanda']}, Comision={row['Comision Net']}")

print('\n\n=== ANALIZA FILTRARE PERIOADA 01-15 SEPTEMBRIE ===')
df['Data stornare comanda'] = pd.to_datetime(df['Data stornare comanda'], errors='coerce')

# Filtrare strictă
mask_strict = (df['Data stornare comanda'] >= '2025-09-01') & (df['Data stornare comanda'] <= '2025-09-15')
print(f"Linii cu dată în perioada 01-15: {mask_strict.sum()}")
print(f"Total Comision Net (cu dată): {df[mask_strict]['Comision Net'].sum():.2f}")

# Filtrare inclusiv NaT (fără dată)
mask_loose = mask_strict | df['Data stornare comanda'].isna()
print(f"\nLinii cu dată în perioada SAU fără dată: {mask_loose.sum()}")
print(f"Total Comision Net (inclusiv fără dată): {df[mask_loose]['Comision Net'].sum():.2f}")

print('\n=== PRIMA LINIE (fără Order ID și fără dată) ===')
print(df.iloc[0][['ID comanda', 'Data stornare comanda', 'Comision Net', 'Total vouchere cadou']])
