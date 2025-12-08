"""
User Controller
Handles HTTP requests/responses for user operations, integrated with Firebase Auth.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from ..service.user_service import UserService
from ..model.user import User
from ..core.firebase_auth import get_current_user, verify_firebase_token  # Correct import

router = APIRouter(prefix="/api/v1/user", tags=["Users"])
service = UserService()


# --- Request Models ---

class UserCreateRequest(BaseModel):
    """Request model for creating a user record after Firebase authentication."""
    username: str

class UserUpdateRequest(BaseModel):
    """Request model for updating a user's profile."""
    username: Optional[str] = None


# --- Response Models ---

class UserResponse(BaseModel):
    """Response model for user information."""
    id: int
    firebase_uid: str
    gmail: EmailStr
    username: str

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user in the database",
    description="This endpoint is called AFTER the user has been created in Firebase. It creates a corresponding user record in the local database."
)
async def register_user(
    user_data: UserCreateRequest,
    token_claims: Dict = Depends(verify_firebase_token)  # Use verify_firebase_token
):
    """
    Creates a user record in the database.
    The user must be authenticated with Firebase first.
    The Firebase ID Token must be passed in the 'Authorization' header.
    """
    firebase_uid = token_claims["uid"]
    gmail = token_claims["email"]

    try:
        user = await service.register_user(
            firebase_uid=firebase_uid,
            gmail=gmail,
            username=user_data.username
        )
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user's profile"
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieves the profile of the currently authenticated user from the database.
    """
    # The dependency `get_current_user` already fetches the user object.
    return UserResponse.from_orm(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user's profile"
)
async def update_me(
    user_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Updates the username of the currently authenticated user.
    """
    update_dict = user_data.dict(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update."
        )

    try:
        # We pass the firebase_uid from the user object provided by the dependency
        updated_user = await service.update_user_profile(
            firebase_uid=current_user.firebase_uid,
            **update_dict
        )
        if not updated_user:
            # This case should ideally not be reached if get_current_user succeeds
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user's account"
)
async def delete_me(current_user: User = Depends(get_current_user)):
    """
    Deletes the user's record from the local database.
    Note: This does NOT delete the user from Firebase Authentication.
    """
    success = await service.delete_user(current_user.firebase_uid)
    if not success:
        # This case should ideally not be reached if get_current_user succeeds
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    # No content to return on successful deletion
    return None
