"""
Procesor pentru generarea raportului OP-uri
Combina datele din Supabase (GLS, Sameday, Netopia) cu Gomag si MT940
pentru a genera export-ul in formatul original
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .supabase_client import get_supabase_client as get_client


def get_gls_parcels_for_period(start_date: str, end_date: str) -> List[Dict]:
    """
    Obtine coletele GLS livrate intr-o perioada.

    Args:
        start_date: Data start (YYYY-MM-DD)
        end_date: Data end (YYYY-MM-DD)

    Returns:
        Lista de colete GLS grupate pe data livrarii
    """
    client = get_client()
    if not client:
        return []

    try:
        result = client.table("gls_parcels").select("*").gte(
            "delivery_date", start_date
        ).lte(
            "delivery_date", end_date
        ).eq("is_delivered", True).execute()

        return result.data or []
    except Exception as e:
        print(f"Eroare la citirea GLS: {e}")
        return []


def get_sameday_parcels_for_period(start_date: str, end_date: str) -> List[Dict]:
    """
    Obtine coletele Sameday livrate intr-o perioada.
    """
    client = get_client()
    if not client:
        return []

    try:
        result = client.table("sameday_parcels").select("*").gte(
            "delivery_date", start_date
        ).lte(
            "delivery_date", end_date
        ).eq("is_delivered", True).execute()

        return result.data or []
    except Exception as e:
        print(f"Eroare la citirea Sameday: {e}")
        return []


def get_netopia_transactions_for_period(start_date: str, end_date: str) -> List[Dict]:
    """
    Obtine tranzactiile Netopia pentru o perioada.
    """
    client = get_client()
    if not client:
        return []

    try:
        # Netopia transactions don't have delivery_date, use synced_at or batch date
        result = client.table("netopia_transactions").select("*").execute()
        return result.data or []
    except Exception as e:
        print(f"Eroare la citirea Netopia: {e}")
        return []


def get_mt940_transactions_for_period(start_date: str, end_date: str) -> List[Dict]:
    """
    Obtine tranzactiile MT940 (OP-uri bancare) pentru o perioada.
    """
    client = get_client()
    if not client:
        return []

    try:
        result = client.table("bank_transactions").select("*").gte(
            "transaction_date", start_date
        ).lte(
            "transaction_date", end_date
        ).execute()

        return result.data or []
    except Exception as e:
        print(f"Eroare la citirea MT940: {e}")
        return []


def group_parcels_by_delivery_date(parcels: List[Dict], curier: str) -> List[Dict]:
    """
    Grupeaza coletele pe data livrarii (simuleaza borderourile).

    Returneza lista de "borderouri" cu:
    - borderou: nume borderou (data)
    - curier: GLS/Sameday
    - parcels: lista de colete
    - suma_total: suma totala COD
    """
    if not parcels:
        return []

    # Group by delivery date
    by_date = {}
    for p in parcels:
        date_str = p.get('delivery_date', 'Unknown')
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(p)

    result = []
    for date_str, date_parcels in sorted(by_date.items()):
        suma_total = sum(float(p.get('cod_amount', 0) or 0) for p in date_parcels)

        # Generate borderou name like original app
        if curier == "GLS":
            # GLS: clientnumber_RON_DDMMYYYY.xlsx format
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                borderou_name = f"553005982_RON_{dt.strftime('%d%m%Y')}.xlsx"
            except:
                borderou_name = f"GLS_{date_str}.xlsx"
        else:
            # Sameday: YYYY-MM-DD-obsid-s r l-cod-ledger-ron.xlsx format
            try:
                borderou_name = f"{date_str}-obsid-s r l-cod-ledger-ron.xlsx"
            except:
                borderou_name = f"Sameday_{date_str}.xlsx"

        result.append({
            'borderou': borderou_name,
            'curier': curier,
            'delivery_date': date_str,
            'parcels': date_parcels,
            'suma_total': suma_total
        })

    return result


def match_parcels_with_gomag_oblio(
    parcels: List[Dict],
    gomag_df: pd.DataFrame,
    invoices: List[Dict]
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Potriveste coletele cu comenzile din Gomag si facturile din Oblio.

    Args:
        parcels: Lista de colete (GLS sau Sameday)
        gomag_df: DataFrame cu comenzile Gomag
        invoices: Lista de facturi din Oblio (Supabase)

    Returns:
        Tuple (DataFrame cu rezultate, lista de erori)
    """
    erori = []
    rezultate = []

    # Pregateste dictionarul de facturi pentru cautare rapida
    # Factura poate fi gasita dupa order_id sau alte referinte
    facturi_by_order = {}
    for inv in invoices:
        # Extrage order ID din referinta sau alte campuri
        ref = inv.get('reference', '') or ''
        order_id = inv.get('order_id', '')

        if order_id:
            facturi_by_order[str(order_id)] = inv

        # Incearca sa extragi order ID din referinta
        import re
        matches = re.findall(r'\b(\d{3,6})\b', ref)
        for m in matches:
            if m not in facturi_by_order:
                facturi_by_order[m] = inv

    # Pregateste Gomag pentru cautare
    gomag_lookup = {}
    if gomag_df is not None and not gomag_df.empty:
        for _, row in gomag_df.iterrows():
            # Cauta AWB in Gomag
            awb = str(row.get('AWB', row.get('awb', row.get('Numar AWB', '')))).strip()
            order_id = str(row.get('ID', row.get('Order ID', row.get('id', '')))).strip()

            if awb:
                gomag_lookup[awb] = {
                    'order_id': order_id,
                    'awb': awb,
                    'row': row
                }

    for p in parcels:
        # Normalizeaza AWB
        awb = p.get('parcel_number', p.get('awb_number', ''))
        awb_norm = str(awb).strip().upper()

        cod_amount = float(p.get('cod_amount', 0) or 0)

        # Cauta in Gomag
        gomag_match = None
        order_id = None

        # Incearca potrivire directa
        if awb_norm in gomag_lookup:
            gomag_match = gomag_lookup[awb_norm]
            order_id = gomag_match['order_id']

        # Incearca fara ultimele 3 caractere (pentru GLS)
        if not gomag_match and len(awb_norm) > 10:
            awb_short = awb_norm[:-3]
            if awb_short in gomag_lookup:
                gomag_match = gomag_lookup[awb_short]
                order_id = gomag_match['order_id']

        # Cauta factura
        numar_factura = None
        if order_id and order_id in facturi_by_order:
            numar_factura = facturi_by_order[order_id].get('number', '')

        # Adauga rezultat
        rezultate.append({
            'AWB_normalizat': awb_norm,
            'Order ID': order_id or '',
            'numar factura': numar_factura or '',
            'Sumă ramburs': cod_amount,
            'eroare': 'NU' if numar_factura else 'DA'
        })

        if not numar_factura:
            erori.append(f"AWB {awb_norm}: nu s-a gasit factura")

    return pd.DataFrame(rezultate), erori


