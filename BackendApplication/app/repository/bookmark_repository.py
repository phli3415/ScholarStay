"""
Bookmark Repository
Handles all database operations related to Bookmark model
"""

from typing import Optional, List
from ..model.bookmark import Bookmark


class BookmarkRepository:
    """Repository for Bookmark model operations"""
    
    @staticmethod
    async def get_by_id(bookmark_id: int) -> Optional[Bookmark]:
        """
        Get bookmark by ID
        
        Args:
            bookmark_id: ID of the bookmark
            
        Returns:
            Bookmark object or None if not found
        """
        return await Bookmark.get_or_none(id=bookmark_id)
    
    @staticmethod
    async def get_by_user(user_id: int) -> List[Bookmark]:
        """
        Get all bookmarks of a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Bookmark objects with related house information
        """
        return await Bookmark.filter(user_id=user_id).prefetch_related("house").all()
    
    @staticmethod
    async def get_by_user_and_house(user_id: int, house_id: int) -> Optional[Bookmark]:
        """
        Get bookmark by user and house
        
        Args:
            user_id: ID of the user
            house_id: ID of the house
            
        Returns:
            Bookmark object or None if not found
        """
        return await Bookmark.filter(user_id=user_id, house_id=house_id).first()
    
    @staticmethod
    async def get_by_house(house_id: int) -> List[Bookmark]:
        """
        Get all users who bookmarked a specific house
        
        Args:
            house_id: ID of the house
            
        Returns:
            List of Bookmark objects
        """
        return await Bookmark.filter(house_id=house_id).prefetch_related("user").all()
    
    @staticmethod
    async def create(user_id: int, house_id: int) -> Bookmark:
        """
        Create a new bookmark
        
        Args:
            user_id: ID of the user
            house_id: ID of the house to bookmark
            
        Returns:
            Created Bookmark object
            
        Raises:
            IntegrityError: if bookmark already exists (unique constraint)
        """
        return await Bookmark.create(user_id=user_id, house_id=house_id)
    
    @staticmethod
    async def delete(bookmark_id: int) -> bool:
        """
        Delete bookmark by ID
        
        Args:
            bookmark_id: ID of the bookmark to delete
            
        Returns:
            True if deleted, False if bookmark not found
        """
        bookmark = await Bookmark.get_or_none(id=bookmark_id)
        if bookmark:
            await bookmark.delete()
            return True
        return False
    
    @staticmethod
    async def delete_by_user_and_house(user_id: int, house_id: int) -> bool:
        """
        Delete bookmark by user and house
        
        Args:
            user_id: ID of the user
            house_id: ID of the house
            
        Returns:
            True if deleted, False if bookmark not found
        """
        bookmark = await Bookmark.filter(user_id=user_id, house_id=house_id).first()
        if bookmark:
            await bookmark.delete()
            return True
        return False
    
    @staticmethod
    async def count() -> int:
        """
        Get total count of bookmarks
        
        Returns:
            Total number of bookmarks
        """
        return await Bookmark.all().count()
    
    @staticmethod
    async def count_by_user(user_id: int) -> int:
        """
        Get count of bookmarks for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of bookmarks for the user
        """
        return await Bookmark.filter(user_id=user_id).count()
    
    @staticmethod
    async def count_by_house(house_id: int) -> int:
        """
        Get count of users who bookmarked a house
        
        Args:
            house_id: ID of the house
            
        Returns:
            Number of users who bookmarked this house
        """
        return await Bookmark.filter(house_id=house_id).count()
    
    @staticmethod
    async def exists(user_id: int, house_id: int) -> bool:
        """
        Check if a bookmark exists for user and house
        
        Args:
            user_id: ID of the user
            house_id: ID of the house
            
        Returns:
            True if bookmark exists, False otherwise
        """
        bookmark = await Bookmark.filter(user_id=user_id, house_id=house_id).first()
        return bookmark is not None

