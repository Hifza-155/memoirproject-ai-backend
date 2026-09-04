"""
@file memory_service.py
@description Core business logic service managing memory creation with strict 
date timeline normalization, media asset linking, feed retrieval, and lifecycle security,
fully decoupled from direct database infrastructure calls.
"""

from fastapi import HTTPException, status
from src.schemas.memory import MemoryCreateRequest
from src.integrations import memory_repository
from src.domain.authorization import verify_active_participant
from src.integrations import storage_adapter

class MemoryService:
    """
    Handles business logic for memory stories, including participant security enforcement,
    timeline normalization, media-to-memory junction mapping, and feed processing.
    """

    @classmethod
    def create_memory(cls, payload: MemoryCreateRequest, user_id: str) -> dict:        
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
        participant = verify_active_participant(
        str(payload.memoir_id), 
        user_id, 
        required_roles=["owner", "admin", "contributor"]
        )
        participant_id = participant["id"]

        # Timeline Date: Pass through exactly what the user sent without inventing defaults
        # Timeline Date: Pass through exactly what the user sent without inventing defaults
        memory_data = {
            "memoir_id": str(payload.memoir_id),
            "author_participant_id": participant_id, 
            "title": payload.title,
            "body_text": payload.body_text,
            "status": payload.status,
            "occurred_start": payload.occurred_start.isoformat() if payload.occurred_start else None,
            "occurred_end": payload.occurred_end.isoformat() if payload.occurred_end else None,
            "occurred_precision": payload.occurred_precision,
            "date_source": payload.date_source,
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
                "memory_id": str(memory_id),         
                "media_asset_id": str(media_id),     
                "memoir_id": str(payload.memoir_id) 
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
    def get_memoir_feed(cls, memoir_id: str, user_id: str, limit: int = 20, offset: int = 0) -> list:
        """
        Retrieves a paginated memoir memory feed for an active participant, 
        hydrating all attached media assets with secure signed playback URLs.
        """
        # 1. Enforce active participant check
        verify_active_participant(str(memoir_id), str(user_id))

        # 2. Fetch paginated memory records using your repository function
        try:
            res = memory_repository.fetch_memoir_feed_records(str(memoir_id), limit, offset)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch memoir feed: {str(e)}"
            )

        memories = res.data if res and res.data else []

        # 3. Hydrate media assets with secure playback URLs
        hydrated_memories = []
        for mem in memories:
            media_list = []
            raw_links = mem.pop("memory_media", [])
            for link in raw_links:
                asset = link.get("media_asset")
                if asset:
                    storage_key = asset.get("storage_key")
                    playback_url = None
                    if storage_key:
                        try:
                            playback_url = storage_adapter.create_playback_url(storage_key)
                        except Exception:
                            playback_url = None
                    
                    asset["playback_url"] = playback_url
                    media_list.append(asset)
            
            mem["media_assets"] = media_list
            hydrated_memories.append(mem)

        return hydrated_memories
        
    @classmethod
    def delete_memory(cls, memoir_id: str, memory_id: str, user_id: str) -> dict:
        """
        Safely soft-deletes a memory record after confirming the user is either 
        the memory's author or a memoir owner/admin.
        """
        # 1. Fetch participant details to check their role in this memoir
        participant_res = memory_repository.fetch_participant(memoir_id, user_id)
        if not participant_res.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant of this memoir."
            )
        
        participant = participant_res.data[0]
        user_role = participant.get("role")  # e.g., 'owner', 'admin', 'contributor', 'viewer'
        participant_id = participant.get("id")

        # 2. Fetch target memory strictly scoped to this memoir
        try:
            mem_res = memory_repository.fetch_memory_by_id(memory_id, memoir_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        if not mem_res.data:
            raise HTTPException(status_code=404, detail="Memory not found in this memoir.")

        memory = mem_res.data[0]

        # 3. SECURITY CHECK: Restrict deletion to Memoir Owners/Admins OR the Memory Author
        is_owner_or_admin = user_role in ["owner", "admin"]
        is_author = (
            memory.get("author_user_id") == user_id or 
            memory.get("author_participant_id") == participant_id
        )

        if not (is_owner_or_admin or is_author):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this memory."
            )

        if memory.get("status") == "saved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a saved/finalized memory."
            )

        # 4. Perform soft-delete (reversible, matching feed filter .is_('deleted_at', 'null'))
        try:
            memory_repository.soft_delete_memory_record(memory_id, memoir_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete memory: {str(e)}"
            )
            
        return {"success": True, "message": "Memory successfully deleted."}