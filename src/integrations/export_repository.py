"""
@file integrations/export_repository.py
@description Database repository for memoir export job tracking and memoir data retrieval.
"""

import os
from datetime import datetime, timezone

from src.integrations.supabase_client import supabase_admin


# Use your project's environment bucket name or fallback to media-bucket
BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "media-bucket")


class ExportRepository:

    @staticmethod
    def create_export_job(memoir_id: str, participant_id: str, kind: str = "pdf") -> dict:
        """Inserts a new export job with 'queued' status."""
        response = supabase_admin.table("memoir_export").insert({
            "memoir_id": memoir_id,
            "requested_by_participant_id": participant_id,
            "kind": kind,
            "status": "queued"
        }).execute()

        if not response.data:
            raise Exception("Failed to create export job record in database.")

        return response.data[0]

    @staticmethod
    def update_job_status(
        export_id: str,
        status: str,
        storage_key: str = None,
        byte_size: int = None,
        error_message: str = None
    ) -> None:
        """Updates the export job status, storage reference, or failure reason."""
        update_data = {
            "status": status,
            "completed_at": (
                datetime.now(timezone.utc).isoformat()
                if status in ["ready", "failed"]
                else None
            )
        }

        if storage_key is not None:
            update_data["storage_key"] = storage_key

        if byte_size is not None:
            update_data["byte_size"] = byte_size

        if error_message is not None:
            update_data["error_message"] = error_message

        supabase_admin.table("memoir_export").update(
            update_data
        ).eq("id", export_id).execute()

    @staticmethod
    def fetch_memoir_export_payload(memoir_id: str) -> dict:
        """
        Fetch all data required to build the memoir PDF.

        The export includes:
        - memoir metadata
        - memoir participants/contributors
        - memories
        - memory-to-media relationships
        - media assets
        - audio transcripts

        Comments are intentionally excluded because the exported PDF
        represents a static keepsake archive.
        """

        # 1. Fetch memoir metadata
        memoir_res = (
            supabase_admin
            .table("memoir")
            .select("*")
            .eq("id", memoir_id)
            .single()
            .execute()
        )

        memoir_data = memoir_res.data if memoir_res and memoir_res.data else {}

        # 2. Fetch memoir participants/contributors
        participants_res = (
            supabase_admin
            .table("memoir_participant")
            .select(
                "id, memoir_id, user_id, role, display_name, email, relationship"
            )
            .eq("memoir_id", memoir_id)
            .execute()
        )

        participants = (
            participants_res.data
            if participants_res and participants_res.data
            else []
        )

        # 3. Fetch memories
        #
        # author_participant_id connects each memory to the
        # memoir_participant record that represents its contributor.
        memories_res = (
            supabase_admin
            .table("memory")
            .select(
                """
                id,
                memoir_id,
                author_participant_id,
                title,
                body_text,
                status,
                occurred_start,
                occurred_end,
                occurred_precision,
                date_source,
                created_at
                """
            )
            .eq("memoir_id", memoir_id)
            .order("occurred_start", desc=False)
            .execute()
        )

        memories = (
            memories_res.data
            if memories_res and memories_res.data
            else []
        )

        # 4. Fetch memory-to-media relationships
        #
        # A media asset belongs to a memory through memory_media.
        memory_ids = [memory["id"] for memory in memories if memory.get("id")]

        memory_media = []

        if memory_ids:
            memory_media_res = (
                supabase_admin
                .table("memory_media")
                .select("memory_id, media_asset_id")
                .in_("memory_id", memory_ids)
                .execute()
            )

            memory_media = (
                memory_media_res.data
                if memory_media_res and memory_media_res.data
                else []
            )

        # 5. Fetch media assets connected to those memories
        media_asset_ids = list({
            relation["media_asset_id"]
            for relation in memory_media
            if relation.get("media_asset_id")
        })

        media_assets = []

        if media_asset_ids:
            media_res = (
                supabase_admin
                .table("media_asset")
                .select(
                    """
                    id,
                    storage_key,
                    kind,
                    caption,
                    mime_type,
                    duration_ms,
                    width_px,
                    height_px,
                    original_filename,
                    uploaded_by_participant_id
                    """
                )
                .in_("id", media_asset_ids)
                .execute()
            )

            media_assets = (
                media_res.data
                if media_res and media_res.data
                else []
            )

        # 6. Fetch transcripts for audio media
        #
        # Transcript text is stored in raw_text.
        # Transcripts are linked through media_asset_id.
        audio_media_ids = [
            media["id"]
            for media in media_assets
            if media.get("kind") == "audio" and media.get("id")
        ]

        transcripts = []

        if audio_media_ids:
            transcripts_res = (
                supabase_admin
                .table("transcript")
                .select("media_asset_id, raw_text")
                .in_("media_asset_id", audio_media_ids)
                .execute()
            )

            transcripts = (
                transcripts_res.data
                if transcripts_res and transcripts_res.data
                else []
            )

        return {
            "memoir": memoir_data,
            "participants": participants,
            "memories": memories,
            "memory_media": memory_media,
            "media_assets": media_assets,
            "transcripts": transcripts
        }

    @staticmethod
    def upload_pdf_to_storage(storage_key: str, pdf_bytes: bytes) -> None:
        """Uploads generated PDF binary stream to Supabase Storage bucket."""
        supabase_admin.storage.from_(BUCKET_NAME).upload(
            path=storage_key,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )

    @staticmethod
    def get_signed_download_url(storage_key: str) -> str:
        """Generates a secure temporary download URL for the exported PDF."""
        res = supabase_admin.storage.from_(BUCKET_NAME).create_signed_url(
            storage_key,
            3600
        )

        return res.get("signedURL") or res.get("signedUrl")

    @staticmethod
    def get_latest_export(memoir_id: str) -> dict:
        res = (
            supabase_admin
            .table("memoir_export")
            .select("*")
            .eq("memoir_id", memoir_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        return res.data[0] if res.data else None