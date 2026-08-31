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
from src.core.config import (
    STORAGE_TIER_HOT, 
    TRANSCRIPTION_STATUS_SKIPPED, 
    TRANSCRIPTION_STATUS_PENDING
)


class MediaService:
    """
    Handles business rules, participant access controls, security validations, 
    and database record cataloging for media assets.
    """

    @staticmethod
    def _verify_participant(memoir_id: str, user_id: str) -> str:
        """
        Verifies whether a user is an authorized participant of a specific memoir container.

        Args:
            memoir_id (str): The unique identifier of the target memoir.
            user_id (str): The unique identifier of the requesting user.

        Returns:
            str: The participant record ID associated with the user and memoir.

        Raises:
            HTTPException (500): If a database query error occurs.
            HTTPException (403): If the user is not an authorized participant.
        """
        try:
            participant_res = media_repository.fetch_participant(memoir_id, user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while verifying permissions: {str(e)}"
            )

        if not participant_res or not participant_res.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to perform this action on this memoir."
            )
        return participant_res.data[0]["id"]

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

        cls._verify_participant(memoir_id, user_id)

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
        prevents duplicate ghost records via checksum idempotency, and persists metadata.

        Args:
            payload (MediaMetadataRequest): The validated media metadata object.
            user_session (dict): The active user session dictionary containing the user ID.

        Returns:
            dict: The newly created or existing database media asset record.

        Raises:
            HTTPException (401): If the user session lacks a valid user ID.
            HTTPException (400): If the storage key fails cross-tenant prefix validation.
            HTTPException (500): If database insertion fails.
        """
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session is missing user ID."
            )

        participant_id = cls._verify_participant(memoir_id, user_id)

        # SECURITY FIX: Enforce tenant isolation — ensure the storage key explicitly belongs 
        # to this memoir ID to prevent cross-tenant asset hijacking.
        expected_prefix = f"memoirs/{memoir_id}/"
        if not payload.storage_key.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage key path for this memoir container."
            )

        # IDEMPOTENCY CHECK: Prevent duplicate media asset records if a request is retried
        if payload.checksum_sha256:
            existing = media_repository.check_existing_media_by_checksum(str(memoir_id), payload.checksum_sha256)
            if existing:
                # Return the existing record safely instead of creating a duplicate ghost row
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