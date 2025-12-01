"""
Bookmark Service
Business logic for bookmark operations
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
        """
        Get all bookmarks of a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Bookmark objects with related house information
        """
        return await self.bookmark_repo.get_by_user(user_id)
    
    async def add_bookmark(self, user_id: int, house_id: int) -> Optional[Bookmark]:
        """
        Add a house to user's bookmarks
        
        Args:
            user_id: ID of the user
            house_id: ID of the house to bookmark
            
        Returns:
            Created Bookmark object or None if user/house doesn't exist
            
        Raises:
            ValueError: if bookmark already exists
        """
        # Verify user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
        
        # Verify house exists
        house = await self.house_repo.get_by_id(house_id)
        if not house:
            return None
        
        # Check if bookmark already exists
        existing = await self.bookmark_repo.get_by_user_and_house(user_id, house_id)
        if existing:
            raise ValueError(f"Bookmark already exists for user {user_id} and house {house_id}")
        
        return await self.bookmark_repo.create(user_id=user_id, house_id=house_id)
    
    async def remove_bookmark(self, user_id: int, house_id: int) -> bool:
        """
        Remove a bookmark
        
        Args:
            user_id: ID of the user
            house_id: ID of the house
            
        Returns:
            True if removed successfully, False if bookmark not found
        """
        return await self.bookmark_repo.delete_by_user_and_house(user_id, house_id)
    
    async def delete_bookmark(self, bookmark_id: int) -> bool:
        """
        Delete bookmark by ID
        
        Args:
            bookmark_id: ID of the bookmark to delete
            
        Returns:
            True if deleted successfully, False if bookmark not found
        """
        return await self.bookmark_repo.delete(bookmark_id)
    
    async def is_bookmarked(self, user_id: int, house_id: int) -> bool:
        """
        Check if a house is bookmarked by a user
        
        Args:
            user_id: ID of the user
            house_id: ID of the house
            
        Returns:
            True if bookmarked, False otherwise
        """
        return await self.bookmark_repo.exists(user_id, house_id)
    
    async def get_bookmark_count(self) -> int:
        """
        Get total count of bookmarks
        
        Returns:
            Total number of bookmarks
        """
        return await self.bookmark_repo.count()
    
    async def get_bookmark_count_by_user(self, user_id: int) -> int:
        """
        Get count of bookmarks for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of bookmarks for the user
        """
        return await self.bookmark_repo.count_by_user(user_id)
    
    async def get_bookmark_count_by_house(self, house_id: int) -> int:
        """
        Get count of users who bookmarked a house
        
        Args:
            house_id: ID of the house
            
        Returns:
            Number of users who bookmarked this house
        """
        return await self.bookmark_repo.count_by_house(house_id)

