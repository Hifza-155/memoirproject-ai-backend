"""
@file domain/media_service.py
@description Core business logic service managing memoir participant authorizations,
secure path generation, upload validation, and database metadata persistence,
fully decoupled from direct infrastructure calls and secured against path traversal.
"""

from fastapi import HTTPException, status
from src.integrations import media_repository
from src.integrations import storage_adapter
from src.schemas.media import PresignedUrlRequest, MediaMetadataRequest
from src.domain.authorization import verify_active_participant

from src.core.config import (
    STORAGE_TIER_HOT, 
    TRANSCRIPTION_STATUS_PENDING
)


class MediaService:
    """
    Handles business rules, participant access controls, security validations, 
    and database record cataloging for media assets.
    """


    @classmethod
    def generate_presigned_url(cls, payload: PresignedUrlRequest, user_session: dict) -> dict:
        """
        Authorizes user access to a memoir, validates file upload limits/types, 
        generates a collision-free secure path, and requests a short-lived signed upload URL.

        Args:
            payload (PresignedUrlRequest): The request payload containing memoir ID, MIME type, and size.
            user_session (dict): The active user session dictionary containing the user ID.

        Returns:
            dict: A dictionary containing the secure storage key, signed upload URL, and token.

        Raises:
            HTTPException (500): If the storage provider fails to generate the signed URL.
        """
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id
        
        verify_active_participant(
            memoir_id, 
            user_id, 
            required_roles=["owner", "admin", "contributor"]
        )

        # SECURITY FIX: Enforce file size and type validation via the storage adapter
        media_type, extension = storage_adapter.validate_upload(payload.mime_type, payload.byte_size)
        
        # SECURITY FIX: Prevent path traversal by generating a secure UUID-based path key 
        # instead of trusting raw user filenames.
        storage_path = storage_adapter.build_key(memoir_id, media_type, extension)

        try:
            upload_res = storage_adapter.create_signed_upload(storage_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate signed upload URL: {str(e)}"
            )

        return {
            "storage_key": upload_res.path,
            "upload_url": upload_res.signed_url,
            "token": upload_res.token
        }

    @classmethod
    def save_metadata(cls, payload: MediaMetadataRequest, user_session: dict) -> dict:
        """
        Validates user session permissions, enforces tenant isolation on the storage key, 
        confirms physical object existence in storage, validates kind-specific rules,
        prevents duplicate ghost records via checksum idempotency, and persists metadata.
        """
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id

        participant = verify_active_participant(
            memoir_id, 
            user_id, 
            required_roles=["owner", "admin", "contributor"]
        )
        participant_id = participant["id"]

        # SECURITY FIX: Enforce tenant isolation — ensure the storage key explicitly belongs 
        # to this memoir ID to prevent cross-tenant asset hijacking.
        expected_prefix = f"memoirs/{memoir_id}/"
        if not payload.storage_key.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage key path for this memoir container."
            )

        # 1. STORAGE EXISTENCE CHECK: Verify the file actually exists in storage
        try:
            file_exists = storage_adapter.object_exists(payload.storage_key)
        except Exception:
            file_exists = False

        if not file_exists:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The referenced file does not exist in storage. Please upload the file first."
            )

        # 2. KIND-SPECIFIC VALIDATION: Ensure audio and video assets provide a valid duration
        if payload.kind in ["audio", "video"] and (payload.duration_ms is None or payload.duration_ms <= 0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Audio and video assets require a valid positive duration_ms."
            )

        # IDEMPOTENCY CHECK: Prevent duplicate media asset records if a request is retried
        if payload.checksum_sha256:
            existing = media_repository.check_existing_media_by_checksum(str(memoir_id), payload.checksum_sha256)
            if existing:
                return existing

        media_data = {
            "memoir_id": memoir_id,
            "uploaded_by_participant_id": participant_id,
            "storage_key": payload.storage_key,
            "kind": payload.kind,
            "mime_type": payload.mime_type,
            "byte_size": payload.byte_size,
            "original_filename": payload.original_filename,
            "duration_ms": payload.duration_ms,
            "width_px": payload.width_px,
            "height_px": payload.height_px,
            "caption": payload.caption,
            "checksum_sha256": payload.checksum_sha256,
            "storage_tier": STORAGE_TIER_HOT,
            "transcription_status": STORAGE_TIER_HOT if payload.kind == "photo" else TRANSCRIPTION_STATUS_PENDING
        }

        try:
            db_response = media_repository.insert_media_metadata(media_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while saving media metadata: {str(e)}"
            )

        if not db_response or not db_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save media metadata record in database."
            )

        return db_response.data[0]