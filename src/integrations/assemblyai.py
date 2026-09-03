"""AssemblyAI speech-to-text adapter.

Thin wrapper only — no polling loop, no business logic. AssemblyAI fetches
the audio itself, by URL; we never handle the bytes here.
"""
import logging

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.assemblyai.com/v2"
_TIMEOUT = 30.0


class TranscriptionError(Exception):
    """Raised when AssemblyAI can't be reached or returns something unusable."""


def _headers() -> dict:
    return {"authorization": settings.assemblyai_api_key}


def submit_transcription(audio_url: str) -> str:
    """Submit an audio URL for transcription. Returns AssemblyAI's job id."""
    try:
        response = httpx.post(
            f"{_BASE_URL}/transcript",
            json={"audio_url": audio_url},
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("AssemblyAI submit failed: %s", exc)
        raise TranscriptionError("Could not submit audio for transcription.") from exc

    job_id = response.json().get("id")
    if not job_id:
        raise TranscriptionError("AssemblyAI did not return a job id.")
    return job_id


def get_transcription(job_id: str) -> dict:
    """Poll one job's current state.

    Returns {"status", "text", "confidence", "language", "error"}. AssemblyAI
    reports "queued", "processing", "completed", or "error" — passed through
    unchanged; the caller maps "error" to our own 'failed' status.
    """
    try:
        response = httpx.get(
            f"{_BASE_URL}/transcript/{job_id}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("AssemblyAI poll failed job_id=%s: %s", job_id, exc)
        raise TranscriptionError("Could not check transcription status.") from exc

    data = response.json()
    return {
        "status": data.get("status"),
        "text": data.get("text"),
        "confidence": data.get("confidence"),
        "language": data.get("language_code"),
        "error": data.get("error"),
    }