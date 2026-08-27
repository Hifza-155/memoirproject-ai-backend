"""
@file user.py
@description SQLAlchemy ORM model representing user accounts, profiles, 
authentication synchronization pointers, and onboarding subject preferences.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class User(Base):
    """
    Represents an application user profile synchronized with external auth providers,
    holding user metadata, activity tracking, and onboarding context.
    """
    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider_uid: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subject_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_relationship: Mapped[str | None] = mapped_column(String(255), nullable=True)