import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.domain.authorization import CurrentUser, get_current_user
from src.db.session import get_db
# Adjust this schema import path depending on where your Transcript schemas are defined
from src.schemas.media import TranscriptRead, TranscriptUpdate 
from src.domain import transcription_service

router = APIRouter(tags=["transcripts"])


@router.get("/media/{media_asset_id}/transcript", response_model=TranscriptRead)
def get_transcript(
    media_asset_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transcription_service.get_transcript(db, media_asset_id, current.user.id)


@router.patch("/transcripts/{transcript_id}", response_model=TranscriptRead)
def update_transcript(
    transcript_id: uuid.UUID,
    payload: TranscriptUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transcription_service.update_transcript(
        db, transcript_id=transcript_id, user_id=current.user.id, data=payload
    )


@router.post(
    "/transcripts/{transcript_id}/retry",
    response_model=TranscriptRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_transcript(
    transcript_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transcription_service.retry_transcript(
        db, transcript_id=transcript_id, user_id=current.user.id
    )