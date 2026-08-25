"""
@file domain/media_service.py
@description Business logic and orchestration for media operations and database insertion.
"""

import time
import re
from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase
from src.models.media import PresignedUrlRequest, MediaMetadataRequest

class MediaService:

    @staticmethod
    def generate_presigned_url(payload: PresignedUrlRequest, user_session: dict) -> dict:
        ALLOWED_MIME_TYPES = {
            "audio/webm", "audio/mp4", "audio/mpeg", "audio/wav",
            "image/jpeg", "image/png", "image/webp"
        }
        MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit

        if payload.file_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The file type '{payload.file_type}' is not supported."
            )

        if payload.file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum allowed limit of 50MB."
            )

        sanitized_file_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', payload.file_name)
        file_path = f"memories/{user_session['memoir_id']}/{int(time.time())}_{sanitized_file_name}"

        response = supabase.storage.from_("media-bucket").create_signed_upload_url(file_path)

        if not response or "signedUrl" not in response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate presigned upload URL from storage provider."
            )

        return {
            "signedUrl": response["signedUrl"],
            "path": response["path"],
            "token": response.get("token")
        }

    @staticmethod
    def save_metadata(payload: MediaMetadataRequest, user_session: dict) -> dict:
        memoir_id = user_session["memoir_id"]
        participant_id = user_session["participant_id"]

        # Enforce database constraints and rules
        if payload.kind == "photo":
            if payload.duration_ms is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Constraint Violation: Photos cannot have a duration."
                )
            transcription_status = "skipped"
        else:  # audio
            if payload.duration_ms is None or payload.duration_ms <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Constraint Violation: Audio assets require a valid positive duration in milliseconds."
                )
            transcription_status = "pending"

        asset_data = {
            "memoir_id": memoir_id,
            "kind": payload.kind,
            "storage_key": payload.storage_key,
            "mime_type": payload.mime_type,
            "byte_size": payload.byte_size,
            "checksum_sha256": payload.checksum_sha256,
            "original_filename": payload.original_filename,
            "duration_ms": payload.duration_ms,
            "width_px": payload.width_px,
            "height_px": payload.height_px,
            "caption": payload.caption,
            "storage_tier": "hot",
            "transcription_status": transcription_status,
            "uploaded_by_participant_id": participant_id
        }

        try:
            db_response = supabase.table("media_asset").insert(asset_data).execute()
        except Exception as e:
            error_message = str(e)
            if "unique constraint" in error_message.lower() or "duplicate key" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A media asset with this storage key already exists."
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {error_message}"
            )

        if not db_response or not db_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save media metadata to the database."
            )

        return db_response.data[0]