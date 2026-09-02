"""
@file api/memoir.py
@description FastAPI router handling HTTP endpoints for memoir creation and management.
"""

from fastapi import APIRouter, Depends, status
from src.schemas.memoir import MemoirCreateRequest, MemoirResponseEnvelope
from src.domain.memoir_service import MemoirService
from src.core.auth import get_current_user

router = APIRouter(prefix="/api/memoirs", tags=["Memoirs"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MemoirResponseEnvelope)
def create_memoir(
    payload: MemoirCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new root memoir container for a subject. 
    This must be executed first to obtain a memoir_id before adding media or memories.
    """
    # extract user ID string from the dictionary
    user_id = current_user.get("user_id") or current_user.get("id") or current_user.get("sub")
    
    user_session = {"user_id": user_id}
    new_memoir = MemoirService.create_memoir(payload, user_session)
    return {
        "success": True,
        "message": "Memoir successfully created.",
        "data": new_memoir
    }