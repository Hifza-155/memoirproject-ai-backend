"""
@file api/memory.py
@description FastAPI router for owner memory capture, feed retrieval, and pre-publication management.
"""


from fastapi import Request, status, HTTPException, Depends,APIRouter
from typing import Optional
from src.schemas.memory import MemoryCreateRequest
from src.domain.memory_service import MemoryService
from src.core.auth import get_current_user ,get_current_user_optional  # Production JWT verification dependency
from src.integrations.organization_repository import update_ai_woven_text_in_db
from src.integrations.share_repository import ShareRepository
router = APIRouter(prefix="/api/memories", tags=["Memories"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreateRequest, 
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional) # Use your optional auth dependency here
):
    """
    Create a new memory entry. Supports authenticated owners and 
    verified contributors via secure share-link cookies.
    """
    user_id = None
    author_name = None
    date_source = "owner"

    if current_user:
        # 1. Authenticated Owner flow
        user_id = current_user.get("user_id") or current_user.get("id") or current_user.get("sub")
        author_name = current_user.get("full_name") or current_user.get("name") or "Author"
        date_source = "owner"
    else:
        # 2. Verified Contributor flow (reads the HttpOnly cookie set during /verify)
        contributor_cookie_key = f"contributor_name_{payload.memoir_id}"
        contributor_name = request.cookies.get(contributor_cookie_key)
        
        if contributor_name:
            date_source = "contributor"
            author_name = contributor_name
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Authentication required to create a memory."
            )

    # Pass session info including the dynamic author name into your service layer
    user_session = {
        "user_id": user_id,
        "author_name": author_name,
        "date_source": date_source
    }
    
    result = MemoryService.create_memory(payload, user_session)
    return {
        "success": True,
        "message": "Memory successfully created.",
        "data": result
    }    
    

@router.get("/feed/{memoir_id}", status_code=status.HTTP_200_OK)
async def get_memoir_feed_route(
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
async def delete_memory_route(memoir_id: str, memory_id: str, user_session: dict = Depends(get_current_user)):
    """
    API endpoint to delete a memory securely within a specific memoir container, 
    returning a consistent response envelope.
    """
    user_id = user_session.get("user_id")
    result = MemoryService.delete_memory(memoir_id, memory_id, user_id)
    
    return {"success": True, "data": result}

@router.put(
    "/{memoir_id}/memories/{memory_id}/woven-text",
    status_code=status.HTTP_200_OK
)
async def update_woven_text(
    memoir_id: str,
    memory_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """Allows owners and co-owners to edit the AI-woven narrative text of a specific memory."""
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant or participant.get("role") not in ["owner", "co_owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and co-owners can edit chapter narrative text."
        )

    updated = update_ai_woven_text_in_db(memory_id, memoir_id, payload.get("ai_woven_text"))
    
    return {
        "success": True,
        "message": "Narrative text successfully updated.",
        "data": updated
    }