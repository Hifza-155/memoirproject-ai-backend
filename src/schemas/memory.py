"""
@file models/memory.py
@description Pydantic models for memory creation matching the schema.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

class MemoryCreateRequest(BaseModel):
    memoir_id: str
    title: Optional[str] = None
    body_text: Optional[str] = None
    status: str = "draft"
    occurred_start: Optional[str] = None
    occurred_end: Optional[str] = None
    occurred_precision: Optional[str] = None
    date_source: Optional[str] = None
    media_asset_ids: Optional[List[str]] = Field(default=[])
    
class MemoryUpdateRequest(BaseModel):
    title: Optional[str] = None
    body_text: Optional[str] = None
    status: Optional[str] = None
    occurred_start: Optional[str] = None
    media_asset_ids: Optional[List[str]] = Field(default=None, description="Updated list of media assets.")