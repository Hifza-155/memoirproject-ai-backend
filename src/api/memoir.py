"""
@file api/memoir.py
@description FastAPI router handling HTTP endpoints for memoir creation and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from src.schemas.memoir import MemoirCreateRequest
from src.domain.memoir_service import MemoirService
from src.core.auth import get_current_user  # Production JWT verification dependency

router = APIRouter(prefix="/api/memoirs", tags=["Memoirs"])

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_memoir(
    payload: MemoirCreateRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Creates a new root memoir container for a subject. 
    This must be executed first to obtain a memoir_id before adding media or memories.
    """
    user_session = {"user_id": current_user_id}
    new_memoir = MemoirService.create_memoir(payload, user_session)
    return {
        "success": True,
        "message": "Memoir successfully created.",
        "data": new_memoir
    }