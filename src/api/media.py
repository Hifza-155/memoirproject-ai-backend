"""
@file api/media.py
@description FastAPI router for media presigned URLs and metadata.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from src.models.media import PresignedUrlRequest, MediaMetadataRequest
from src.domain.media_service import MediaService

router = APIRouter(prefix="/api/media", tags=["Media Management"])

# Session only provides the authenticated user's ID
MOCK_USER_SESSION = {
    "user_id": "1c65d3b5-0de1-47a0-82cc-ea1f210c596c"
}

@router.post("/presigned-url")
def create_presigned_url(
    payload: PresignedUrlRequest, 
    user_session: dict = Depends(lambda: MOCK_USER_SESSION)
):
    """
    Generates a presigned storage URL after validating user permissions for the requested memoir.
    """
    if not user_session or not user_session.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in to upload media."
        )

    data = MediaService.generate_presigned_url(payload, user_session)
    return {
        "success": True,
        "data": data
    }

@router.post("/metadata", status_code=status.HTTP_201_CREATED)
def save_metadata(
    payload: MediaMetadataRequest,
    user_session: dict = Depends(lambda: MOCK_USER_SESSION)
):
    if not user_session or not user_session.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session is missing user ID."
        )

    saved_record = MediaService.save_metadata(payload, user_session)
    return {
        "success": True,
        "message": "Media metadata successfully saved.",
        "data": saved_record
    }