"""
@file models/media.py
@description Pydantic validation models for media upload and metadata.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional

class PresignedUrlRequest(BaseModel):
    file_name: str = Field(..., description="Original name of the file")
    file_type: str = Field(..., description="MIME type of the file (e.g., image/jpeg, audio/webm)")
    file_size: int = Field(..., description="Size of the file in bytes", gt=0)


class MediaMetadataRequest(BaseModel):
    storage_key: str = Field(..., description="The unique storage path key returned from Supabase storage")
    kind: str = Field(..., description="Media kind: either 'photo' or 'audio'")
    mime_type: str = Field(..., description="MIME type of the file")
    byte_size: int = Field(..., description="Size of the file in bytes", gt=0)
    original_filename: Optional[str] = Field(None, description="Original filename from client")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds (required for audio, null for photos)")
    width_px: Optional[int] = Field(None, description="Width in pixels (optional, for photos)")
    height_px: Optional[int] = Field(None, description="Height in pixels (optional, for photos)")
    caption: Optional[str] = Field(None, description="Optional text caption for the asset")
    checksum_sha256: Optional[str] = Field(None, description="Optional SHA-256 checksum for deduplication")

    @field_validator('kind')
    @classmethod
    def validate_media_kind(cls, v: str) -> str:
        allowed_kinds = {'photo', 'audio'}
        if v not in allowed_kinds:
            raise ValueError(f"Invalid media kind '{v}'. Must be one of {allowed_kinds}.")
        return v