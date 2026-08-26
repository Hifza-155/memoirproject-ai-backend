"""
@file core/auth.py
@description Secure token verification using the official Supabase SDK auth.get_user method.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.integrations.supabase_client import supabase

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates the Supabase JWT Bearer token via Supabase Auth and returns the user's UUID.
    Bypasses local secret mismatches by delegating validation to the Supabase client.
    """
    token = credentials.credentials
    try:
        # Query Supabase Auth to verify the token and fetch the user session
        response = supabase.auth.get_user(token)
        
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token."
            )
            
        return response.user.id
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )