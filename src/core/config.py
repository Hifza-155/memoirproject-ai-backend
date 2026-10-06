"""
@file src/core/config.py
@description Centralized application configuration and environment variable validation
using Pydantic BaseSettings.
"""

from typing import Annotated, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded securely from environment variables.
    """
    supabase_url: str = Field(..., validation_alias="SUPABASE_URL")
    supabase_anon_key: str = Field(..., validation_alias="SUPABASE_ANON_KEY")
    supabase_secret_key: str = Field(..., validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    supabase_jwks_url: str = Field(..., validation_alias="SUPABASE_JWKS_URL")
    supabase_media_bucket: str = Field("media", validation_alias="SUPABASE_BUCKET_NAME")
    
    media_max_bytes: int = Field(52_428_576, validation_alias="MEDIA_MAX_BYTES")
    media_signed_url_ttl: int = Field(300, validation_alias="MEDIA_SIGNED_URL_TTL")
    
    # FIXED: Added cors_origins so main.py can dynamically read allowed origins from the environment.
    # NoDecode is required: pydantic-settings would otherwise JSON-decode this env var before
    # assemble_cors_origins() runs, which makes a comma-separated CORS_ORIGINS crash at import.
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        validation_alias="CORS_ORIGINS"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """
        Accepts a comma-separated string, a JSON array string, or an existing list,
        and normalizes it into a clean list of origins.
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return ["http://localhost:3000"]
            if raw.startswith("["):
                try:
                    import json
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except ValueError:
                    pass  # fall through to comma-separated handling
            return [i.strip() for i in raw.split(",") if i.strip()]
        return ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    share_link_base_url: str = Field(
    default="http://localhost:3000/contribute", 
    validation_alias="SHARE_LINK_BASE_URL"
    )    
    
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        validation_alias="GEMINI_MODEL"
    )
settings = Settings()

# Storage tiers for media asset lifecycle management
STORAGE_TIER_HOT = "hot"
STORAGE_TIER_COLD = "cold"

# Transcription status states for audio/video assets
TRANSCRIPTION_STATUS_PENDING = "pending"
TRANSCRIPTION_STATUS_COMPLETED = "completed"
TRANSCRIPTION_STATUS_FAILED = "failed"

SUPABASE_JWKS_URL = settings.supabase_jwks_url
