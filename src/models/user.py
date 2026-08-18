# 1. We added CheckConstraint and Text here
from sqlalchemy import Column, String, DateTime, CheckConstraint, Text
from sqlalchemy.sql import func
from database import Base

from sqlalchemy.dialects.postgresql import CITEXT, UUID
import uuid

class User(Base):
    __tablename__ = "user_account"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    email = Column(CITEXT, unique=True, nullable=False)
    
    full_name = Column(Text, nullable=False)
    
    auth_provider_uid = Column(Text, unique=True, nullable=True)
        
    # Timestamps
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Ensures full_name isn't just blank spaces, perfectly matching the SQL constraint
    __table_args__ = (
        CheckConstraint("btrim(full_name) <> ''", name="user_account_name_not_blank"),
    )