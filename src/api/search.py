"""
@file api/search.py
@description API router handling full-text search requests.
"""

from fastapi import APIRouter, Depends, Query, status
from src.domain.search_service import SearchService
from src.core.auth import get_current_user  # Adjust import based on your auth dependency

router = APIRouter(prefix="/api/search", tags=["Search"])

@router.get("/")
def search_memories(
    memoir_id: str = Query(..., description="Target memoir container UUID"),
    q: str = Query(..., min_length=1, description="Search keyword or phrase"),
    current_user_id: str = Depends(get_current_user)
):
    """
    Performs full-text search across written entries, transcripts, and captions.
    """
    results = SearchService.search_memoir(memoir_id, q, current_user_id)
    return {
        "success": True,
        "query": q,
        "count": len(results),
        "data": results
    }