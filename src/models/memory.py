"""
@file memory.py
@description SQLAlchemy ORM models representing individual memory stories 
and their many-to-many associations with media assets via junction tables.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Memory(Base):
    """
    Represents an individual memory entry. 
    Design rule: ONE memory encapsulates text, audio, and/or photos unified together.
    """
    __tablename__ = "memory"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'saved')", name="ck_memory_status"),
        Index("ix_memory_memoir_created", "memoir_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memoir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memoir.id", ondelete="CASCADE"), nullable=False
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    media_links: Mapped[list["MemoryMedia"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", order_by="MemoryMedia.position"
    )


class MemoryMedia(Base):
    """Association object: which asset belongs to which memory, with its caption."""

    __tablename__ = "memory_media"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memory.id", ondelete="CASCADE"), primary_key=True
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_asset.id", ondelete="CASCADE"),
        primary_key=True, index=True,
    )
    position: Mapped[int] = mapped_column(nullable=False, server_default="0")
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory"] = relationship(back_populates="media_links")