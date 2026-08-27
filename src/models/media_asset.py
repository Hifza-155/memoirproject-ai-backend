"""
@file media_asset.py
@description SQLAlchemy ORM model representing file metadata and storage pointers
for photos and audio assets linked to memoirs.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Integer, BigInteger, DateTime, ForeignKey, CheckConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class MediaAsset(Base):
    """
    Represents metadata pointers for files stored in external object storage.
    Note: Binary file bytes never touch Postgres; this table stores references,
    sizes, validation statuses, and security constraints.
    """
    __tablename__ = "media_asset"
    __table_args__ = (
        CheckConstraint("media_type IN ('audio', 'image')", name="ck_media_asset_type"),
        CheckConstraint("status IN ('pending', 'ready', 'failed')", name="ck_media_asset_status"),
        CheckConstraint(
            "storage_tier IN ('hot', 'cold', 'archived')", name="ck_media_asset_tier"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memoir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memoir.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    uploader_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id"), nullable=False
    )
    storage_bucket: Mapped[str] = mapped_column(String(63), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending", index=True)
    storage_tier: Mapped[str] = mapped_column(String(20), nullable=False, server_default="hot")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)