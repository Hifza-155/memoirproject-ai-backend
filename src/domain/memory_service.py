"""
@file memory_service.py
@description Core business logic service managing memory creation with strict 
date timeline normalization, media asset linking, feed retrieval, and lifecycle security,
fully decoupled from direct database infrastructure calls.
"""

from fastapi import HTTPException, status
from src.schemas.memory import MemoryCreateRequest
from src.integrations import memory_repository


class MemoryService:
    """
    Handles business logic for memory stories, including participant security enforcement,
    timeline normalization, media-to-memory junction mapping, and feed processing.
    """

    @staticmethod
    def _verify_participant(memoir_id: str, user_id: str) -> str:
        """
        Verifies whether a user is an authorized participant permitted to manage 
        memories for a specific memoir container.

        Args:
            memoir_id (str): The unique identifier of the target memoir.
            user_id (str): The unique identifier of the requesting user.

        Returns:
            str: The unique participant record ID associated with the user and memoir.

        Raises:
            HTTPException (500): If a database query error occurs during verification.
            HTTPException (403): If the user is not an authorized participant.
        """
        try:
            participant_res = memory_repository.fetch_participant(memoir_id, user_id)
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
        """
        Validates participant permissions, normalizes timeline and date parameters, 
        persists the new memory entry, and maps any attached media asset IDs.

        Args:
            payload (MemoryCreateRequest): The validated memory creation payload.
            user_session (dict): The active user session dictionary containing the user ID.

        Returns:
            dict: The newly created memory database record.

        Raises:
            HTTPException (500): If database insertion or media linking fails.
        """
        user_id = user_session.get("user_id")
        participant_id = cls._verify_participant(payload.memoir_id, user_id)

        # Timeline Date Normalization:
        # Ensures all 4 timeline parameters have valid values or are uniformly set to None.
        if payload.occurred_start:
            occ_start = str(payload.occurred_start)
            occ_end = str(payload.occurred_end) if payload.occurred_end else occ_start
            occ_precision = str(payload.occurred_precision) if payload.occurred_precision else "day"
            dt_source = str(payload.date_source) if payload.date_source else "contributor"
        else:
            occ_start = None
            occ_end = None
            occ_precision = None
            dt_source = None

        memory_data = {
            "memoir_id": payload.memoir_id,
            "author_participant_id": participant_id,
            "title": payload.title,
            "body_text": payload.body_text,
            "status": payload.status,
            "occurred_start": occ_start,
            "occurred_end": occ_end,
            "occurred_precision": occ_precision,
            "date_source": dt_source,
        }

        try:
            mem_res = memory_repository.insert_memory(memory_data)
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

        # Associate attached media assets via the junction table with ownership verification
        if payload.media_asset_ids:
            # SECURITY FIX: Ensure all media assets belong to this memoir (Flag 3)
            owned_assets = memory_repository.verify_media_assets_belong_to_memoir(
                payload.memoir_id, payload.media_asset_ids
            )
            
            if len(owned_assets) != len(payload.media_asset_ids):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="One or more media assets do not belong to this memoir container."
                )

            link_records = [
                {
                    "memory_id": memory_id,
                    "media_asset_id": media_id,
                    "memoir_id": payload.memoir_id
                }
                for media_id in payload.media_asset_ids
            ]
            try:
                memory_repository.insert_memory_media(link_records)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to link media assets to memory: {str(e)}"
                )            
        return new_memory
    
    @classmethod
    def get_memoir_feed(cls, memoir_id: str, user_id: str, limit: int = 20, offset: int = 0) -> dict:
        """
        Retrieves a paginated feed of active memories for a memoir.
        """
        cls._verify_participant(memoir_id, user_id)

        try:
            memories_res = memory_repository.fetch_memoir_feed_records(memoir_id, limit=limit, offset=offset)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while fetching memoir feed: {str(e)}"
            )

        memories = memories_res.data or []

        return {
            "memoir_id": memoir_id,
            "limit": limit,
            "offset": offset,
            "is_empty": len(memories) == 0 and offset == 0,
            "memories": memories
        }
        
    @classmethod
    def delete_memory(cls, memoir_id: str, memory_id: str, user_id: str) -> dict:
        """
        Safely deletes a memory record after confirming participant ownership 
        and ensuring the memory has not been published, fully tenant-scoped.
        """
        # 1. Authorize participant first
        cls._verify_participant(memoir_id, user_id)

        # 2. Fetch memory safely scoped to this memoir
        try:
            mem_res = memory_repository.fetch_memory_by_id(memory_id, memoir_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        if not mem_res.data:
            raise HTTPException(status_code=404, detail="Memory not found in this memoir.")

        memory = mem_res.data[0]

        if memory["status"] == "saved":
            raise HTTPException(status_code=400, detail="Cannot delete a saved/finalized memory.")

        # 3. Delete with strict tenant scoping
        try:
            memory_repository.delete_memory_record(memory_id, memoir_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")
            
        return {"success": True, "message": "Memory successfully deleted."}