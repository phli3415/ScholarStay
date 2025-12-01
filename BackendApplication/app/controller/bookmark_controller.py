"""
Bookmark Controller
Handles HTTP requests/responses for bookmark operations
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List
from ..service.bookmark_service import BookmarkService
from ..model.bookmark import Bookmark

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])
service = BookmarkService()


# Request Models
class BookmarkCreateRequest(BaseModel):
    user_id: int
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
    house: dict  # Will contain house details
    
    class Config:
        from_attributes = True


def bookmark_to_response(bookmark: Bookmark) -> BookmarkResponse:
    """Convert Bookmark model to BookmarkResponse"""
    return BookmarkResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        house_id=bookmark.house_id,
        created_at=bookmark.created_at.isoformat()
    )


def bookmark_with_house_to_response(bookmark: Bookmark) -> BookmarkWithHouseResponse:
    """Convert Bookmark model with house to BookmarkWithHouseResponse"""
    house = bookmark.house
    return BookmarkWithHouseResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        house_id=bookmark.house_id,
        created_at=bookmark.created_at.isoformat(),
        house={
            "id": house.id,
            "province": house.province,
            "city": house.city,
            "street": house.street,
            "house_number": house.house_number,
            "monthly_rent": float(house.monthly_rent),
            "distance_to_university": float(house.distance_to_university),
            "has_kitchen": house.has_kitchen,
            "has_washer": house.has_washer,
            "has_parking": house.has_parking,
            "is_rented": house.is_rented,
            "description": house.description,
        }
    )


# Endpoints
@router.post("/", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def add_bookmark(bookmark_data: BookmarkCreateRequest):
    """Add a house to user's bookmarks"""
    try:
        bookmark = await service.add_bookmark(
            user_id=bookmark_data.user_id,
            house_id=bookmark_data.house_id
        )
        if not bookmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or house not found"
            )
        return bookmark_to_response(bookmark)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/user/{user_id}", response_model=List[BookmarkWithHouseResponse])
async def get_user_bookmarks(user_id: int):
    """Get all bookmarks of a user"""
    bookmarks = await service.get_user_bookmarks(user_id)
    return [bookmark_with_house_to_response(bookmark) for bookmark in bookmarks]


@router.get("/check/{user_id}/{house_id}", status_code=status.HTTP_200_OK)
async def check_bookmark(user_id: int, house_id: int):
    """Check if a house is bookmarked by a user"""
    is_bookmarked = await service.is_bookmarked(user_id, house_id)
    return {"is_bookmarked": is_bookmarked}


@router.delete("/{user_id}/{house_id}", status_code=status.HTTP_200_OK)
async def remove_bookmark(user_id: int, house_id: int):
    """Remove a bookmark"""
    success = await service.remove_bookmark(user_id, house_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    return {"message": "Bookmark removed successfully"}


@router.delete("/id/{bookmark_id}", status_code=status.HTTP_200_OK)
async def delete_bookmark(bookmark_id: int):
    """Delete bookmark by ID"""
    success = await service.delete_bookmark(bookmark_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bookmark with ID {bookmark_id} not found"
        )
    return {"message": "Bookmark deleted successfully"}

