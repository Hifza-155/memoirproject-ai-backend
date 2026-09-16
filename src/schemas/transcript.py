"""
@file transcript.py
@description Pydantic schemas for audio transcription validation and requests.
"""

from pydantic import BaseModel, Field

class TranscriptionRequest(BaseModel):
    media_asset_id: str = Field(..., description="The UUID of the audio media asset")
    memoir_id: str = Field(..., description="The UUID of the memoir container")
    storage_key: str = Field(..., description="The storage path key inside the Supabase bucket")