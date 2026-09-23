import uuid
from datetime import date
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

class TranscriptOut(BaseModel):
    id: str
    raw_text: str
    engine: Optional[str] = None
    confidence: Optional[float] = None
    language: Optional[str] = None
class MediaAssetOut(BaseModel):
    id: str
    kind: str = Field(description="Type of media, e.g., 'audio', 'image'")
    mime_type: Optional[str] = None
    storage_key: Optional[str] = None
    playback_url: Optional[str] = Field(None, description="Secure signed URL for frontend playback/viewing")
    transcript: Optional[TranscriptOut] = Field(None, description="Hydrated transcript data if the asset is audio")

class MemoryCreateRequest(BaseModel):
    memoir_id: uuid.UUID = Field(..., description="UUID of the parent memoir container")
    title: Optional[str] = Field(None, max_length=255)
    body_text: Optional[str] = Field(None, max_length=10000)
    status: Literal["draft", "submitted"] = Field("draft")    
    occurred_start: Optional[date] = Field(None)
    occurred_end: Optional[date] = Field(None)
    occurred_precision: Optional[Literal["day", "month", "year", "decade"]] = Field(None)
    date_source: Optional[Literal["owner", "contributor", "ai"]] = Field(None)
    
    media_asset_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)

class MemoryResponse(BaseModel):
    id: uuid.UUID
    memoir_id: uuid.UUID
    title: Optional[str] = None
    body_text: Optional[str] = None
    occurred_start: Optional[date] = None
    media_assets: Optional[List[MediaAssetOut]] = Field(default_factory=list)