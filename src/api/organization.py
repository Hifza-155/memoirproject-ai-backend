from src.core.config import settings 
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from src.core.auth import get_current_user
from src.integrations.share_repository import ShareRepository
from src.integrations.supabase_client import supabase_admin
from src.integrations.organization_repository import fetch_archive_raw_data
from src.domain.organization_service import (
    perform_background_organization, 
    get_archive_context_for_chat,
    get_ai_client 
)
from src.schemas.organization import (
    OrganizeResponseEnvelope,
    ChapterUpdateRequest,
    ChatRequest, 
    ChatResponse
)
from src.integrations.organization_repository import (
    update_chapter_in_db,
    update_ai_woven_text_in_db
)

organization_router = APIRouter(prefix="/api/memoirs", tags=["AI Organization & Editing"])
# Global OpenAI client removed to prevent duplicate initialization

@organization_router.post(
    "/{memoir_id}/organize",
    response_model=OrganizeResponseEnvelope,
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_ai_organization(
    memoir_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Triggers automated AI chapter clustering and timeline generation in the background."""
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant or participant.get("role") not in ["owner", "co_owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and co-owners can trigger AI organization."
        )

    memoir = await ShareRepository.get_memoir_by_id(memoir_id)
    if not memoir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memoir not found."
        )

    if memoir.get("status") == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot organize a published, immutable memoir."
        )

    background_tasks.add_task(perform_background_organization, memoir_id)

    return OrganizeResponseEnvelope(
        success=True,
        message="Organization started in the background.",
        job_status="processing"
    )

@organization_router.post(
    "/{memoir_id}/publish",
    status_code=status.HTTP_200_OK
)
async def publish_memoir(
    memoir_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Permanently locks the memoir and transitions it to the published read-only state."""
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant or participant.get("role") not in ["owner", "co_owner"]:
        raise HTTPException(status_code=403, detail="Only owners can publish the memoir.")

    # Lock the memoir in the database
    res = supabase_admin.table("memoir") \
        .update({"status": "published"}) \
        .eq("id", memoir_id) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Memoir not found.")

    return {
        "success": True,
        "message": "Memoir successfully published and locked."
    }

@organization_router.put(
    "/{memoir_id}/chapters/{chapter_id}",
    status_code=status.HTTP_200_OK
)
async def manual_update_chapter(
    memoir_id: str,
    chapter_id: str,
    payload: ChapterUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Allows the memoir owner or co-owner to manually rename or summarize a chapter.
    Automatically locks the chapter by setting edited_by_owner to True.
    """
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant or participant.get("role") not in ["owner", "co_owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and co-owners can edit chapters."
        )

    if not payload.title and not payload.summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide title or summary to update."
        )

    updated_chapter = update_chapter_in_db(
        chapter_id=chapter_id,
        memoir_id=memoir_id,
        title=payload.title,
        summary=payload.summary
    )
    
    return {
        "success": True,
        "message": "Chapter manually edited and locked against automated AI overwrites.",
        "data": updated_chapter
    }


@organization_router.put(
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


@organization_router.post(
    "/{memoir_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK
)
async def chat_with_archive(
    memoir_id: str,
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Allows the user to converse with an AI co-author that has full contextual 
    awareness and conversational history support.
    """
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this memoir."
        )

    archive_context = get_archive_context_for_chat(memoir_id)

    system_prompt = (
        "You are an empathetic, insightful archival co-author assisting a user with their family memoir. "
        "You have direct access to the structured table of contents of their archive below. "
        "Use this context to answer their questions, suggest chapter improvements, or help them brainstorm ideas. "
        "Keep your tone warm, encouraging, and focused on storytelling.\n\n"
        f"{archive_context}"
    )

    try:
        # Initialize client lazily here
        client = get_ai_client()
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if payload.history:
            # FIX: Secondary safeguard - strictly slice the last 20 messages
            safe_history = payload.history[-20:]
            for hist_item in safe_history:
                # FIX: Double-check that we NEVER append a rogue system prompt from the client
                if hist_item.role in ["user", "assistant"]:
                    messages.append({"role": hist_item.role, "content": hist_item.content})
                
        messages.append({"role": "user", "content": payload.message})

        response = client.chat.completions.create(
            model=settings.gemini_model,
            messages=messages
        )

        reply_text = response.choices[0].message.content

        return ChatResponse(
            success=True,
            reply=reply_text
        )

    except RuntimeError as re:
        # Fails fast cleanly if API key is missing
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(re)
        )
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "ResourceExhausted" in error_str or "Too Many Requests" in error_str:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You are sending messages too quickly or have exceeded your quota. Please wait 30 seconds."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI chat service failed: {error_str}"
        )
        

@organization_router.get("/{memoir_id}/chapters", status_code=status.HTTP_200_OK)
async def get_memoir_chapters(
    memoir_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetches all structured chapters for a specific memoir."""
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this memoir."
        )

    try:
        raw_data = fetch_archive_raw_data(memoir_id)
        chapters = raw_data.get("chapters", [])
    except Exception:
        chapters = []

    return {
        "success": True,
        "message": "Chapters fetched successfully.",
        "data": chapters
    }