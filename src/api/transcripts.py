"""
@file transcript.py
@description FastAPI router exposing endpoints to request background transcriptions.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from src.schemas.transcript import TranscriptionRequest
from src.domain.transcription_service import transcribe_and_store_audio

router = APIRouter(prefix="/api/transcript", tags=["Transcript"])

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def request_transcription(
    payload: TranscriptionRequest,
    background_tasks: BackgroundTasks
):
    """
    Triggers AssemblyAI speech-to-text conversion in the background for a given media asset.
    """
    try:
        background_tasks.add_task(
            transcribe_and_store_audio,
            media_asset_id=payload.media_asset_id,
            memoir_id=payload.memoir_id,
            storage_key=payload.storage_key
        )
        return {"status": "processing", "message": "Transcription task initiated in background."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue transcription task: {str(e)}"
        )