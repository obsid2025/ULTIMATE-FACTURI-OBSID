"""
Data synchronization module for MT940 and Oblio data
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, date
import json

from .supabase_client import get_supabase_client
from .oblio_api import get_all_invoices, transform_invoice_for_db
from .mt940_parser import extrage_referinte_op_din_mt940_folder, get_sursa_incasare


def import_mt940_to_supabase(
    folder_path: str,
    file_names: Optional[List[str]] = None
) -> Dict:
    """
    Import MT940 transactions to Supabase with deduplication.

    Returns:
        Dict with import statistics
    """
    supabase = get_supabase_client()

    # Create sync log
    log_response = supabase.table('sync_logs').insert({
        'sync_type': 'mt940_import',
        'status': 'running',
        'file_names': file_names or []
    }).execute()
    sync_log_id = log_response.data[0]['id']

    stats = {
        'processed': 0,
        'inserted': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    try:
        # Extract transactions from MT940 files
        transactions = extrage_referinte_op_din_mt940_folder(folder_path)

        for op_ref, amount, trans_date, batch_id, details in transactions:
            stats['processed'] += 1

            # Determine source
            source = get_sursa_incasare(details)

            # Prepare record
            record = {
                'op_reference': op_ref,
                'transaction_date': trans_date,
                'amount': amount,
                'source': source,
                'batch_id': batch_id,
                'details': details,
                'file_name': file_names[0] if file_names else None
            }

            try:
                # Try to insert (will fail if duplicate due to UNIQUE constraint)
                supabase.table('bank_transactions').insert(record).execute()
                stats['inserted'] += 1
            except Exception as e:
                error_str = str(e)
                if 'duplicate' in error_str.lower() or '23505' in error_str:
                    stats['skipped'] += 1
                else:
                    stats['failed'] += 1
                    stats['errors'].append(f"{op_ref}: {error_str}")

        # Update sync log
        supabase.table('sync_logs').update({
            'status': 'completed',
            'finished_at': datetime.now().isoformat(),
            'records_processed': stats['processed'],
            'records_inserted': stats['inserted'],
            'records_skipped': stats['skipped'],
            'records_failed': stats['failed'],
            'details': json.dumps({'errors': stats['errors'][:10]})  # Keep first 10 errors
        }).eq('id', sync_log_id).execute()

    except Exception as e:
        # Update sync log with error
        supabase.table('sync_logs').update({
            'status': 'failed',
            'finished_at': datetime.now().isoformat(),
            'error_message': str(e)
        }).eq('id', sync_log_id).execute()
        raise

    return stats


def sync_oblio_invoices(
    issued_after: Optional[date] = None,
    issued_before: Optional[date] = None
) -> Dict:
    """
    Sync invoices from Oblio API to Supabase.

    Returns:
        Dict with sync statistics
    """
    supabase = get_supabase_client()

    # Create sync log
    log_response = supabase.table('sync_logs').insert({
        'sync_type': 'oblio_sync',
        'status': 'running',
        'details': json.dumps({
            'issued_after': issued_after.isoformat() if issued_after else None,
            'issued_before': issued_before.isoformat() if issued_before else None
        })
    }).execute()
    sync_log_id = log_response.data[0]['id']

    stats = {
        'processed': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    try:
        # Get invoices from Oblio
        invoices = get_all_invoices(issued_after, issued_before)

        for invoice in invoices:
            stats['processed'] += 1

            try:
                # Transform to DB format
                db_record = transform_invoice_for_db(invoice)
                db_record['updated_at'] = datetime.now().isoformat()

                # Try upsert (insert or update)
                supabase.table('invoices').upsert(
                    db_record,
                    on_conflict='oblio_id'
                ).execute()

                stats['inserted'] += 1

            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append(f"{invoice.get('number')}: {str(e)}")

        # Update sync log
        supabase.table('sync_logs').update({
            'status': 'completed',
            'finished_at': datetime.now().isoformat(),
            'records_processed': stats['processed'],
            'records_inserted': stats['inserted'],
            'records_skipped': stats['skipped'],
            'records_failed': stats['failed'],
            'details': json.dumps({'errors': stats['errors'][:10]})
        }).eq('id', sync_log_id).execute()

    except Exception as e:
        supabase.table('sync_logs').update({
            'status': 'failed',
            'finished_at': datetime.now().isoformat(),
            'error_message': str(e)
        }).eq('id', sync_log_id).execute()
        raise

    return stats


def get_profit_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    group_by: str = 'month'  # day, month, year
) -> List[Dict]:
    """
    Get profit data grouped by time period.

    Args:
        start_date: Start date filter
        end_date: End date filter
        group_by: Grouping period (day, month, year)

    Returns:
        List of dicts with date and amount
    """
    supabase = get_supabase_client()

    # Build query
    query = supabase.table('bank_transactions').select('transaction_date, amount, source')

    if start_date:
        query = query.gte('transaction_date', start_date.isoformat())
    if end_date:
        query = query.lte('transaction_date', end_date.isoformat())

    response = query.order('transaction_date').execute()
    transactions = response.data

    # Group by period
    grouped = {}
    for trans in transactions:
        trans_date = datetime.strptime(trans['transaction_date'], '%Y-%m-%d')

        if group_by == 'day':
            key = trans_date.strftime('%Y-%m-%d')
        elif group_by == 'month':
            key = trans_date.strftime('%Y-%m')
        else:  # year
            key = trans_date.strftime('%Y')

        if key not in grouped:
            grouped[key] = {'date': key, 'total': 0, 'by_source': {}}

        grouped[key]['total'] += float(trans['amount'])

        source = trans['source']
        if source not in grouped[key]['by_source']:
            grouped[key]['by_source'][source] = 0
        grouped[key]['by_source'][source] += float(trans['amount'])

    return list(grouped.values())


def get_dashboard_stats() -> Dict:
    """Get statistics for dashboard."""
    supabase = get_supabase_client()

    # Get total transactions
    trans_response = supabase.table('bank_transactions').select('amount, source').execute()
    transactions = trans_response.data

    total_amount = sum(float(t['amount']) for t in transactions)
    total_count = len(transactions)

    # Group by source
    by_source = {}
    for t in transactions:
        source = t['source']
        if source not in by_source:
            by_source[source] = {'count': 0, 'amount': 0}
        by_source[source]['count'] += 1
        by_source[source]['amount'] += float(t['amount'])

    # Get invoice stats
    inv_response = supabase.table('invoices').select('total, invoice_type').execute()
    invoices = inv_response.data

    invoice_total = sum(float(i['total']) for i in invoices if i['invoice_type'] == 'Normala')
    invoice_count = len([i for i in invoices if i['invoice_type'] == 'Normala'])

    return {
        'bank_transactions': {
            'total_amount': total_amount,
            'total_count': total_count,
            'by_source': by_source
        },
        'invoices': {
            'total_amount': invoice_total,
            'total_count': invoice_count
        }
    }


def get_recent_sync_logs(limit: int = 10) -> List[Dict]:
    """Get recent sync logs."""
    supabase = get_supabase_client()

    response = supabase.table('sync_logs')\
        .select('*')\
        .order('started_at', desc=True)\
        .limit(limit)\
        .execute()

    return response.data
