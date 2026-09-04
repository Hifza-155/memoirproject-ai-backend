import logging
import time
import uuid

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from src.core.celery_app import celery_app
from src.db.session import SessionLocal
from src.schemas.media import MediaAsset
from src.schemas.transcript import Transcript
from src.integrations import assemblyai
from src.integrations import storage_adapter as storage_service

logger = logging.getLogger(__name__)

_PLAYBACK_URL_TTL = 7200
_POLL_INTERVAL = 5
_MAX_POLL_SECONDS = 480


@celery_app.task(name="transcription.transcribe_asset", bind=True)
def transcribe_asset(self, media_asset_id: str) -> None:
    db = SessionLocal()
    try:
        asset = db.get(MediaAsset, uuid.UUID(media_asset_id))
        if asset is None or asset.media_type != "audio" or asset.status != "ready":
            logger.info("Skipping transcription for asset_id=%s (missing or not ready audio)", media_asset_id)
            return

        transcript = db.execute(
            select(Transcript).where(Transcript.media_asset_id == asset.id)
        ).scalar_one_or_none()

        if transcript is not None and transcript.status == "completed":
            logger.info("Transcript already completed for asset_id=%s, skipping", asset.id)
            return

        if transcript is None:
            transcript = Transcript(media_asset_id=asset.id)
            db.add(transcript)

        transcript.status = "processing"
        transcript.attempt_count += 1
        transcript.error_message = None
        db.commit()

        try:
            playback_url = storage_service.create_playback_url(
                asset.storage_key, ttl_seconds=_PLAYBACK_URL_TTL
            )
            if not playback_url:
                raise assemblyai.TranscriptionError("Could not generate a playback URL.")

            job_id = assemblyai.submit_transcription(playback_url)
            transcript.provider_job_id = job_id
            db.commit()

            result = _poll_until_done(job_id)

            if result["status"] == "completed":
                transcript.raw_text = result["text"]
                transcript.text = result["text"]
                transcript.confidence = result["confidence"]
                transcript.language = result["language"]
                transcript.status = "completed"
                transcript.error_message = None
            else:
                transcript.status = "failed"
                transcript.error_message = result.get("error") or "We couldn't transcribe this recording. Please try again."

            db.commit()
            logger.info("Transcription %s for asset_id=%s", transcript.status, asset.id)

        except SoftTimeLimitExceeded:
            transcript.status = "failed"
            transcript.error_message = "Transcription took too long and was stopped."
            db.commit()
            raise
        except Exception as exc:
            logger.error("Transcription failed asset_id=%s: %s", asset.id, exc)
            transcript.status = "failed"
            transcript.error_message = "We couldn't transcribe this recording. Please try again."
            db.commit()
    finally:
        db.close()


def _poll_until_done(job_id: str) -> dict:
    waited = 0
    while waited < _MAX_POLL_SECONDS:
        result = assemblyai.get_transcription(job_id)
        if result["status"] in ("completed", "error"):
            return result
        time.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL

    return {"status": "error", "error": "Transcription timed out waiting for a result."}