"""
@file integrations/database.py
@description Centralized database engine, session factory, and unified 
SQLAlchemy 2.0 DeclarativeBase registry.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate DATABASE_URL (Fail Fast)
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from environment variables.")

# Ensures secure database connections in production environments
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    """
    Unified SQLAlchemy 2.0 DeclarativeBase registry. 
    Acts as the single source of truth for all ORM models and database migrations.
    """
    pass

def get_db():
    """
    FastAPI dependency yielding a transactional database session scope.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()