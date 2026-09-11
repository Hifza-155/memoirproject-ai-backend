from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from src.core.auth import get_current_user
from src.integrations.share_repository import ShareRepository
from src.domain.organization_service import perform_background_organization
from src.schemas.organization import OrganizeResponseEnvelope

organization_router = APIRouter(prefix="/api/memoirs", tags=["AI Organization"])

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
    user_id = str(current_user.get("user_id") or current_user.get("id") or current_user.get("sub"))

    participant = await ShareRepository.get_participant(memoir_id, user_id)
    if not participant or participant.get("role") != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the memoir owner can trigger AI organization."
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