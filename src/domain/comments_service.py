"""
@file services/comments_service.py
@description Business logic layer for comment processing.
"""

from typing import List, Dict, Any
from src.integrations.comments_repository import CommentsRepository
from fastapi import HTTPException, status

class CommentsService:

    @staticmethod
    async def get_memory_comments(memory_id: str) -> List[Dict[str, Any]]:
        if not memory_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Memory ID is required."
            )
        return await CommentsRepository.get_comments_by_memory_id(memory_id)

    @staticmethod
    async def create_new_comment(payload: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        if not payload.get("body") or not payload["body"].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment text cannot be empty."
            )
        return await CommentsRepository.insert_comment(payload, user_id)