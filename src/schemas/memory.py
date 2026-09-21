import uuid
from datetime import date
from typing import Optional, Literal, List, Any
from pydantic import BaseModel, Field

class MemoryCreateRequest(BaseModel):
    memoir_id: uuid.UUID = Field(..., description="UUID of the parent memoir container")
    title: Optional[str] = Field(None, max_length=255)
    body_text: Optional[str] = Field(None, max_length=10000)
    status: Literal["draft", "submitted"] = Field("draft")    
    occurred_start: Optional[date] = Field(None)
    occurred_end: Optional[date] = Field(None)
    
    # FIX: Defaults removed. Will safely pass as None if no dates are provided.
    occurred_precision: Optional[Literal["day", "month", "year", "decade"]] = Field(None)
    date_source: Optional[Literal["owner", "contributor", "ai"]] = Field(None)
    
    media_asset_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)

class MemoryResponse(BaseModel):
    id: uuid.UUID
    memoir_id: uuid.UUID
    title: Optional[str] = None
    body_text: Optional[str] = None
    occurred_start: Optional[date] = None
    media_assets: Optional[List[Any]] = Field(default=[])