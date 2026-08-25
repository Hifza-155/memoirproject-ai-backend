"""
@file models/memoir.py
@description Pydantic validation models for creating a new memoir.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import date

class MemoirCreateRequest(BaseModel):
    subject_name: str = Field(..., description="Name of the subject of the memoir")
    subject_born_on: Optional[date] = Field(None, description="Birth date of the subject (YYYY-MM-DD)")
    subject_died_on: Optional[date] = Field(None, description="Death date of the subject (YYYY-MM-DD)")
    subject_is_living: bool = Field(False, description="Whether the subject is currently alive")
    description: Optional[str] = Field(None, description="Optional description or blurb for the memoir")
    visibility: Optional[str] = Field("invited_only", description="Visibility setting: 'invited_only', 'public', or 'link_with_password'")
    comment_policy: Optional[str] = Field("invited_only", description="Comment policy setting")

    @model_validator(mode='after')
    def validate_memoir_constraints(self) -> 'MemoirCreateRequest':
        # Mirroring SQL constraint: memoir_dates_ordered
        if self.subject_born_on and self.subject_died_on:
            if self.subject_born_on > self.subject_died_on:
                raise ValueError("Subject birth date cannot be after their death date.")
        
        # Mirroring SQL constraint: memoir_living_has_no_death_date
        if self.subject_is_living and self.subject_died_on is not None:
            raise ValueError("A living subject cannot have a death date.")
            
        return self