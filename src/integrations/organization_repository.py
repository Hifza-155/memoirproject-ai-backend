from typing import Dict, Any, List
from src.integrations.supabase_client import supabase_admin
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def fetch_memories_for_ai(memoir_id: str) -> List[Dict[str, Any]]:
    """Fetches ALL completed (saved) memories for the memoir, ignoring strict status filters."""
    res = supabase_admin.table("memory") \
        .select("id, title, body_text, occurred_start, ai_woven_text") \
        .eq("memoir_id", memoir_id) \
        .is_("deleted_at", "null") \
        .execute()
    return res.data or []

def apply_ai_organization(memoir_id: str, ai_output: dict):
    """
    Calls a Postgres RPC to atomically clear old chapters, insert new ones, 
    and update all memories in a single network round-trip.
    """
    try:
        # Replaces 90+ HTTP round-trips with 1 atomic database transaction!
        supabase_admin.rpc(
            "apply_ai_organization_tx",
            {
                "p_memoir_id": memoir_id,
                "p_chapters": ai_output.get("chapters", [])
            }
        ).execute()
        
    except Exception as e:
        logger.error(f"Error applying AI organization RPC for {memoir_id}: {str(e)}")
        raise e
            
def update_chapter_in_db(chapter_id: str, memoir_id: str, title: str = None, summary: str = None) -> dict:
    """Updates a chapter's text and locks it from future AI deletion."""
    update_payload = {"edited_by_owner": True}
    if title is not None:
        update_payload["title"] = title
    if summary is not None:
        update_payload["summary"] = summary

    # Ensure the chapter belongs to the specified memoir_id for security
    res = supabase_admin.table("chapter") \
        .update(update_payload) \
        .eq("id", chapter_id) \
        .eq("memoir_id", memoir_id) \
        .select() \
        .execute()
        
    if not res.data:
        raise HTTPException(status_code=404, detail="Chapter not found or does not belong to this memoir.")
        
    return res.data[0]

def fetch_archive_raw_data(memoir_id: str) -> dict:
    """Fetches raw chapters and finalized (saved) memories for a memoir directly from Supabase."""
    # Fetch chapters
    chapters_res = supabase_admin.table("chapter") \
        .select("id, title, summary, sort_order") \
        .eq("memoir_id", memoir_id) \
        .order("sort_order") \
        .execute()
    
    chapters = chapters_res.data or []

    # Fetch memories (Status filter removed so it catches all your dashboard memories)
    memories_res = supabase_admin.table("memory") \
        .select("id, title, body_text, occurred_start, chapter_id, ai_woven_text") \
        .eq("memoir_id", memoir_id) \
        .is_("deleted_at", "null") \
        .execute()
        
    memories = memories_res.data or []

    return {
        "chapters": chapters,
        "memories": memories
    }
    
def update_ai_woven_text_in_db(memory_id: str, memoir_id: str, ai_woven_text: str):
    """Updates the AI-woven story text for a specific memory."""
    res = supabase_admin.table("memory") \
        .update({"ai_woven_text": ai_woven_text}) \
        .eq("id", memory_id) \
        .eq("memoir_id", memoir_id) \
        .execute()
    return res.data[0] if res.data else None

def update_generation_status(memoir_id: str, status: str, error_message: str = None):
    """
    Bypassed: Since the memoir_generation table does not exist in your Supabase schema yet,
    we will just log the status to the terminal to prevent the database from crashing the request.
    """
    if error_message:
        logger.error(f"AI Status for {memoir_id}: {status} | Error: {error_message}")
    else:
        logger.info(f"AI Status for {memoir_id}: {status}")
    pass