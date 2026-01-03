"""
Bookmark Service
Business logic for bookmark operations, with security checks.
"""

from typing import List, Optional
from ..model.bookmark import Bookmark
from ..repository.bookmark_repository import BookmarkRepository
from ..repository.user_repository import UserRepository
from ..repository.house_repository import HouseRepository


class BookmarkService:
    """Service for bookmark business logic"""

    def __init__(self):
        self.bookmark_repo = BookmarkRepository()
        self.user_repo = UserRepository()
        self.house_repo = HouseRepository()

    async def get_user_bookmarks(self, user_id: int) -> List[Bookmark]:
        """Get all bookmarks of a specific user."""
        return await self.bookmark_repo.get_by_user(user_id)

    async def add_bookmark(self, user_id: int, house_id: int) -> Bookmark:
        """
        Add a house to a user's bookmarks.
        Raises ValueError if bookmark already exists or if user/house not found.
        """
        # Verify user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")

        # Verify house exists
        house = await self.house_repo.get_by_id(house_id)
        if not house:
            raise ValueError(f"House with ID {house_id} not found.")

        # Check if bookmark already exists
        existing = await self.bookmark_repo.get_by_user_and_house(user_id, house_id)
        if existing:
            raise ValueError(f"Bookmark already exists for this user and house.")

        return await self.bookmark_repo.create(user_id=user_id, house_id=house_id)

    async def remove_bookmark(self, user_id: int, house_id: int) -> bool:
        """Remove a bookmark by user and house ID."""
        return await self.bookmark_repo.delete_by_user_and_house(user_id, house_id)

    async def delete_bookmark_for_user(self, bookmark_id: int, user_id: int) -> bool:
        """
        Delete a bookmark by its ID, but only if it belongs to the specified user.
        This adds a crucial ownership check.
        """
        # First, retrieve the bookmark
        bookmark = await self.bookmark_repo.get_by_id(bookmark_id)

        # Check for existence AND ownership
        if not bookmark or bookmark.user_id != user_id:
            return False

        # If checks pass, delete it
        await self.bookmark_repo.delete(bookmark_id) # This re-fetches and deletes, can be optimized if needed
        return True

    async def is_bookmarked(self, user_id: int, house_id: int) -> bool:
        """Check if a house is bookmarked by a user."""
        return await self.bookmark_repo.exists(user_id, house_id)

    # The methods below are not directly used by the controller but can be useful for other services or analytics.

    async def get_bookmark_count(self) -> int:
        return await self.bookmark_repo.count()

    async def get_bookmark_count_by_user(self, user_id: int) -> int:
        return await self.bookmark_repo.count_by_user(user_id)

    async def get_bookmark_count_by_house(self, house_id: int) -> int:
        return await self.bookmark_repo.count_by_house(house_id)
