"""
@file src/schemas/memory.py
@description Pydantic request and response schemas for memory creation and management,
enforcing strict status literals.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
import uuid


class MemoryCreateRequest(BaseModel):
    """
    Validation schema for creating a new memory record.
    """
    memoir_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    body_text: str = Field(..., min_length=1)
    
    status: Literal["draft", "saved"] = "draft"
    
    media_asset_ids: Optional[list[uuid.UUID]] = None
    occurred_start: Optional[str] = None
    occurred_end: Optional[str] = None
    occurred_precision: Optional[str] = None
    date_source: Optional[str] = None
    