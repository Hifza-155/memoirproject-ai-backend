"""
@file routers/comments_router.py
@description FastAPI router endpoints for comment operations.
"""

from fastapi import APIRouter, Depends, Query, status, Header
from typing import List, Optional
from src.schemas.comments import CommentCreate, CommentResponse
from src.domain.comments_service import CommentsService
from src.integrations.supabase_client import supabase_admin
from fastapi import HTTPException, status
router = APIRouter(prefix="/api/comments", tags=["Comments"])

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Helper to extract user_id from the incoming Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase_admin.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid session or token expired.")
        return user_res.user.id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@router.get("/", response_model=List[CommentResponse])
async def list_comments(memory_id: str = Query(..., description="The UUID of the memory item")):
    """Fetch all comments linked to a specific memory asset."""
    return await CommentsService.get_memory_comments(memory_id)

@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def post_comment(
    payload: CommentCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Post a new comment to a memory item with automatic participant resolution."""
    return await CommentsService.create_new_comment(payload.dict(), user_id)