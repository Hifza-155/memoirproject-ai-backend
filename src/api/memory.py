"""
@file api/memory.py
@description FastAPI router for owner memory capture, feed retrieval, and pre-publication management.
"""

from fastapi import APIRouter, Depends, status
from src.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest
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

@router.get("", status_code=status.HTTP_200_OK)
def get_memoir_feed(
    memoir_id: str, 
    current_user_id: str = Depends(get_current_user)
):
    """
    Fetch all memories for the memoir owner dashboard feed. 
    Handles intentional empty states if no memories exist yet.
    """
    user_session = {"user_id": current_user_id}
    feed_result = MemoryService.get_memoir_feed(memoir_id, user_session)
    return {
        "success": True,
        "message": "Memoir feed fetched successfully.",
        "data": feed_result
    }

@router.delete("/{memory_id}", status_code=status.HTTP_200_OK)
def delete_memory(
    memory_id: str, 
    current_user_id: str = Depends(get_current_user)
):
    """
    Delete a memory entry by ID (allowed before publication only).
    """
    user_session = {"user_id": current_user_id}
    return MemoryService.delete_memory(memory_id, user_session)