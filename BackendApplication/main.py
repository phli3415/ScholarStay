from fastapi import FastAPI
from tortoise import Tortoise

# Import core and database modules
from app.core.firebase_auth import initialize_firebase
from app.database import TORTOISE_ORM

# Import API routers
from app.api.v1 import user_router
from app.controller import house_controller
from app.controller import user_controller

# Create FastAPI app instance
app = FastAPI(
    title="ScholarStay API",
    description="API for ScholarStay application",
    version="1.0.0"
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
    house_controller.router,
    prefix="/api/v1",
    tags=["Houses"]
)

app.include_router(
    house_controller.router,
    prefix="/api/v1/user",
    tags=["Users"]
)
# --- Root Endpoint ---
@app.get("/", tags=["Default"])
async def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to the ScholarStay API!"}
