"""
Bookmark Controller
Handles all secure HTTP requests/responses for bookmark operations.
Endpoints are redesigned to be user-centric and secure.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List

from ..service.bookmark_service import BookmarkService
from ..model.user import User
from ..model.bookmark import Bookmark
from ..core.firebase_auth import get_current_user

router = APIRouter(tags=["Bookmarks"])
service = BookmarkService()


# Request Models
class BookmarkCreateRequest(BaseModel):
    # user_id is removed for security. It's derived from the authenticated user.
    house_id: int


# Response Models
class BookmarkResponse(BaseModel):
    id: int
    user_id: int
    house_id: int
    created_at: str

    class Config:
        from_attributes = True

class BookmarkWithHouseResponse(BaseModel):
    id: int
    user_id: int
    house_id: int
    created_at: str
    house: dict  # Contains house details

    class Config:
        from_attributes = True


def bookmark_to_response(bookmark: Bookmark) -> BookmarkResponse:
    return BookmarkResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        house_id=bookmark.house_id,
        created_at=bookmark.created_at.isoformat()
    )

def bookmark_with_house_to_response(bookmark: Bookmark) -> BookmarkWithHouseResponse:
    house = bookmark.house
    # Basic check in case house relation is not loaded
    if not house:
        return BookmarkWithHouseResponse(id=bookmark.id, user_id=bookmark.user_id, house_id=bookmark.house_id, created_at=bookmark.created_at.isoformat(), house={})

    return BookmarkWithHouseResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        house_id=bookmark.house_id,
        created_at=bookmark.created_at.isoformat(),
        house={
            "id": house.id,
            "province": house.province,
            "city": house.city,
            "monthly_rent": float(house.monthly_rent),
            # Add other desired house fields here
        }
    )


# Endpoints
@router.post("/", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def add_bookmark(
    bookmark_data: BookmarkCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Add a house to the current user's bookmarks."""
    try:
        # user_id is now securely taken from the authenticated user
        bookmark = await service.add_bookmark(
            user_id=current_user.id,
            house_id=bookmark_data.house_id
        )
        return bookmark_to_response(bookmark)
    except ValueError as e:
        # This typically means bookmark already exists or house/user not found
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/me/", response_model=List[BookmarkWithHouseResponse])
async def get_my_bookmarks(current_user: User = Depends(get_current_user)):
    """Get all bookmarks for the currently authenticated user."""
    bookmarks = await service.get_user_bookmarks(current_user.id)
    return [bookmark_with_house_to_response(b) for b in bookmarks]


@router.get("/check/{house_id}/", response_model=dict)
async def check_is_bookmarked(
    house_id: int,
    current_user: User = Depends(get_current_user)
):
    """Check if a house is bookmarked by the current user."""
    is_bookmarked = await service.is_bookmarked(current_user.id, house_id)
    return {"is_bookmarked": is_bookmarked}


@router.delete("/by-house/{house_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark_by_house(
    house_id: int,
    current_user: User = Depends(get_current_user)
):
    """Remove a bookmark for the current user based on house_id."""
    success = await service.remove_bookmark(current_user.id, house_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark for this house not found.")
    # No content returned on successful deletion


@router.delete("/by-id/{bookmark_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark_by_id(
    bookmark_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a bookmark by its ID, ensuring it belongs to the current user."""
    # Authorization logic is now in the service layer
    success = await service.delete_bookmark_for_user(bookmark_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark with ID {bookmark_id} not found or you do not have permission to delete it.")
    # No content returned on successful deletion
