from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class ShareLinkUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expires_at: Optional[datetime] = None  # The only thing an owner might realistically update

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

class ShareLinkResponseEnvelope(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    data: ShareLinkResponse

class SharedMemoirResponseEnvelope(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    data: Dict[str, Any]