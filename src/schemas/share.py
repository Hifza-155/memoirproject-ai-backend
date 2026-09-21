from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class ShareLinkUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expires_at: Optional[datetime] = None
    # NEW: Allow owners to set or update a password on the share link
    password: Optional[str] = Field(None, max_length=100, description="Optional access password for contributors")

class ShareLinkVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(..., description="Password required to access the shared memoir")
    contributor_name: str = Field(..., min_length=1, max_length=100, description="Name of the contributor accessing the memoir")

class ShareLinkResponse(BaseModel):
    id: str
    memoir_id: str
    scope: str
    token: str
    url: str
    created_by_participant_id: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    open_count: int
    # NEW: Let the frontend know if this link requires a password so it can show the prompt
    is_protected: bool = False

class ShareLinkResponseEnvelope(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    data: ShareLinkResponse

class SharedMemoirResponseEnvelope(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    data: Dict[str, Any]