"""
@file models/auth.py
@description Pydantic models for user authentication and registration requests.
"""

from pydantic import BaseModel, EmailStr, Field

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long.")
    full_name: str = Field(..., min_length=1, description="User's full name for profile setup.")

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str