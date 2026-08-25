"""
@file domain/media_service.py
@description Production-ready media service using the official Supabase Storage SDK 
             to generate cryptographically signed upload URLs and handle metadata.
"""

from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase
from src.models.media import PresignedUrlRequest, MediaMetadataRequest

class MediaService:

    @staticmethod
    def generate_presigned_url(payload: PresignedUrlRequest, user_session: dict) -> dict:
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id

        # 1. Verify user authorization against the memoir_participant table
        try:
            participant_res = supabase.table("memoir_participant") \
                .select("id, role") \
                .eq("memoir_id", memoir_id) \
                .eq("user_id", user_id) \
                .execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while verifying upload permissions: {str(e)}"
            )

        if not participant_res or not participant_res.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to upload media to this memoir."
            )

        # 2. Define storage path and bucket name
        storage_path = f"memories/{memoir_id}/{payload.filename}"
        bucket_name = "media-bucket"  # Ensure this bucket is created in your Supabase project

        # 3. Generate real cryptographically signed upload URL using Supabase Storage SDK
        try:
            response = supabase.storage.from_(bucket_name).create_signed_upload_url(storage_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate signed upload URL from storage: {str(e)}"
            )

        if not response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Received empty response from storage provider."
            )

        # Extract signed URL and token from the storage response object/dict
        signed_url = response.get("signedUrl") or response.get("signed_url")
        token = response.get("token")

        return {
            "storage_key": storage_path,
            "upload_url": signed_url,
            "token": token
        }

    @staticmethod
    def save_metadata(payload: MediaMetadataRequest, user_session: dict) -> dict:
        user_id = user_session.get("user_id")
        memoir_id = payload.memoir_id

        # Verify participant status against table
        try:
            participant_res = supabase.table("memoir_participant") \
                .select("id") \
                .eq("memoir_id", memoir_id) \
                .eq("user_id", user_id) \
                .execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while looking up participant: {str(e)}"
            )

        if not participant_res or not participant_res.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a registered participant of this memoir."
            )

        participant_id = participant_res.data[0]["id"]

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
            "storage_tier": "hot",
            "transcription_status": "skipped" if payload.kind == "photo" else "pending"
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