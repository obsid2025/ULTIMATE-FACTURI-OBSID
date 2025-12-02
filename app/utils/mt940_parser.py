"""
Parser pentru fisiere MT940 (Banca Transilvania)
Extrage incasarile relevante (GLS, Sameday, Netopia, eMag)
"""

import re
import os
from typing import List, Tuple, Optional


def extrage_referinte_op_din_mt940_folder(folder_path: str) -> List[Tuple]:
    """
    Extrage referintele OP din toate fisierele MT940 dintr-un folder.

    Returns:
        Lista de tuple: (op_ref, suma, data, batchid, details)
    """
    referinte = []

    if not folder_path or not os.path.isdir(folder_path):
        return referinte

    for file in os.listdir(folder_path):
        if file.startswith('MT940') and file.endswith('.txt'):
            file_path = os.path.join(folder_path, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                refs = _parseaza_mt940(text)
                referinte.extend(refs)
            except Exception as e:
                print(f"MT940: Eroare la citirea {file}: {e}")

    return referinte


def _parseaza_mt940(text: str) -> List[Tuple]:
    """
    Parseaza un fisier MT940 si extrage incasarile (credite).

    Structura MT940:
    :61:YYMMDDMMDDCD suma tip NONREF//referinta
    :86:Detalii tranzactie (poate fi pe mai multe linii)

    Unde:
    - C = Credit (incasare)
    - D = Debit (plata)
    - suma foloseste virgula ca separator decimal
    """
    referinte = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith(':61:'):
            tranzactie_line = line[4:]

            if len(tranzactie_line) >= 10:
                # Extrage data (primele 6 caractere = YYMMDD)
                data_yy = tranzactie_line[0:2]
                data_mm = tranzactie_line[2:4]
                data_dd = tranzactie_line[4:6]
                data_op = f"20{data_yy}-{data_mm}-{data_dd}"

                # Gaseste C (credit) sau D (debit)
                rest = tranzactie_line[10:]

                if rest and rest[0] in ['C', 'D']:
                    tip_tranzactie = rest[0]
                    rest = rest[1:]

                    # Extrage suma
                    suma_match = re.match(r'([\d,]+)', rest)
                    if suma_match:
                        suma_str = suma_match.group(1).replace(',', '.')
                        try:
                            suma_float = float(suma_str)
                        except ValueError:
                            suma_float = 0

                        # Extrage referinta
                        ref_match = re.search(r'//([A-Za-z0-9]+)', tranzactie_line)
                        op_ref = ref_match.group(1) if ref_match else ""

                        # Colecteaza detaliile din :86:
                        details_text = ""
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if next_line.startswith(':86:'):
                                details_text = next_line[4:]
                                i += 1
                                while i < len(lines) and not lines[i].strip().startswith(':'):
                                    details_text += " " + lines[i].strip()
                                    i += 1
                                break
                            elif next_line.startswith(':'):
                                break
                            i += 1

                        # Verifica daca este o incasare relevanta
                        if tip_tranzactie == 'C' and suma_float > 0:
                            is_relevant = False
                            details_upper = details_text.upper()

                            if "GLS" in details_upper or "GENERAL LOGISTICS" in details_upper:
                                is_relevant = True
                            elif "DELIVERY SOLUTIONS" in details_upper or "SAMEDAY" in details_upper:
                                is_relevant = True
                            elif "NETOPIA" in details_upper or "BATCHID" in details_upper:
                                is_relevant = True
                            elif "DANTE INTERNATIONAL" in details_upper or "EMAG" in details_upper:
                                is_relevant = True
                            elif "TRANSFER RAMBURS" in details_upper:
                                is_relevant = True
                            elif "INCS RBS" in details_upper:
                                is_relevant = True

                            if is_relevant:
                                # Extrage batchId daca exista
                                batchid = None
                                batch_match = re.search(r'BATCHID\s*[:\s]*(\d+)', details_text, re.IGNORECASE)
                                if batch_match:
                                    batchid = batch_match.group(1)

                                referinte.append((op_ref, suma_float, data_op, batchid, details_text))

                        continue
        i += 1

    return referinte


def get_sursa_incasare(details: str) -> str:
    """Determina sursa incasarii din detalii."""
    details_upper = details.upper()

    if "GLS" in details_upper or "GENERAL LOGISTICS" in details_upper:
        return "GLS"
    elif "DELIVERY SOLUTIONS" in details_upper or "SAMEDAY" in details_upper:
        return "Sameday"
    elif "NETOPIA" in details_upper or "BATCHID" in details_upper:
        return "Netopia"
    elif "DANTE INTERNATIONAL" in details_upper or "EMAG" in details_upper:
        return "eMag"
    else:
        return "Altul"
