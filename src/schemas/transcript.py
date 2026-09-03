import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_asset_id: uuid.UUID
    status: str
    text: str | None
    language: str | None
    confidence: float | None
    error_message: str | None
    attempt_count: int
    edited_at: datetime | None
    created_at: datetime


class TranscriptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=50_000)