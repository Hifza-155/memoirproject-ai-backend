"""
@file schemas/export.py
@description Pydantic schemas for memoir export request and job status responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExportRequest(BaseModel):
    kind: str = Field(default="pdf", description="Export format kind, e.g., 'pdf'")

class ExportJobResponse(BaseModel):
    export_id: str
    memoir_id: str
    status: str
    message: str
    storage_key: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime