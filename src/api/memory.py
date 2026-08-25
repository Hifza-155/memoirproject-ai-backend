"""
@file api/memory.py
@description FastAPI router for owner memory capture, feed retrieval, and pre-publication management.
"""

from fastapi import APIRouter, Depends, status
from src.models.memory import MemoryCreateRequest, MemoryUpdateRequest
from src.domain.memory_service import MemoryService

router = APIRouter(prefix="/api/memories", tags=["Memories"])

# Mock session dependency matching your testing setup
def get_current_user_session():
    return {"user_id": "1c65d3b5-0de1-47a0-82cc-ea1f210c596c"}

@router.post("", status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreateRequest, user_session: dict = Depends(get_current_user_session)):
    """
    Create a new memory entry. Supports combining text, voice recordings, 
    and photographs into a single memory using media asset IDs.
    """
    result = MemoryService.create_memory(payload, user_session)
    return {
        "success": True,
        "message": "Memory successfully created.",
        "data": result
    }

@router.get("", status_code=status.HTTP_200_OK)
def get_memoir_feed(memoir_id: str, user_session: dict = Depends(get_current_user_session)):
    """
    Fetch all memories for the memoir owner dashboard feed. 
    Handles intentional empty states if no memories exist yet.
    """
    feed_result = MemoryService.get_memoir_feed(memoir_id, user_session)
    return {
        "success": True,
        "message": "Memoir feed fetched successfully.",
        "data": feed_result
    }

@router.delete("/{memory_id}", status_code=status.HTTP_200_OK)
def delete_memory(memory_id: str, user_session: dict = Depends(get_current_user_session)):
    """
    Delete a memory entry by ID (allowed before publication only).
    """
    return MemoryService.delete_memory(memory_id, user_session)