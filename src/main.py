from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Set up basic logging for startup/shutdown messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# (Startup & Shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application...")
    yield
    logger.info("Shutting down FastAPI application...")
    
app = FastAPI(
    title="Memoir App API",
    version="1.0.0",
    lifespan=lifespan
)

#CORS Configuration
origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allows all request headers
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "API is successfully running!"}

# Health Check Endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}
