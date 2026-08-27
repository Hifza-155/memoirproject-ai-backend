"""
@file domain/memoir_service.py
@description Business logic and orchestration service for creating memoir containers, 
normalizing subject dates, and automatically registering the creator as the owner participant.
"""

from fastapi import HTTPException, status
from src.integrations.supabase_client import supabase_admin
from src.schemas.memoir import MemoirCreateRequest


class MemoirService:
    """
    Handles business logic for memoir creation, account profile resolution,
    and automatic participant role assignments.
    """

    @staticmethod
    def create_memoir(payload: MemoirCreateRequest, user_session: dict) -> dict:
        """
        Validates user session authentication, fetches creator profile details, 
        inserts a new memoir container record, and automatically registers the creator 
        as an authorized participant with the 'owner' role.

        Args:
            payload (MemoirCreateRequest): The validated memoir creation request data.
            user_session (dict): The active user session dictionary containing the user ID.

        Returns:
            dict: The newly created root memoir database record.

        Raises:
            HTTPException (401): If the user session is missing a valid user ID.
            HTTPException (500): If database insertion or participant registration fails.
        """
        user_id = user_session.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session is missing user ID."
            )

        # 1. Fetch user account details using supabase_admin
        try:
            user_res = supabase_admin.table("user_account").select("full_name, email").eq("id", user_id).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch user account details: {str(e)}"
            )

        user_record = user_res.data[0] if user_res and user_res.data else {}
        display_name = user_record.get("full_name") or "Memoir Owner"
        user_email = user_record.get("email")

        # 2. Prepare root memoir payload
        memoir_data = {
            "subject_name": payload.subject_name,
            "subject_born_on": str(payload.subject_born_on) if payload.subject_born_on else None,
            "subject_died_on": str(payload.subject_died_on) if payload.subject_died_on else None,
            "subject_is_living": payload.subject_is_living,
            "description": payload.description,
            "visibility": payload.visibility,
            "comment_policy": payload.comment_policy,
            "created_by_user_id": user_id,
            "status": "draft"
        }

        try:
            # 3. Insert root memoir using supabase_admin (bypasses RLS for server-side orchestration)
            db_response = supabase_admin.table("memoir").insert(memoir_data).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while creating memoir: {str(e)}"
            )

        if not db_response or not db_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create memoir record in database."
            )

        created_memoir = db_response.data[0]
        memoir_id = created_memoir["id"]

        # 4. Automatically register the creator as a memoir participant with 'owner' role
        participant_data = {
            "memoir_id": memoir_id,
            "user_id": user_id,
            "role": "owner",
            "display_name": display_name,
            "email": user_email,
            "relationship": "other"  # Default fallback to satisfy enum/defaults
        }

        try:
            supabase_admin.table("memoir_participant").insert(participant_data).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to automatically register memoir participant: {str(e)}"
            )

        return created_memoir