from fastapi import APIRouter, Depends, status
from typing import Dict

from ...core.firebase_auth import verify_firebase_token, get_current_user, create_or_update_user
from ...model.user import User, User_Pydantic

router = APIRouter()

@router.post("/register",
             response_model=User_Pydantic,
             summary="Register or Login a user",
             description="Receives a Firebase ID token, verifies it, and then creates a new user in the database or retrieves an existing one.",
             status_code=status.HTTP_201_CREATED)
async def register_user(decoded_token: Dict = Depends(verify_firebase_token)) -> User:
    """
    Handles user registration or login.
    This endpoint uses the `verify_firebase_token` dependency to ensure the token is valid.
    Then, it creates a new user if one doesn't exist, or returns the existing user.
    """
    return await create_or_update_user(decoded_token)

@router.get("/me",
            response_model=User_Pydantic,
            summary="Get current user",
            description="Returns the authenticated user's profile information.")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    The `get_current_user` dependency ensures that the user is authenticated and exists in the database.
    """
    return current_user
