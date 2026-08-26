"""
@file domain/auth_service.py
@description Business logic for handling user registration and authentication via Supabase Auth.
"""

from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase
from src.models.auth import UserRegisterRequest

class AuthService:

    @staticmethod
    def register_user(payload: UserRegisterRequest) -> dict:
        """
        Registers a new user via Supabase Auth and explicitly inserts them into user_account.
        """
        try:
            response = supabase.auth.sign_up({
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "full_name": payload.full_name
                    }
                }
            })
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Supabase auth registration failed: {str(e)}"
            )

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not register user. Email may already be in use."
            )

        user_id = response.user.id

        # Explicitly insert the user profile into public.user_account table
        try:
            supabase.table("user_account").upsert({
                "id": user_id,
                "email": payload.email,
                "full_name": payload.full_name
            }, on_conflict="id").execute()
        except Exception as db_err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User created in auth, but failed to save profile to user_account: {str(db_err)}"
            )

        session = response.session
        access_token = session.access_token if session else None

        return {
            "user_id": user_id,
            "email": response.user.email,
            "full_name": payload.full_name,
            "access_token": access_token,
            "message": "User registered and profile provisioned successfully."
        }