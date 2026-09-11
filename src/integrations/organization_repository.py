from typing import Dict, Any, List
from src.integrations.supabase_client import supabase_admin

def fetch_memories_for_ai(memoir_id: str) -> List[Dict[str, Any]]:
    """
    Fetches active submitted memories for the memoir.
    Retrieves only textual content and timestamps to minimize token payload.
    """
    res = supabase_admin.table("memory") \
        .select("id, title, body_text, occurred_start") \
        .eq("memoir_id", memoir_id) \
        .eq("status", "submitted") \
        .is_("deleted_at", "null") \
        .execute()
    return res.data or []

def apply_ai_organization(memoir_id: str, ai_output: dict):
    """
    Persists AI-proposed chapters and updates memory references according to the chapter table schema.
    """
    try:
        # 1. Clear previous AI-generated chapters that haven't been manually locked/edited by the owner
        supabase_admin.table("chapter") \
            .delete() \
            .eq("memoir_id", memoir_id) \
            .eq("edited_by_owner", False) \
            .execute()

        # 2. Insert proposed chapters matching official table schema
        for chapter_data in ai_output.get("chapters", []):
            chapter_payload = {
                "memoir_id": memoir_id,
                "title": chapter_data["title"],
                "summary": chapter_data.get("summary"),
                "sort_order": chapter_data["sort_order"],
                "created_by": "ai",
                "edited_by_owner": False
            }
            
            chapter_res = supabase_admin.table("chapter") \
                .insert(chapter_payload) \
                .select("id") \
                .execute()

            if not chapter_res.data:
                continue

            new_chapter_id = chapter_res.data[0]["id"]

            # 3. Associate memories with the new chapter
            for memory_ref in chapter_data.get("memories", []):
                update_payload = {"chapter_id": new_chapter_id}
                if memory_ref.get("inferred_date"):
                    update_payload["occurred_precision"] = memory_ref["inferred_date"]

                supabase_admin.table("memory") \
                    .update(update_payload) \
                    .eq("id", memory_ref["memory_id"]) \
                    .eq("memoir_id", memoir_id) \
                    .execute()

    except Exception as e:
        print(f"Error applying AI organization to database: {str(e)}")
        raise e