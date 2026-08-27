"""
@file main.py
@description Entry point for the FastAPI application. Bootstraps environment variables, 
configures CORS middleware for frontend integration, defines health check endpoints, 
and mounts all modular feature routers.
"""

from dotenv import load_dotenv

# CRITICAL: load_dotenv() must be called BEFORE any other application modules 
# are imported so database and storage configurations can read environment variables.
load_dotenv()  

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import modular feature routers
from src.api.media import router as media_router
from src.api.memoir import router as memoir_router
from src.api.memory import router as memory_router
from src.api.auth import router as auth_router

# Initialize the core FastAPI application instance
app = FastAPI(
    title="Memoir App API",
    version="1.0.0",
    description="Backend API services for the Memoir life-story documentation platform."
)

# Configure CORS (Cross-Origin Resource Sharing) middleware 
# to allow secure communication with the Next.js frontend client.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],  # Permits all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Permits all headers for authenticated requests
)


@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint verifying that the API service is online."""
    return {"message": "Welcome to the Memoir App API"}


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint utilized by container orchestration and deployment monitors."""
    return {"status": "healthy"}


# -----------------------------------------------------------------
# FEATURE ROUTER REGISTRATION
# -----------------------------------------------------------------
app.include_router(auth_router)
app.include_router(memoir_router)
app.include_router(memory_router)
app.include_router(media_router)