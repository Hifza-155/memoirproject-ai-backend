from datetime import datetime, timezone
from fastapi import HTTPException, status
from passlib.context import CryptContext
from src.core.config import settings
from src.integrations.share_repository import ShareRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ShareService:
    
    @staticmethod
    async def create_or_get_share_link(memoir_id: str, user_id: str, scope: str = "contribute"):
        participant = await ShareRepository.get_participant(memoir_id, user_id)
        if not participant or participant.get("role") != "owner":
            raise HTTPException(status_code=403, detail="Only owners can create share links.")

        existing = await ShareRepository.get_active_link(memoir_id, scope)
        if existing:
            return existing

        insert_data = {
            "memoir_id": memoir_id,
            "scope": scope,
            "created_by_participant_id": participant["id"]
        }
        return await ShareRepository.insert_link(insert_data)

    @staticmethod
    async def update_share_link(memoir_id: str, user_id: str, payload, scope: str = "contribute"):
        participant = await ShareRepository.get_participant(memoir_id, user_id)
        if not participant or participant.get("role") != "owner":
            raise HTTPException(status_code=403, detail="Only owners can update links.")
        
        link = await ShareRepository.get_active_link(memoir_id, scope)
        if not link:
            raise HTTPException(status_code=404, detail="No active share link.")

        update_data = {}
        
        if hasattr(payload, "expires_at") and payload.expires_at is not None:
            update_data["expires_at"] = payload.expires_at.isoformat()

        # Handle password hashing if provided in payload
        if hasattr(payload, "password") and payload.password is not None:
            if payload.password.strip():
                update_data["password_hash"] = pwd_context.hash(payload.password)
            else:
                update_data["password_hash"] = None

        if not update_data:
            return link
            
        return await ShareRepository.update_link(link["id"], update_data)

    @staticmethod
    async def revoke_share_link(memoir_id: str, user_id: str, scope: str = "contribute"):
        participant = await ShareRepository.get_participant(memoir_id, user_id)
        if not participant or participant.get("role") != "owner":
            raise HTTPException(status_code=403, detail="Only owners can revoke links.")
            
        link = await ShareRepository.get_active_link(memoir_id, scope)
        if not link:
            raise HTTPException(status_code=404, detail="No active share link.")

        await ShareRepository.update_link(link["id"], {"revoked_at": datetime.now(timezone.utc).isoformat()})