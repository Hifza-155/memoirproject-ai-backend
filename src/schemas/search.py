"""
@file schemas/search.py
@description Pydantic schemas for full-text search validation and response payloads.
"""

from pydantic import BaseModel, Field
import uuid

class SearchQueryResponseItem(BaseModel):
    id: str
    memoir_id: str
    title: str | None = None
    body_text: str | None = None
    matched_content_type: str  # e.g., 'memory', 'transcript', 'caption'
    relevance_score: float | None = None