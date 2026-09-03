import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.media import MediaAsset
from src.schemas.memoir import Memoir
from src.schemas.transcript import Transcript
from src.schemas.media import TranscriptUpdate

logger = logging.getLogger(__name__)


def get_transcript(db: Session, media_asset_id: uuid.UUID, user_id: uuid.UUID) -> Transcript:
    stmt = (
        select(Transcript)
        .join(MediaAsset, Transcript.media_asset_id == MediaAsset.id)
        .join(Memoir, MediaAsset.memoir_id == Memoir.id)
        .where(
            Transcript.media_asset_id == media_asset_id,
            MediaAsset.deleted_at.is_(None),
            Memoir.owner_user_id == user_id,
            Memoir.deleted_at.is_(None),
        )
    )
    transcript = db.execute(stmt).scalar_one_or_none()
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    return transcript


def _load_owned_transcript(db: Session, transcript_id: uuid.UUID, user_id: uuid.UUID) -> Transcript:
    stmt = (
        select(Transcript)
        .join(MediaAsset, Transcript.media_asset_id == MediaAsset.id)
        .join(Memoir, MediaAsset.memoir_id == Memoir.id)
        .where(
            Transcript.id == transcript_id,
            MediaAsset.deleted_at.is_(None),
            Memoir.owner_user_id == user_id,
            Memoir.deleted_at.is_(None),
        )
    )
    transcript = db.execute(stmt).scalar_one_or_none()
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    return transcript


def update_transcript(db: Session, *, transcript_id: uuid.UUID, user_id: uuid.UUID, data: TranscriptUpdate) -> Transcript:
    transcript = _load_owned_transcript(db, transcript_id, user_id)
    transcript.text = data.text
    transcript.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(transcript)
    logger.info("Transcript edited id=%s", transcript.id)
    return transcript


def retry_transcript(db: Session, *, transcript_id: uuid.UUID, user_id: uuid.UUID) -> Transcript:
    transcript = _load_owned_transcript(db, transcript_id, user_id)
    if transcript.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a failed transcription can be retried.",
        )

    transcript.status = "queued"
    transcript.error_message = None
    db.commit()

    from src.domain.transcription_tasks import transcribe_asset
    try:
        transcribe_asset.delay(str(transcript.media_asset_id))
    except Exception as exc:
        logger.error("Failed to enqueue transcription retry transcript_id=%s: %s", transcript.id, exc)

    logger.info("Transcript retry queued id=%s", transcript.id)
    return transcript