"""
@file core/config.py
@description Centralized application constants and configurations loaded from environment variables.
"""

import os

# Load bucket name from environment variables (defaults to 'media-bucket' if not set)
STORAGE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "media-bucket")

# Other application constants
STORAGE_TIER_HOT = "hot"
TRANSCRIPTION_STATUS_SKIPPED = "skipped"
TRANSCRIPTION_STATUS_PENDING = "pending"