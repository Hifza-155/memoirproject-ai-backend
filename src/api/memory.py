"""
@file api/memory.py
@description FastAPI router for owner memory capture, feed retrieval, and pre-publication management.
"""

from fastapi import APIRouter, Depends, status
from src.schemas.memory import MemoryCreateRequest
from src.domain.memory_service import MemoryService
from src.core.auth import get_current_user  # Production JWT verification dependency

router = APIRouter(prefix="/api/memories", tags=["Memories"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreateRequest, 
    current_user_id: str = Depends(get_current_user)
):
    """
    Create a new memory entry. Supports combining text, voice recordings, 
    and photographs into a single memory using media asset IDs.
    """
    user_session = {"user_id": current_user_id}
    result = MemoryService.create_memory(payload, user_session)
    return {
        "success": True,
        "message": "Memory successfully created.",
        "data": result
    }

@router.get("/feed/{memoir_id}", status_code=status.HTTP_200_OK)
def get_memoir_feed_route(
    memoir_id: str, 
    limit: int = 20, 
    offset: int = 0, 
    user_session: dict = Depends(get_current_user)
):
    """
    API endpoint to fetch a paginated memory feed for a specific memoir container.
    """
    user_id = user_session.get("user_id")
    feed_data = MemoryService.get_memoir_feed(memoir_id, user_id, limit=limit, offset=offset)
    return {"success": True, "data": feed_data}

@router.delete("/memoirs/{memoir_id}/memories/{memory_id}", status_code=status.HTTP_200_OK)
def delete_memory_route(memoir_id: str, memory_id: str, user_session: dict = Depends(get_current_user)):
    """
    API endpoint to delete a memory securely within a specific memoir container, 
    returning a consistent response envelope.
    """
    user_id = user_session.get("user_id")
    result = MemoryService.delete_memory(memoir_id, memory_id, user_id)
    
    return {"success": True, "data": result}