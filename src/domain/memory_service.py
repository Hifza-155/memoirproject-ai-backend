"""
@file domain/memory_service.py
@description Service handling memory creation with correct schema mapping.
"""

from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase
from src.models.memory import MemoryCreateRequest

class MemoryService:

    @staticmethod
    def _verify_participant(memoir_id: str, user_id: str) -> str:
        """Helper to verify participant access and return participant ID."""
        try:
            participant_res = supabase.table("memoir_participant") \
                .select("id") \
                .eq("memoir_id", memoir_id) \
                .eq("user_id", user_id) \
                .execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while verifying permissions: {str(e)}"
            )

        if not participant_res or not participant_res.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to manage memories for this memoir."
            )
        return participant_res.data[0]["id"]

    @classmethod
    def create_memory(cls, payload: MemoryCreateRequest, user_session: dict) -> dict:
        user_id = user_session.get("user_id")
        participant_id = cls._verify_participant(payload.memoir_id, user_id)

        # 1. Insert memory record using correct schema column: author_participant_id
        memory_data = {
            "memoir_id": payload.memoir_id,
            "author_participant_id": participant_id,
            "title": payload.title,
            "body_text": payload.body_text,
            "status": payload.status,
            "occurred_start": payload.occurred_start
        }

        try:
            mem_res = supabase.table("memory").insert(memory_data).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while creating memory: {str(e)}"
            )

        if not mem_res or not mem_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create memory record."
            )

        new_memory = mem_res.data[0]
        memory_id = new_memory["id"]

        # 2. Link media assets if provided (Combining text + audio/photo into ONE memory)
        if payload.media_asset_ids:
            link_records = [
                {
                    "memory_id": memory_id,
                    "media_asset_id": media_id,
                    "memoir_id": payload.memoir_id  # <-- Added memoir_id here!
                }
                for media_id in payload.media_asset_ids
            ]
            try:
                supabase.table("memory_media").insert(link_records).execute()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to link media assets to memory: {str(e)}"
                )
        return new_memory

    @classmethod
    def get_memoir_feed(cls, memoir_id: str, user_session: dict) -> dict:
        user_id = user_session.get("user_id")
        cls._verify_participant(memoir_id, user_id)

        try:
            memories_res = supabase.table("memory") \
                .select("*") \
                .eq("memoir_id", memoir_id) \
                .is_("deleted_at", "null") \
                .order("created_at", desc=True) \
                .execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while fetching memoir feed: {str(e)}"
            )

        memories = memories_res.data or []

        if not memories:
            return {
                "memoir_id": memoir_id,
                "is_empty": True,
                "message": "This memoir has no memories yet. Start capturing your first written, audio, or photographic memory below.",
                "memories": []
            }

        return {
            "memoir_id": memoir_id,
            "is_empty": False,
            "memories": memories
        }

    @classmethod
    def delete_memory(cls, memory_id: str, user_session: dict) -> dict:
        user_id = user_session.get("user_id")

        try:
            mem_res = supabase.table("memory").select("memoir_id, status").eq("id", memory_id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        if not mem_res.data:
            raise HTTPException(status_code=404, detail="Memory not found.")

        memory = mem_res.data[0]
        cls._verify_participant(memory["memoir_id"], user_id)

        if memory["status"] == "published":
            raise HTTPException(status_code=400, detail="Cannot delete a published memory.")

        try:
            supabase.table("memory").delete().eq("id", memory_id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")

        return {"success": True, "message": "Memory successfully deleted."}