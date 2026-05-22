from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

# Import core and database modules
from app.core.firebase_auth import initialize_firebase
from app.database import TORTOISE_ORM

#Import system packages
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
import sys
import time
import uuid

# Import API routers
from app.api.v1 import user_router
from app.api.v1 import agent_router
from app.controller import house_controller
from app.controller import user_controller
from app.controller import bookmark_controller

#Set up basic logging config, level = DEBUG / INFO
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)

logger.handlers = [] #Clear default handlers



# Create FastAPI app instance
app = FastAPI(
    title="ScholarStay API",
    description="API for ScholarStay application",
    version="1.0.0"
)

# --- CORS Middleware ---
# Define the list of allowed origins (frontend URL)
origins = [
    "http://localhost:5173",  # React/Vite dev server
    "http://127.0.0.1:5173",
]

# Add CORS middleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    - Initializes Firebase Admin SDK
    - Initializes Tortoise ORM and creates database schemas
    """
    print("Starting up application...")
    initialize_firebase()

    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    print("Database connection established.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    - Closes database connections gracefully
    """
    print("Shutting down application...")
    await Tortoise.close_connections()
    print("Database connections closed.")



# --- API Routers ---
# Include the user router with a prefix and tags for organization
app.include_router(
    user_router.router,
    prefix="/api/v1/auth",
    tags=["Auth"]
)

app.include_router(
    agent_router.router,
    prefix="/api/v1",
    tags=["Agent"]
)

app.include_router(
    house_controller.router,
    prefix="/api/v1",
    tags=["Houses"]
)

app.include_router(
    user_controller.router,
    prefix="/api/v1/user",
    tags=["Users"]
)

app.include_router(
    bookmark_controller.router,
    prefix="/api/v1/bookmarks",
    tags=["bookmarks"]
)

# --- Root Endpoint ---
@app.get("/", tags=["Default"])
async def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to the ScholarStay API!"}
