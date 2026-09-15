"""
@file memoir_repository.py
@description Data access layer adapter module handling direct Supabase queries
and persistence for user accounts, memoirs, and memoir participant roles.
"""

from src.integrations.supabase_client import supabase_admin


def fetch_user_account(user_id: str):
    """
    Fetches user account profile details from the database.

    Args:
        user_id (str): The unique identifier of the user account.

    Returns:
        Any: The database query result containing profile records.
    """
    return (
        supabase_admin
        .table("user_account")
        .select("full_name, email")
        .eq("id", user_id)
        .execute()
    )


def insert_memoir(memoir_data: dict):
    """
    Inserts a new root memoir container record into the database.

    Args:
        memoir_data (dict): The dictionary containing validated memoir properties.

    Returns:
        Any: The database response object containing the inserted memoir record.
    """
    return supabase_admin.table("memoir").insert(memoir_data).execute()


def insert_memoir_participant(participant_data: dict):
    """
    Registers a user as a participant in a memoir container.

    Args:
        participant_data (dict): The dictionary containing participant mapping data.

    Returns:
        Any: The database response object from the participant insertion.
    """
    return (
        supabase_admin
        .table("memoir_participant")
        .insert(participant_data)
        .execute()
    )


def delete_memoir_record(memoir_id: str):
    """Deletes an orphan memoir during a failed transaction rollback."""
    return (
        supabase_admin
        .table("memoir")
        .delete()
        .eq("id", memoir_id)
        .execute()
    )


def fetch_memoir_by_user_id(user_id: str):
    """
    Fetches the memoir created by the current user.

    Args:
        user_id (str): The unique identifier of the current user.

    Returns:
        Any: The database query result containing the user's memoir.
    """
    return (
        supabase_admin
        .table("memoir")
        .select(
            "id, subject_name, subject_born_on, subject_died_on, "
            "subject_is_living, description, visibility, "
            "comment_policy, created_by_user_id, status"
        )
        .eq("created_by_user_id", user_id)
        .limit(1)
        .execute()
    )