from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from passlib.context import CryptContext

from src.core.config import settings
from src.core.auth import get_current_user
from src.domain.share_service import ShareService
from src.integrations.share_repository import ShareRepository
from src.schemas.share import (
    ShareLinkResponse, ShareLinkResponseEnvelope, ShareLinkUpdateRequest, 
    ShareLinkVerifyRequest, SharedMemoirResponseEnvelope
)

owner_router = APIRouter(prefix="/api/memoirs", tags=["Share Links"])
reader_router = APIRouter(prefix="/api/share", tags=["Shared Memoirs"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _to_link_response(link: Dict[str, Any]) -> ShareLinkResponse:
    return ShareLinkResponse(
        id=str(link["id"]),
        memoir_id=str(link["memoir_id"]),
        scope=link["scope"],
        token=link["token"],
        url=f"{settings.share_link_base_url.rstrip('/')}/{link['token']}",
        created_by_participant_id=str(link["created_by_participant_id"]) if link.get("created_by_participant_id") else None,
        created_at=link["created_at"],
        expires_at=link.get("expires_at"),
        revoked_at=link.get("revoked_at"),
        open_count=link.get("open_count", 0),
        # NEW: Check if password_hash is present in the database row
        is_protected=bool(link.get("password_hash"))
    )

# --- OWNER ROUTES ---
@owner_router.post("/{memoir_id}/share-link", status_code=201, response_model=ShareLinkResponseEnvelope)
async def create_share_link(memoir_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))
    link = await ShareService.create_or_get_share_link(memoir_id, user_id)
    return {"success": True, "message": "Share link ready.", "data": _to_link_response(link)}

@owner_router.patch("/{memoir_id}/share-link", response_model=ShareLinkResponseEnvelope)
async def patch_share_link(memoir_id: str, payload: ShareLinkUpdateRequest, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))
    link = await ShareService.update_share_link(memoir_id, user_id, payload)
    return {"success": True, "message": "Share link updated.", "data": _to_link_response(link)}

@owner_router.delete("/{memoir_id}/share-link", status_code=200)
async def delete_share_link(memoir_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))
    await ShareService.revoke_share_link(memoir_id, user_id)
    return {"success": True, "message": "Share link revoked."}


# --- READER/CONTRIBUTOR ROUTES ---

@reader_router.post("/{token}/verify", response_model=SharedMemoirResponseEnvelope)
async def verify_and_access_shared_memoir(token: str, payload: ShareLinkVerifyRequest, response: Response):
    """
    Gatekeeper endpoint: Validates token and password, sets a secure cookie for the contributor name,
    and returns the shared memoir view if successful.
    """
    link = await ShareRepository.get_link_by_token(token)
    
    if not link or link.get("revoked_at"):
        raise HTTPException(status_code=404, detail="Not found.")
    
    if link.get("expires_at"):
        expires_at = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=404, detail="Link expired.")

    # Validate password if the link is protected
    if link.get("password_hash"):
        if not payload.password or not pwd_context.verify(payload.password, link["password_hash"]):
            raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")

    memoir = await ShareRepository.get_memoir_by_id(link["memoir_id"])
    if not memoir:
        raise HTTPException(status_code=404, detail="Memoir not found.")

    # Set secure HttpOnly cookie with the contributor's name for attribution when they post memories
    response.set_cookie(
        key=f"contributor_name_{link['memoir_id']}",
        value=payload.contributor_name,
        httponly=True,
        secure=True,  # Set to False if you are testing locally on plain http:// instead of https://
        samesite="lax",
        max_age=60 * 60 * 24  # Valid for 24 hours (in seconds)
    )
    # Increment open count and fetch view
    await ShareRepository.increment_open_count(link["id"], link.get("open_count", 0))
    memories = await ShareRepository.get_shared_memoir_view(link["memoir_id"])
    
    data = {
        **memoir,
        "can_comment": memoir.get("comment_policy") == "public",
        "memories": memories,
        "contributor_name": payload.contributor_name
    }
    return {"success": True, "message": "Access granted", "data": data}


@reader_router.get("/{token}", response_model=SharedMemoirResponseEnvelope)
async def read_shared_memoir(token: str):
    link = await ShareRepository.get_link_by_token(token)
    
    if not link or link.get("revoked_at"):
        raise HTTPException(status_code=404, detail="Not found.")
    
    if link.get("expires_at"):
        expires_at = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=404, detail="Link expired.")

    # NEW: If the link requires a password, a simple GET should return metadata or status 
    # indicating a password is required so the frontend can display the gatekeeper screen.
    if link.get("password_hash"):
        return {
            "success": True,
            "message": "Password required",
            "data": {
                "requires_password": True,
                "memoir_id": str(link["memoir_id"])
            }
        }

    memoir = await ShareRepository.get_memoir_by_id(link["memoir_id"])
    if not memoir:
        raise HTTPException(status_code=404, detail="Memoir not found.")

    await ShareRepository.increment_open_count(link["id"], link.get("open_count", 0))
    memories = await ShareRepository.get_shared_memoir_view(link["memoir_id"])
    
    data = {
        **memoir,
        "can_comment": memoir.get("comment_policy") == "public",
        "memories": memories,
        "requires_password": False
    }
    return {"success": True, "message": "Operation successful", "data": data}