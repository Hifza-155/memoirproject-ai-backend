"""
@file models/media.py
@description Pydantic models for media presigned URL and metadata validation.
"""

from pydantic import BaseModel, Field , field_validator
from typing import Optional

class PresignedUrlRequest(BaseModel):
    memoir_id: str = Field(..., description="UUID of the parent memoir")
    filename: str = Field(..., description="Original name of the file being uploaded")
    file_type: str = Field(..., description="MIME type of the file (e.g., image/jpeg, audio/mpeg)")

class MediaMetadataRequest(BaseModel):
    memoir_id: str = Field(..., description="UUID of the parent memoir")
    storage_key: str = Field(..., description="Storage path key in Supabase storage")
    kind: str = Field(..., description="Media kind: 'photo', 'audio', or 'video'")
    mime_type: str = Field(..., description="MIME type of the file")
    byte_size: int = Field(..., description="Size of the file in bytes")
    original_filename: Optional[str] = Field(None, description="Original filename")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds (null for photos)")
    width_px: Optional[int] = Field(None, description="Width in pixels (null for audio)")
    height_px: Optional[int] = Field(None, description="Height in pixels (null for audio)")
    caption: Optional[str] = Field(None, description="Optional caption for the media")
    checksum_sha256: Optional[str] = Field(None, description="Optional file checksum")
    
    @field_validator('kind')
    @classmethod
    def validate_media_kind(cls, v: str) -> str:
        allowed_kinds = {'photo', 'audio'}
        if v not in allowed_kinds:
            raise ValueError(f"Invalid media kind '{v}'. Must be one of {allowed_kinds}.")
        return v