def match_op_with_borderou(suma_borderou: float, mt940_transactions: List[Dict], curier: str) -> Tuple[str, str]:
    """
    Gaseste OP-ul care se potriveste cu suma borderoului si curierul.

    Args:
        suma_borderou: Suma totala a borderoului
        mt940_transactions: Lista de tranzactii MT940
        curier: Numele curierului (GLS, Sameday, Netopia)

    Returns:
        Tuple (numar_op, data_op)
    """
    for trans in mt940_transactions:
        suma_op = float(trans.get('amount', 0) or 0)
        source = trans.get('source', '')

        # Verifica daca sursa se potriveste
        if curier.upper() not in source.upper():
            continue

        # Potrivire cu toleranta de 0.10 RON
        if abs(suma_op - suma_borderou) < 0.10:
            return trans.get('op_reference', ''), trans.get('transaction_date', '')

    return '', ''


def generate_opuri_export(
    start_date: str,
    end_date: str,
    gomag_df: Optional[pd.DataFrame] = None
) -> BytesIO:
    """
    Genereaza export-ul OP-uri in formatul original.

    Args:
        start_date: Data start (YYYY-MM-DD)
        end_date: Data end (YYYY-MM-DD)
        gomag_df: DataFrame cu date Gomag (optional)

    Returns:
        BytesIO cu fisierul Excel
    """
    # Obtine datele din Supabase
    gls_parcels = get_gls_parcels_for_period(start_date, end_date)
    sameday_parcels = get_sameday_parcels_for_period(start_date, end_date)
    mt940_transactions = get_mt940_transactions_for_period(start_date, end_date)

    # Obtine facturile din Oblio
    client = get_client()
    invoices = []
    if client:
        try:
            result = client.table("invoices").select("*").execute()
            invoices = result.data or []
        except:
            pass

    # Grupeaza coletele pe borderouri (data livrarii)
    gls_borderouri = group_parcels_by_delivery_date(gls_parcels, "GLS")
    sameday_borderouri = group_parcels_by_delivery_date(sameday_parcels, "Sameday")

    # Creeaza workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "OP-uri"

    # Stiluri
    header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    gls_fill = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")
    sameday_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    netopia_fill = PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid")
    error_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

    # Header exact ca in original
    headers = ["Data OP", "Număr OP", "Nume Borderou", "Curier", "Order ID",
               "Număr Factură", "Sumă", "Erori", "Diferență eMag", "Facturi Comision eMag"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    # Ajusteaza latimea coloanelor
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 8
    ws.column_dimensions['I'].width = 15
    ws.column_dimensions['J'].width = 20

    row_num = 2

    # Proceseaza GLS si Sameday
    for borderouri, curier, fill_color in [
        (gls_borderouri, "GLS", gls_fill),
        (sameday_borderouri, "Sameday", sameday_fill)
    ]:
        for borderou in borderouri:
            # Match parcels with Gomag/Oblio
            parcels_df, erori = match_parcels_with_gomag_oblio(
                borderou['parcels'],
                gomag_df,
                invoices
            )

            suma_total = borderou['suma_total']

            # Gaseste OP-ul (foloseste curierul pentru matching)
            numar_op, data_op = match_op_with_borderou(suma_total, mt940_transactions, curier)

            # Verifica daca sunt erori
            erori_exist = any(parcels_df['eroare'] == 'DA') if not parcels_df.empty else False
            erori_text = "DA" if erori_exist else "NU"

            # Scrie facturile
            first_row = True
            facturi_ok = parcels_df[parcels_df['numar factura'] != ''] if not parcels_df.empty else pd.DataFrame()

            for _, parcel_row in facturi_ok.iterrows():
                # Converteste numarul facturii la int daca e numeric
                numar_factura = parcel_row['numar factura']
                try:
                    numar_factura = int(float(numar_factura))
                except:
                    pass

                ws.cell(row=row_num, column=1, value=data_op if first_row else "")
                ws.cell(row=row_num, column=2, value=numar_op if first_row else "")
                ws.cell(row=row_num, column=3, value=borderou['borderou'] if first_row else "")

                cell_curier = ws.cell(row=row_num, column=4, value=curier if first_row else "")
                if first_row:
                    cell_curier.fill = fill_color
                    cell_curier.font = Font(color="FFFFFF")

                ws.cell(row=row_num, column=5, value=parcel_row['Order ID'])
                ws.cell(row=row_num, column=6, value=numar_factura)
                ws.cell(row=row_num, column=7, value=parcel_row['Sumă ramburs'])

                cell_erori = ws.cell(row=row_num, column=8, value=erori_text if first_row else "")
                if first_row and erori_exist:
                    cell_erori.fill = error_fill

                first_row = False
                row_num += 1

            # Daca nu sunt facturi OK, scrie o linie goala
            if facturi_ok.empty:
                ws.cell(row=row_num, column=1, value=data_op)
                ws.cell(row=row_num, column=2, value=numar_op)
                ws.cell(row=row_num, column=3, value=borderou['borderou'])
                cell_curier = ws.cell(row=row_num, column=4, value=curier)
                cell_curier.fill = fill_color
                cell_curier.font = Font(color="FFFFFF")
                ws.cell(row=row_num, column=8, value=erori_text)
                row_num += 1

            # Scrie AWB-urile fara factura
            facturi_ko = parcels_df[parcels_df['numar factura'] == ''] if not parcels_df.empty else pd.DataFrame()
            if not facturi_ko.empty:
                ws.cell(row=row_num, column=6, value="AWB-uri fără factură:")
                row_num += 1

                for _, parcel_row in facturi_ko.iterrows():
                    ws.cell(row=row_num, column=6, value=parcel_row['AWB_normalizat'])
                    ws.cell(row=row_num, column=7, value=parcel_row['Sumă ramburs'])
                    row_num += 1

            # Rand total
            ws.cell(row=row_num, column=6, value="Total")
            ws.cell(row=row_num, column=6).font = Font(bold=True)
            ws.cell(row=row_num, column=7, value=suma_total)
            ws.cell(row=row_num, column=7).font = Font(bold=True)
            row_num += 1

            # Rand gol
            row_num += 1

    # ============================================
    # Proceseaza Netopia
    # ============================================
    # Grupeaza tranzactiile Netopia pe batch_id din MT940
    netopia_ops = [t for t in mt940_transactions if t.get('source', '').upper() == 'NETOPIA']

    for netopia_op in netopia_ops:
        batch_id = netopia_op.get('batch_id', '')
        suma_op = float(netopia_op.get('amount', 0) or 0)
        numar_op = netopia_op.get('op_reference', '')
        data_op = netopia_op.get('transaction_date', '')

        # Numele borderoului pentru Netopia
        borderou_name = f"batchId.{batch_id}.csv" if batch_id else f"Netopia_{data_op}.csv"

        # Obtine tranzactiile Netopia din Supabase pentru acest batch
        netopia_trans = []
        if client and batch_id:
            try:
                result = client.table("netopia_transactions").select("*").eq("batch_id", batch_id).execute()
                netopia_trans = result.data or []
            except:
                pass

        # Calculeaza comisioane si total facturi
        total_facturi = sum(float(t.get('amount', 0) or 0) for t in netopia_trans)
        total_comisioane = sum(float(t.get('fee', 0) or 0) for t in netopia_trans)

        # Daca nu avem tranzactii detaliate, folosim suma OP-ului
        if not netopia_trans:
            total_facturi = suma_op
            total_comisioane = 0

        # Scrie header-ul borderoului Netopia
        ws.cell(row=row_num, column=1, value=data_op)
        ws.cell(row=row_num, column=2, value=numar_op)
        ws.cell(row=row_num, column=3, value=borderou_name)
        cell_curier = ws.cell(row=row_num, column=4, value="Netopia")
        cell_curier.fill = netopia_fill

        # Daca avem tranzactii detaliate, le scriem
        first_row = True
        if netopia_trans:
            for trans in netopia_trans:
                order_id = trans.get('order_id', '')
                amount = float(trans.get('amount', 0) or 0)

                # Cauta factura pentru order_id
                numar_factura = ''
                if order_id and str(order_id) in [str(inv.get('order_id', '')) for inv in invoices]:
                    for inv in invoices:
                        if str(inv.get('order_id', '')) == str(order_id):
                            numar_factura = inv.get('number', '')
                            break

                if not first_row:
                    ws.cell(row=row_num, column=1, value="")
                    ws.cell(row=row_num, column=2, value="")
                    ws.cell(row=row_num, column=3, value="")
                    ws.cell(row=row_num, column=4, value="")

                ws.cell(row=row_num, column=5, value=order_id)
                ws.cell(row=row_num, column=6, value=numar_factura if numar_factura else "")
                ws.cell(row=row_num, column=7, value=amount)
                ws.cell(row=row_num, column=8, value="NU" if numar_factura else "DA")

                first_row = False
                row_num += 1

        # Linie Comisioane
        ws.cell(row=row_num, column=6, value="Comisioane:")
        ws.cell(row=row_num, column=7, value=total_comisioane)
        row_num += 1

        # Linie Total facturi
        ws.cell(row=row_num, column=6, value="Total facturi:")
        ws.cell(row=row_num, column=7, value=total_facturi)
        row_num += 1

        # Linie Total OP
        ws.cell(row=row_num, column=6, value="Total OP:")
        ws.cell(row=row_num, column=6).font = Font(bold=True)
        ws.cell(row=row_num, column=7, value=suma_op)
        ws.cell(row=row_num, column=7).font = Font(bold=True)
        row_num += 1

        # Rand gol
        row_num += 1

    # Salveaza in buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer
