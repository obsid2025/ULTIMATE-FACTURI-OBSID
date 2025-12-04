"""
Smart Matching Engine - Algoritm inteligent de potrivire colete cu OP-uri bancare

Rezolva problema cand suma coletelor din API nu se potriveste exact cu suma din OP:
- GLS grupeaza coletele diferit in borderouri fata de cum le raporteaza in API
- Algoritmul gaseste combinatia de colete care se potriveste cu suma OP-ului
- Coletele ramase sunt marcate ca "pending" pentru urmatorul OP
"""

from typing import List, Dict, Optional, Tuple, Set
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from itertools import combinations

from .supabase_client import get_supabase_client


def find_parcel_combination(
    parcels: List[Dict],
    target_amount: float,
    tolerance: float = 0.02
) -> Tuple[List[Dict], List[Dict]]:
    """
    Gaseste combinatia de colete care se potriveste cu suma target.

    Foloseste un algoritm de subset sum pentru a gasi combinatia optima.

    Args:
        parcels: Lista de colete cu 'cod_amount'
        target_amount: Suma de atins (din OP bancar)
        tolerance: Toleranta pentru potrivire (default 0.02 RON)

    Returns:
        Tuple (matched_parcels, remaining_parcels)
    """
    if not parcels:
        return [], []

    target = Decimal(str(target_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tolerance_dec = Decimal(str(tolerance))

    # Converteste sumele la Decimal pentru precizie
    parcel_amounts = []
    for p in parcels:
        amt = Decimal(str(p.get('cod_amount', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        parcel_amounts.append((p, amt))

    # Calculeaza suma totala
    total_sum = sum(amt for _, amt in parcel_amounts)

    # Daca suma totala se potriveste exact, toate coletele fac parte din OP
    if abs(total_sum - target) <= tolerance_dec:
        return parcels, []

    # Daca suma totala e mai mica decat target-ul, nu avem destule colete
    if total_sum < target - tolerance_dec:
        return [], parcels

    # Sortam descrescator pentru eficienta
    parcel_amounts.sort(key=lambda x: x[1], reverse=True)

    n = len(parcel_amounts)

    # Cautam combinatia exacta - incepem cu cele mai mari subseturi
    # (e mai probabil sa fie un singur colet lipsa decat mai multe)
    for size in range(n, 0, -1):
        for combo in combinations(range(n), size):
            combo_sum = sum(parcel_amounts[i][1] for i in combo)
            if abs(combo_sum - target) <= tolerance_dec:
                matched = [parcel_amounts[i][0] for i in combo]
                remaining = [parcel_amounts[i][0] for i in range(n) if i not in combo]
                return matched, remaining

    # Nu s-a gasit combinatie exacta
    return [], parcels


def match_gls_parcels_to_bank_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict:
    """
    Potriveste coletele GLS cu tranzactiile bancare folosind matching inteligent.

    Workflow:
    1. Ia toate tranzactiile bancare GLS din perioada
    2. Ia toate coletele GLS livrate (nepotrivite inca)
    3. Pentru fiecare OP, gaseste combinatia de colete care se potriveste
    4. Marcheaza coletele potrivite si le leaga de OP
    5. Coletele ramase raman "pending" pentru urmatorul OP

    Returns:
        Dict cu statistici si rezultate
    """
    supabase = get_supabase_client()

    # Setam perioada default (ultimele 60 zile)
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=60)

    # 1. Ia tranzactiile bancare GLS
    bank_query = supabase.table('bank_transactions').select('*').eq('source', 'GLS')
    if start_date:
        bank_query = bank_query.gte('transaction_date', start_date.isoformat())
    if end_date:
        bank_query = bank_query.lte('transaction_date', end_date.isoformat())

    bank_transactions = bank_query.order('transaction_date').execute().data

    # 2. Ia coletele GLS livrate
    # Calculam data de livrare minima (cu 5 zile inainte de prima tranzactie)
    if bank_transactions:
        first_trans_date = datetime.strptime(bank_transactions[0]['transaction_date'], '%Y-%m-%d').date()
        delivery_start = first_trans_date - timedelta(days=5)
    else:
        delivery_start = start_date - timedelta(days=5)

    parcels_query = supabase.table('gls_parcels').select('*').eq('is_delivered', True)
    parcels_query = parcels_query.gte('delivery_date', delivery_start.isoformat())

    all_parcels = parcels_query.order('delivery_date').execute().data

    # Rezultate
    results = {
        'bank_transactions': len(bank_transactions),
        'total_parcels': len(all_parcels),
        'matched_parcels': 0,
        'pending_parcels': 0,
        'matches': [],
        'pending': [],
        'errors': []
    }

    # Set pentru a urmari coletele deja potrivite
    matched_parcel_ids = set()

    # 3. Pentru fiecare OP, gaseste coletele potrivite
    for trans in bank_transactions:
        op_amount = float(trans.get('amount', 0))
        op_ref = trans.get('op_reference', '')
        op_date = trans.get('transaction_date', '')

        # Coletele disponibile (livrate inainte de OP, nepotrivite inca)
        available_parcels = [
            p for p in all_parcels
            if p.get('id') not in matched_parcel_ids
            and p.get('delivery_date', '') <= op_date
        ]

        if not available_parcels:
            results['errors'].append({
                'op_reference': op_ref,
                'amount': op_amount,
                'error': 'Nu exista colete disponibile pentru potrivire'
            })
            continue

        # Gaseste combinatia de colete
        matched, remaining = find_parcel_combination(available_parcels, op_amount)

        if matched:
            # Marcheaza coletele ca potrivite
            matched_ids = [p['id'] for p in matched]
            matched_parcel_ids.update(matched_ids)

            matched_sum = sum(float(p.get('cod_amount', 0)) for p in matched)

            results['matches'].append({
                'op_reference': op_ref,
                'op_date': op_date,
                'op_amount': op_amount,
                'matched_amount': round(matched_sum, 2),
                'difference': round(op_amount - matched_sum, 2),
                'parcels_count': len(matched),
                'parcels': [
                    {
                        'parcel_number': p.get('parcel_number'),
                        'cod_amount': float(p.get('cod_amount', 0)),
                        'recipient_name': p.get('recipient_name'),
                        'delivery_date': p.get('delivery_date')
                    }
                    for p in matched
                ]
            })

            results['matched_parcels'] += len(matched)
        else:
            # Nu s-a gasit combinatie - incearca matching partial
            results['errors'].append({
                'op_reference': op_ref,
                'amount': op_amount,
                'available_parcels': len(available_parcels),
                'available_sum': round(sum(float(p.get('cod_amount', 0)) for p in available_parcels), 2),
                'error': 'Nu s-a gasit combinatie exacta de colete'
            })

    # 4. Coletele ramase sunt pending
    pending_parcels = [
        p for p in all_parcels
        if p.get('id') not in matched_parcel_ids
    ]

    results['pending_parcels'] = len(pending_parcels)
    results['pending'] = [
        {
            'parcel_number': p.get('parcel_number'),
            'cod_amount': float(p.get('cod_amount', 0)),
            'recipient_name': p.get('recipient_name'),
            'delivery_date': p.get('delivery_date')
        }
        for p in pending_parcels
    ]

    if pending_parcels:
        results['pending_total'] = round(sum(float(p.get('cod_amount', 0)) for p in pending_parcels), 2)

    return results


def match_sameday_parcels_to_bank_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict:
    """
    Potriveste coletele Sameday cu tranzactiile bancare folosind matching inteligent.

    Similar cu GLS, dar pentru Sameday.
    """
    supabase = get_supabase_client()

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=60)

    # 1. Ia tranzactiile bancare Sameday
    bank_query = supabase.table('bank_transactions').select('*').eq('source', 'Sameday')
    if start_date:
        bank_query = bank_query.gte('transaction_date', start_date.isoformat())
    if end_date:
        bank_query = bank_query.lte('transaction_date', end_date.isoformat())

    bank_transactions = bank_query.order('transaction_date').execute().data

    # 2. Ia coletele Sameday livrate
    if bank_transactions:
        first_trans_date = datetime.strptime(bank_transactions[0]['transaction_date'], '%Y-%m-%d').date()
        delivery_start = first_trans_date - timedelta(days=5)
    else:
        delivery_start = start_date - timedelta(days=5)

    parcels_query = supabase.table('sameday_parcels').select('*').eq('is_delivered', True)
    parcels_query = parcels_query.gte('delivery_date', delivery_start.isoformat())

    all_parcels = parcels_query.order('delivery_date').execute().data

    results = {
        'bank_transactions': len(bank_transactions),
        'total_parcels': len(all_parcels),
        'matched_parcels': 0,
        'pending_parcels': 0,
        'matches': [],
        'pending': [],
        'errors': []
    }

    matched_parcel_ids = set()

    for trans in bank_transactions:
        op_amount = float(trans.get('amount', 0))
        op_ref = trans.get('op_reference', '')
        op_date = trans.get('transaction_date', '')

        available_parcels = [
            p for p in all_parcels
            if p.get('id') not in matched_parcel_ids
            and p.get('delivery_date', '') <= op_date
        ]

        if not available_parcels:
            results['errors'].append({
                'op_reference': op_ref,
                'amount': op_amount,
                'error': 'Nu exista colete disponibile pentru potrivire'
            })
            continue

        matched, remaining = find_parcel_combination(available_parcels, op_amount)

        if matched:
            matched_ids = [p['id'] for p in matched]
            matched_parcel_ids.update(matched_ids)

            matched_sum = sum(float(p.get('cod_amount', 0)) for p in matched)

            results['matches'].append({
                'op_reference': op_ref,
                'op_date': op_date,
                'op_amount': op_amount,
                'matched_amount': round(matched_sum, 2),
                'difference': round(op_amount - matched_sum, 2),
                'parcels_count': len(matched),
                'parcels': [
                    {
                        'awb_number': p.get('awb_number'),
                        'cod_amount': float(p.get('cod_amount', 0)),
                        'delivery_date': p.get('delivery_date')
                    }
                    for p in matched
                ]
            })

            results['matched_parcels'] += len(matched)
        else:
            results['errors'].append({
                'op_reference': op_ref,
                'amount': op_amount,
                'available_parcels': len(available_parcels),
                'available_sum': round(sum(float(p.get('cod_amount', 0)) for p in available_parcels), 2),
                'error': 'Nu s-a gasit combinatie exacta de colete'
            })

    pending_parcels = [
        p for p in all_parcels
        if p.get('id') not in matched_parcel_ids
    ]

    results['pending_parcels'] = len(pending_parcels)
    results['pending'] = [
        {
            'awb_number': p.get('awb_number'),
            'cod_amount': float(p.get('cod_amount', 0)),
            'delivery_date': p.get('delivery_date')
        }
        for p in pending_parcels
    ]

    if pending_parcels:
        results['pending_total'] = round(sum(float(p.get('cod_amount', 0)) for p in pending_parcels), 2)

    return results


def analyze_discrepancy(
    source: str,
    op_amount: float,
    delivery_date: str
) -> Dict:
    """
    Analizeaza discrepanta pentru un OP specific.

    Util pentru debugging si intelegerea diferentelor.

    Args:
        source: 'GLS' sau 'Sameday'
        op_amount: Suma OP-ului
        delivery_date: Data livrarii (aproximativa)

    Returns:
        Dict cu analiza discrepantei
    """
    supabase = get_supabase_client()

    # Calculeaza intervalul de date (livrare cu 1-3 zile inainte de OP)
    ref_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
    start_date = ref_date - timedelta(days=3)
    end_date = ref_date + timedelta(days=1)

    if source == 'GLS':
        table = 'gls_parcels'
        id_field = 'parcel_number'
    else:
        table = 'sameday_parcels'
        id_field = 'awb_number'

    # Ia coletele din perioada
    parcels = supabase.table(table).select('*') \
        .eq('is_delivered', True) \
        .gte('delivery_date', start_date.isoformat()) \
        .lte('delivery_date', end_date.isoformat()) \
        .execute().data

    total_sum = sum(float(p.get('cod_amount', 0)) for p in parcels)
    difference = round(total_sum - op_amount, 2)

    result = {
        'source': source,
        'op_amount': op_amount,
        'parcels_count': len(parcels),
        'parcels_sum': round(total_sum, 2),
        'difference': difference,
        'parcels': []
    }

    # Daca avem diferenta, cautam coletul care lipseste
    if abs(difference) > 0.02:
        # Cauta coletul cu suma egala cu diferenta
        for p in parcels:
            cod = float(p.get('cod_amount', 0))
            if abs(cod - abs(difference)) < 0.02:
                result['likely_missing_parcel'] = {
                    id_field: p.get(id_field),
                    'cod_amount': cod,
                    'recipient_name': p.get('recipient_name', ''),
                    'delivery_date': p.get('delivery_date'),
                    'note': 'Acest colet probabil va fi pe alt borderou'
                }
                break

        # Gaseste combinatia care se potriveste
        matched, remaining = find_parcel_combination(parcels, op_amount)
        if matched:
            result['matched_parcels'] = [
                {id_field: p.get(id_field), 'cod_amount': float(p.get('cod_amount', 0))}
                for p in matched
            ]
            result['remaining_parcels'] = [
                {id_field: p.get(id_field), 'cod_amount': float(p.get('cod_amount', 0))}
                for p in remaining
            ]

    result['parcels'] = [
        {
            id_field: p.get(id_field),
            'cod_amount': float(p.get('cod_amount', 0)),
            'recipient_name': p.get('recipient_name', ''),
            'delivery_date': p.get('delivery_date')
        }
        for p in parcels
    ]

    return result


def run_smart_matching_test():
    """
    Ruleaza un test al algoritmului de matching inteligent.

    Afiseaza rezultatele pentru verificare.
    """
    print("=" * 60)
    print("TEST SMART MATCHING - GLS")
    print("=" * 60)

    gls_results = match_gls_parcels_to_bank_transactions()

    print(f"\nTranzactii bancare GLS: {gls_results['bank_transactions']}")
    print(f"Total colete GLS: {gls_results['total_parcels']}")
    print(f"Colete potrivite: {gls_results['matched_parcels']}")
    print(f"Colete pending: {gls_results['pending_parcels']}")

    if gls_results.get('pending_total'):
        print(f"Suma pending: {gls_results['pending_total']} RON")

    print("\n--- MATCHES ---")
    for match in gls_results['matches']:
        print(f"\nOP: {match['op_reference']} | {match['op_date']}")
        print(f"  Suma OP: {match['op_amount']} RON")
        print(f"  Suma potrivita: {match['matched_amount']} RON")
        print(f"  Diferenta: {match['difference']} RON")
        print(f"  Colete: {match['parcels_count']}")
        for p in match['parcels']:
            print(f"    - {p['parcel_number']}: {p['cod_amount']} RON ({p['recipient_name']})")

    if gls_results['errors']:
        print("\n--- ERORI ---")
        for err in gls_results['errors']:
            print(f"  OP {err['op_reference']}: {err['error']}")

    if gls_results['pending']:
        print("\n--- COLETE PENDING (vor fi pe urmatorul OP) ---")
        for p in gls_results['pending']:
            print(f"  - {p['parcel_number']}: {p['cod_amount']} RON ({p['recipient_name']})")

    print("\n" + "=" * 60)
    print("TEST SMART MATCHING - SAMEDAY")
    print("=" * 60)

    sameday_results = match_sameday_parcels_to_bank_transactions()

    print(f"\nTranzactii bancare Sameday: {sameday_results['bank_transactions']}")
    print(f"Total colete Sameday: {sameday_results['total_parcels']}")
    print(f"Colete potrivite: {sameday_results['matched_parcels']}")
    print(f"Colete pending: {sameday_results['pending_parcels']}")

    if sameday_results['matches']:
        print("\n--- MATCHES ---")
        for match in sameday_results['matches']:
            print(f"\nOP: {match['op_reference']} | {match['op_date']}")
            print(f"  Suma OP: {match['op_amount']} RON")
            print(f"  Colete: {match['parcels_count']}")

    if sameday_results['errors']:
        print("\n--- ERORI ---")
        for err in sameday_results['errors']:
            print(f"  OP {err.get('op_reference', 'N/A')}: {err.get('error', 'Unknown')}")

    return {
        'gls': gls_results,
        'sameday': sameday_results
    }


if __name__ == "__main__":
    run_smart_matching_test()
