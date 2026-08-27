"""
@file base.py
@description Declares the shared SQLAlchemy DeclarativeBase registry used 
as the parent class for all ORM database models across the application.
"""
from sqlalchemy.orm import DeclarativeBase
"""
Base class for all SQLAlchemy declarative models. 
Maintains metadata and registry mappings for database table generation and migrations.
"""

class Base(DeclarativeBase):
    pass