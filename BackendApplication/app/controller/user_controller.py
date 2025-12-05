"""
User Controller
Handles HTTP requests/responses for user operations
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from ..service.user_service import UserService
from ..model.user import User

router = APIRouter(tags=["users"])
service = UserService()


# Request Models
class UserCreateRequest(BaseModel):
    gmail: EmailStr
    username: str
    password: str


class UserLoginRequest(BaseModel):
    gmail: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


# Response Models
class UserResponse(BaseModel):
    id: int
    gmail: str
    username: str
    created_at: str
    
    class Config:
        from_attributes = True


# Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreateRequest):
    """Register a new user"""
    try:
        user = await service.register_user(
            gmail=user_data.gmail,
            username=user_data.username,
            password=user_data.password
        )
        return UserResponse(
            id=user.id,
            gmail=user.gmail,
            username=user.username,
            created_at=user.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=UserResponse)
async def login_user(login_data: UserLoginRequest):
    """Authenticate user and return user information"""
    user = await service.authenticate_user(
        gmail=login_data.gmail,
        password=login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid gmail or password"
        )
    return UserResponse(
        id=user.id,
        gmail=user.gmail,
        username=user.username,
        created_at=user.created_at.isoformat()
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get user by ID"""
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return UserResponse(
        id=user.id,
        gmail=user.gmail,
        username=user.username,
        created_at=user.created_at.isoformat()
    )


@router.get("/gmail/{gmail}", response_model=UserResponse)
async def get_user_by_gmail(gmail: str):
    """Get user by gmail address"""
    user = await service.get_user_by_gmail(gmail)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with gmail {gmail} not found"
        )
    return UserResponse(
        id=user.id,
        gmail=user.gmail,
        username=user.username,
        created_at=user.created_at.isoformat()
    )


@router.get("/username/{username}", response_model=UserResponse)
async def get_user_by_username(username: str):
    """Get user by username"""
    user = await service.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found"
        )
    return UserResponse(
        id=user.id,
        gmail=user.gmail,
        username=user.username,
        created_at=user.created_at.isoformat()
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdateRequest):
    """Update user profile"""
    try:
        update_dict = user_data.dict(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        user = await service.update_user_profile(user_id, **update_dict)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return UserResponse(
            id=user.id,
            gmail=user.gmail,
            username=user.username,
            created_at=user.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{user_id}/change-password", status_code=status.HTTP_200_OK)
async def change_password(user_id: int, password_data: PasswordChangeRequest):
    """Change user password"""
    success = await service.change_password(
        user_id=user_id,
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect or user not found"
        )
    return {"message": "Password changed successfully"}


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int):
    """Delete a user"""
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return {"message": "User deleted successfully"}


@router.delete("/gmail/{gmail}", status_code=status.HTTP_200_OK)
async def delete_user_by_gmail(gmail: str):
    """Delete a user by gmail address"""
    success = await service.delete_user_by_gmail(gmail)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with gmail {gmail} not found"
        )
    return {"message": "User deleted successfully"}

