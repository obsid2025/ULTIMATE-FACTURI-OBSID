"""
Supabase client pentru conectare la baza de date
"""

import os
from supabase import create_client, Client
from typing import Optional

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://gfrzetttjnrozlbgyjsa.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdmcnpldHR0am5yb3psYmd5anNhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ2NTY3OTEsImV4cCI6MjA4MDIzMjc5MX0.eqO5xO-RgODMCNwfPmPt7UGiDM9YM-5Ov0Pls3pEFBs')

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def test_connection() -> bool:
    """Test Supabase connection."""
    try:
        client = get_supabase_client()
        # Simple query to test connection
        client.table('sync_logs').select('id').limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase connection error: {e}")
        return False
