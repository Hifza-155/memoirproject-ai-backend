"""
@file api/media.py
@description FastAPI router handling HTTP endpoints for media presigned URLs and metadata recording.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from src.models.media import PresignedUrlRequest, MediaMetadataRequest
from src.domain.media_service import MediaService

router = APIRouter(prefix="/api/media", tags=["Media Upload & Metadata"])

# Valid dummy UUIDs for mock testing so Postgres doesn't reject them
MOCK_SESSION = {
    "id": "00000000-0000-0000-0000-000000000001",
    "memoir_id": "00000000-0000-0000-0000-000000000002",
    "participant_id": "00000000-0000-0000-0000-000000000003"
}

@router.post("/presigned-url")
def create_presigned_url(
    payload: PresignedUrlRequest, 
    user_session: dict = Depends(lambda: MOCK_SESSION)
):
    if not user_session or not user_session.get("id") or not user_session.get("memoir_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in as a memoir owner to upload media."
        )

    data = MediaService.generate_presigned_url(payload, user_session)
    return {
        "success": True,
        "data": data
    }


@router.post("/metadata", status_code=status.HTTP_201_CREATED)
def save_media_metadata(
    payload: MediaMetadataRequest,
    user_session: dict = Depends(lambda: MOCK_SESSION)
):
    if not user_session or not user_session.get("memoir_id") or not user_session.get("participant_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing user session or participant context."
        )

    saved_record = MediaService.save_metadata(payload, user_session)
    return {
        "success": True,
        "message": "Media metadata successfully recorded.",
        "data": saved_record
    }