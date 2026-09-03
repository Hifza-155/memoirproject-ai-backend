"""
@file integrations/supabase_client.py
@description Initializes and exports dedicated Supabase clients for admin and user operations,
enforcing strict fail-fast validation and preventing service-role privilege escalation.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# FIXED: Fail fast if ANY required key is missing. 
# Never allow the public client to fall back to the service role key.
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing from environment variables.")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY is missing from environment variables.")

if not SUPABASE_ANON_KEY:
    raise ValueError(
        "SUPABASE_ANON_KEY is missing from environment variables. "
        "Failing fast to prevent accidental RLS bypass via service role fallback."
    )

# 1. Dedicated Admin Client (Bypasses RLS safely for backend orchestration)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 2. Public/Auth Client strictly restricted by Row Level Security (NO FALLBACK)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)