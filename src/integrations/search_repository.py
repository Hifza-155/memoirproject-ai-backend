"""
@file integrations/search_repository.py
@description Executes full-text search queries against PostgreSQL search vectors.
"""

from src.integrations.supabase_client import supabase_admin

def search_memoir_content(memoir_id: str, query_text: str):
    """
    Calls a Postgres RPC function to perform a full-text search 
    across memories, transcripts, and media captions filtered by memoir_id.
    """
    response = supabase_admin.rpc(
        "search_memoirs_fts", 
        {
            "target_memoir_id": memoir_id,
            "search_query": query_text
        }
    ).execute()
    
    return response.data if response.data else []