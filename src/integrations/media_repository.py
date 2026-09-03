"""
@file media_repository.py
@description Data access layer adapter module handling direct Supabase queries 
for participant authorizations and media asset metadata persistence.
"""

from src.integrations.supabase_client import supabase


def fetch_participant(memoir_id: str, user_id: str):
    """
    Queries the database to verify if a user is an authorized participant of a memoir.

    Args:
        memoir_id (str): The unique identifier of the target memoir.
        user_id (str): The unique identifier of the user.

    Returns:
        Any: The database query result object containing participant data.
    """
    return supabase.table("memoir_participant") \
        .select("id") \
        .eq("memoir_id", memoir_id) \
        .eq("user_id", user_id) \
        .is_("removed_at", "null") \
        .execute()


def insert_media_metadata(media_data: dict):
    """
    Persists a new media asset metadata record into the database.

    Args:
        media_data (dict): The dictionary containing validated media asset attributes.

    Returns:
        Any: The database response object containing the inserted media record.
    """
    return supabase.table("media_asset").insert(media_data).execute()

def check_existing_media_by_checksum(memoir_id: str, checksum: str):
    """
    Checks if a media asset with the exact same checksum already exists in this memoir 
    to prevent duplicate ghost uploads.
    """
    if not checksum:
        return None
    res = supabase.table("media_asset") \
        .select("id, storage_key") \
        .eq("memoir_id", memoir_id) \
        .eq("checksum_sha256", checksum) \
        .execute()
    return res.data[0] if res.data else None