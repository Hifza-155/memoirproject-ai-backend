"""
@file domain/auth_service.py
@description Business logic service handling user registration, Supabase Auth synchronization,
credential authentication, and login activity tracking.
"""

from datetime import datetime, timezone
from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase
from src.schemas.auth import UserRegisterRequest, UserLoginRequest


class AuthService:
    """
    Handles user authentication workflows, coordinating between external Supabase Auth 
    credentials and internal application profile records in PostgreSQL.
    """

    @staticmethod
    def register_user(payload: UserRegisterRequest) -> dict:
        """
        Registers a new user via Supabase Auth, provisions their profile metadata, 
        and explicitly syncs an entry into the public `user_account` database table.

        Args:
            payload (UserRegisterRequest): The registration request payload containing email, password, and full name.

        Returns:
            dict: A dictionary containing the new user ID, email, full name, access token, and status message.

        Raises:
            HTTPException (500): If Supabase auth registration fails or database synchronization errors occur.
            HTTPException (400): If user creation returns an empty response (e.g., email already in use).
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

    @staticmethod
    def login_user(payload: UserLoginRequest) -> dict:
        """
        Authenticates an existing user via Supabase Auth password verification, 
        updates their last login timestamp in the database, and returns an active access token.

        Args:
            payload (UserLoginRequest): The login request payload containing email and password.

        Returns:
            dict: A dictionary containing the user ID, email, access token, and success message.

        Raises:
            HTTPException (401): If credentials are invalid, authentication fails, or session tokens are missing.
        """
        try:
            response = supabase.auth.sign_in_with_password({
                "email": payload.email,
                "password": payload.password
            })
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid email or password: {str(e)}"
            )

        if not response or not response.session or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        user_id = response.user.id
        access_token = response.session.access_token

        # Update last_login_at timestamp in user_account table (non-blocking)
        try:
            supabase.table("user_account").update({
                "last_login_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", user_id).execute()
        except Exception as db_err:
            # Non-blocking log, allows login to proceed even if timestamp update fails
            print(f"Failed to update last login timestamp: {str(db_err)}")

        return {
            "user_id": user_id,
            "email": response.user.email,
            "access_token": access_token,
            "message": "Login successful."
        }