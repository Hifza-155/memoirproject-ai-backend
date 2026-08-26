"""
@file api/routers/auth.py
@description FastAPI router for user registration and authentication endpoints.
"""

from fastapi import APIRouter, status
from src.models.auth import UserRegisterRequest
from src.domain.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def register_user_endpoint(payload: UserRegisterRequest):
    """
    Registers a new user account, triggers automatic database account provisioning,
    and returns the session access token for immediate frontend use.
    """
    result = AuthService.register_user(payload)
    return {
        "success": True,
        "message": result["message"],
        "data": {
            "user_id": result["user_id"],
            "email": result["email"],
            "full_name": result["full_name"],
            "access_token": result["access_token"]
        }
    }