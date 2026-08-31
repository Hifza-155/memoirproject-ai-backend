"""
@file src/core/config.py
@description Centralized application configuration and environment variable validation
using Pydantic BaseSettings.
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    # FIXED: Added cors_origins so main.py can dynamically read allowed origins from the environment
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        validation_alias="CORS_ORIGINS"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """
        Parses comma-separated CORS origins string from environment variables into a list,
        or accepts an existing list.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()