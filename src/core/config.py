"""
@file core/config.py
@description Centralized application configuration and environment variable manager 
using Pydantic BaseSettings with explicit field aliases, type validation, and fallback defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration schema defining and validating all environment variables, 
    connection strings, security keys, and application limits required by the backend.
    """

    # --- Supabase Identity & Auth (Feature 1) ---
    supabase_url: str
    supabase_jwks_url: str = Field(..., validation_alias="SUPABASE_JWKS_URL")
    supabase_jwt_aud: str = "authenticated"

    # --- Database Configuration ---
    database_url: str = Field(..., validation_alias="DATABASE_URL")

    # --- Web & CORS Configuration ---
    cors_origins: str = "http://localhost:3000"

    # --- Object Storage & Media Limits (Feature 2) ---
    # Automatically maps your existing .env keys to clean internal attribute names
    supabase_secret_key: str = Field(..., validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_media_bucket: str = Field("memoir-media", validation_alias="SUPABASE_BUCKET_NAME")

    media_max_bytes: int = 26_214_400              # Maximum upload limit: 25 MB
    media_signed_url_ttl: int = 3600             # Playback link lifetime in seconds (1 hour)

    # --- Application State Constants ---
    storage_tier_hot: str = "hot"
    transcription_status_skipped: str = "skipped"
    transcription_status_pending: str = "pending"

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=False, 
        extra="ignore"
    )


# Instantiate a global settings singleton for application-wide import
settings = Settings()

# Module-level convenience variables for clean, direct imports across services
STORAGE_BUCKET_NAME = settings.supabase_media_bucket
STORAGE_TIER_HOT = settings.storage_tier_hot
TRANSCRIPTION_STATUS_SKIPPED = settings.transcription_status_skipped
TRANSCRIPTION_STATUS_PENDING = settings.transcription_status_pending