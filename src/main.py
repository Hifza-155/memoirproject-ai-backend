"""
@file main.py
@description Entry point for the FastAPI application. Loads environment variables 
and mounts all API routers.
"""

from dotenv import load_dotenv
load_dotenv()  # <-- THIS MUST BE AT THE VERY TOP BEFORE OTHER IMPORTS

from fastapi import FastAPI
from src.api.media import router as media_router
from src.api.memoir import router as memoir_router
from src.api.memory import router as memory_router
from src.api.auth import router as auth_router

app = FastAPI(
    title="Memoir App API",
    version="1.0.0"
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Memoir App API"}

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}

# -----------------------------------------------------------------
# INCLUDE FEATURE ROUTERS
# -----------------------------------------------------------------
app.include_router(media_router)
app.include_router(memoir_router)
app.include_router(memory_router)
app.include_router(auth_router)