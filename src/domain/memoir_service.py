"""
@file memoir_service.py

@description Business logic and orchestration service for creating memoir containers,
normalizing subject dates, automatically registering the creator as the owner
participant, and fetching the current user's memoir.
"""

from fastapi import HTTPException, status

from src.integrations import memoir_repository
from src.schemas.memoir import MemoirCreateRequest


class MemoirService:
    """
    Handles business logic for memoir creation, account profile resolution,
    participant role assignments, and memoir retrieval.
    """

    @staticmethod
    def create_memoir(payload: MemoirCreateRequest, user_session: dict) -> dict:
        """
        Creates a new root memoir and automatically registers the creator
        as the owner participant.
        """

        user_id = user_session.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session is missing user ID."
            )

        # 1. Fetch user account details using repository
        try:
            user_res = memoir_repository.fetch_user_account(user_id)
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
            "subject_born_on": (
                str(payload.subject_born_on)
                if payload.subject_born_on
                else None
            ),
            "subject_died_on": (
                str(payload.subject_died_on)
                if payload.subject_died_on
                else None
            ),
            "subject_is_living": payload.subject_is_living,
            "description": payload.description,
            "visibility": payload.visibility,
            "comment_policy": payload.comment_policy,
            "created_by_user_id": user_id,
            "status": "draft"
        }

        try:
            db_response = memoir_repository.insert_memoir(memoir_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while creating memoir: {str(e)}"
            )

        created_memoir = db_response.data[0]
        memoir_id = created_memoir["id"]

        # 3. Register creator as memoir owner
        participant_data = {
            "memoir_id": memoir_id,
            "user_id": user_id,
            "role": "owner",
            "display_name": display_name,
            "email": user_email,
            "relationship": payload.relationship
        }

        try:
            memoir_repository.insert_memoir_participant(participant_data)
        except Exception as e:
            # Compensation rollback: delete orphan memoir
            # if participant insertion fails.
            try:
                memoir_repository.delete_memoir_record(memoir_id)
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Failed to register memoir owner. "
                    f"Operation rolled back: {str(e)}"
                )
            )

        return created_memoir

    @staticmethod
    def get_memoir_by_user_id(user_id: str) -> dict | None:
        """
        Fetches the memoir created by the current user.
        """

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session is missing user ID."
            )

        try:
            response = memoir_repository.fetch_memoir_by_user_id(user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch memoir: {str(e)}"
            )

        if not response.data:
            return None

        return response.data[0]