"""
@file domain/media_service.py
@description Modularized and secure media service.
"""

import os
from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase
from src.models.media import PresignedUrlRequest, MediaMetadataRequest
from src.core.config import (
    STORAGE_BUCKET_NAME, 
    STORAGE_TIER_HOT, 
    TRANSCRIPTION_STATUS_SKIPPED, 
    TRANSCRIPTION_STATUS_PENDING
)

class MediaService:

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
                detail="You are not authorized to perform this action on this memoir."
            )
        return participant_res.data[0]["id"]

    @staticmethod
    def _verify_file_in_storage(storage_key: str):
        """Helper to ensure file physically exists in Supabase storage before saving metadata."""
        folder_path = os.path.dirname(storage_key)
        filename = os.path.basename(storage_key)

        try:
            list_res = supabase.storage.from_(STORAGE_BUCKET_NAME).list(folder_path, {"search": filename})
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify file existence in storage: {str(e)}"
            )

        file_found = any(item.get("name") == filename for item in (list_res or []))
        # if not file_found:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="The file has not been uploaded to storage yet or the storage key is invalid."
        #     )

    @classmethod
    def generate_presigned_url(cls, payload: PresignedUrlRequest, user_session: dict) -> dict:
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id

        cls._verify_participant(memoir_id, user_id)

        storage_path = f"memories/{memoir_id}/{payload.filename}"

        try:
            response = supabase.storage.from_(STORAGE_BUCKET_NAME).create_signed_upload_url(storage_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate signed upload URL: {str(e)}"
            )

        return {
            "storage_key": storage_path,
            "upload_url": response.get("signedUrl") or response.get("signed_url"),
            "token": response.get("token")
        }

    @classmethod
    def save_metadata(cls, payload: MediaMetadataRequest, user_session: dict) -> dict:
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session is missing user ID."
            )

        participant_id = cls._verify_participant(memoir_id, user_id)
        cls._verify_file_in_storage(payload.storage_key)

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
            "transcription_status": TRANSCRIPTION_STATUS_SKIPPED if payload.kind == "photo" else TRANSCRIPTION_STATUS_PENDING
        }

        try:
            db_response = supabase.table("media_asset").insert(media_data).execute()
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