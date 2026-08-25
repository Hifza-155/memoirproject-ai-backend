"""
@file api/memoir.py
@description FastAPI router handling HTTP endpoints for memoir creation and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from src.models.memoir import MemoirCreateRequest
from src.domain.memoir_service import MemoirService

router = APIRouter(prefix="/api/memoirs", tags=["Memoirs"])

# Mock authenticated user session (Must reference an existing user UUID in your user_account table)
MOCK_USER_SESSION = {
    "user_id": "1c65d3b5-0de1-47a0-82cc-ea1f210c596c"
}

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_memoir(
    payload: MemoirCreateRequest,
    user_session: dict = Depends(lambda: MOCK_USER_SESSION)
):
    """
    Creates a new root memoir container for a subject. 
    This must be executed first to obtain a memoir_id before adding media or memories.
    """
    if not user_session or not user_session.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create a memoir."
        )

    new_memoir = MemoirService.create_memoir(payload, user_session)
    return {
        "success": True,
        "message": "Memoir successfully created.",
        "data": new_memoir
    }