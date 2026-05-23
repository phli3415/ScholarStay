from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

from BackendApplication.app.utils.config import Config
# Import core and database modules
from app.core.firebase_auth import initialize_firebase
from app.database import TORTOISE_ORM

#Import system packages
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
import sys
import time
import uuid
import re

# Import API routers
from app.api.v1 import user_router
from app.api.v1 import agent_router
from app.controller import house_controller
from app.controller import user_controller
from app.controller import bookmark_controller
from app.utils.config import Config
from app.utils.llms import initialize_llm, initialize_embedding


from contextlib import asynccontextmanager


#Set up basic logging config, level = DEBUG / INFO
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)

logger.handlers = [] #Clear default handlers
handler = ConcurrentRotatingFileHandler(
    Config.LOG_FILE,
    maxBytes = Config.MAX_BYTES,
    backupCount = Config.BACKUP_COUNT,
)

#Set handler level to DEBUG
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    '''
    An asynchronous context manager that manages the FastAPI application lifecycle, responsible for initialization and cleanup during startup and shutdown.

    Args:
        app (FastAPI): FastAPI application instance

    Yields:
        None: Finish initialization before yield, clean up after yield.

    Raises:
        ConnectionPoolError: Connection pool initialization failed.
        Exception: Other unexpected errors.

    '''

    global graph, tool_config
    logger.info("Starting up application")
    initialize_firebase()

    await Tortoise.init(config=TORTOISE_ORM)
    # await Tortoise.generate_schemas()
    db_url = TORTOISE_ORM["connections"]["default"]

    try:
        llm_chat = initialize_llm(Config.LLM_TYPE)
        llm_embedding = initialize_embedding(Config.LLM_TYPE)



        tools = get_tools(llm_embedding)

        # Create tool config
        tool_config = ToolConfig(tools)

        # Define database connection parameters: auto-commit, no prepared threshold, 5-second timeout
        connection_kwargs = {"autocommit": True, "prepare_threshold": 0, "connect_timeout": 5}
        # 创建数据库连接池：最大20个连接，最小2个活跃连接，超时120秒
        db_connection_pool = ConnectionPool(
            conninfo=Config.DB_URI,
            max_size=20,
            min_size=2,
            kwargs=connection_kwargs,
            timeout=120
        )




# @app.on_event("startup")
# async def startup_event():
#     """
#     Application startup event.
#     - Initializes Firebase Admin SDK
#     - Initializes Tortoise ORM and creates database schemas
#     """
#     print("Starting up application...")
#     initialize_firebase()
#
#     await Tortoise.init(config=TORTOISE_ORM)
#     await Tortoise.generate_schemas()
#     print("Database connection established.")
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     """
#     Application shutdown event.
#     - Closes database connections gracefully
#     """
#     print("Shutting down application...")
#     await Tortoise.close_connections()
#     print("Database connections closed.")
#
#

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
