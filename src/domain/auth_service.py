"""
@file auth_service.py
@description Business logic service handling user registration, Supabase Auth synchronization,
credential authentication, and login activity tracking, fully decoupled from direct 
infrastructure and database connection calls.
"""

import logging
from datetime import datetime, timezone
from fastapi import HTTPException, status
from src.integrations import auth_repository
from src.schemas.auth import UserRegisterRequest, UserLoginRequest

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles user authentication workflows, coordinating between external auth 
    credentials and internal application profile records through repository adapters.
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
            response = auth_repository.auth_sign_up(payload.email, payload.password, payload.full_name)
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

        # Explicitly insert the user profile into public.user_account table via repository
        try:
            auth_repository.upsert_user_account(user_id, payload.email, payload.full_name)
        except Exception as db_err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User created in auth, but failed to save profile to user_account: {str(db_err)}"
            )

        session = response.session
        
        # FIXED: Handle email confirmation requirement cleanly
        if not session:
            return {
                "user_id": user_id,
                "email": response.user.email,
                "full_name": payload.full_name,
                "access_token": None,
                "message": "Registration successful. Please check your email to confirm your account before logging in."
            }

        access_token = session.access_token

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
            response = auth_repository.auth_sign_in(payload.email, payload.password)
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

        # Update last_login_at timestamp in user_account table via repository (non-blocking)
        try:
            auth_repository.update_last_login(user_id, datetime.now(timezone.utc).isoformat())
        except Exception as db_err:
            # Non-blocking log using proper logger instead of print
            logger.warning("Failed to update last login timestamp: %s", str(db_err))

        return {
            "user_id": user_id,
            "email": response.user.email,
            "access_token": access_token,
            "message": "Login successful."
        }