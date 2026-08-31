"""
@file src/domain/authorization.py
@description Centralized authorization and role-checking helpers for memoir participants.
"""

from fastapi import HTTPException, status
from src.integrations import memoir_repository  # or memory_repository


def verify_active_participant(memoir_id: str, user_id: str, required_roles: list[str] = None) -> dict:
    """
    Verifies that a user is an active (non-removed) participant of a memoir 
    and optionally checks if they possess one of the required roles.

    Args:
        memoir_id (str): The memoir container ID.
        user_id (str): The user ID.
        required_roles (list[str], optional): List of allowed roles (e.g., ['owner', 'admin', 'contributor']).

    Returns:
        dict: The participant record dictionary.

    Raises:
        HTTPException (403): If unauthorized, removed, or lacking the required role.
    """
    from src.integrations import memory_repository  # Avoid circular imports if needed

    res = memory_repository.fetch_participant(str(memoir_id), str(user_id))
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not an active participant of this memoir."
        )

    participant = res.data[0]

    # Explicit check for removed status (just in case query soft-filter is bypassed)
    if participant.get("removed_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Your participation in this memoir has been revoked."
        )

    # If specific write/admin roles are required, enforce them
    if required_roles:
        user_role = participant.get("role")
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of the following roles: {', '.join(required_roles)}."
            )

    return participant