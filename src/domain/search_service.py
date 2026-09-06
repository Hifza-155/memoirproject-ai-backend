"""
@file domain/search_service.py
@description Business logic layer for validating search access and executing full-text searches.
"""

from fastapi import HTTPException, status
from src.domain.authorization import verify_active_participant
from src.integrations import search_repository

class SearchService:
    """
    Handles memoir search authorization and result aggregation.
    """

    @classmethod
    def search_memoir(cls, memoir_id: str, query_text: str, user_id: str) -> list:
        """
        Validates user permissions for the memoir and performs full-text search.
        """
        # 1. Enforce security: Ensure user is an active participant of this memoir
        verify_active_participant(
            memoir_id, 
            user_id, 
            required_roles=["owner", "admin", "contributor"]
        )

        # 2. Sanitize/validate query input
        if not query_text or len(query_text.strip()) == 0:
            return []

        # 3. Execute search via repository
        try:
            results = search_repository.search_memoir_content(memoir_id, query_text.strip())
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database search error: {str(e)}"
            )

        return results