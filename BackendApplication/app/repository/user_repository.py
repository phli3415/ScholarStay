"""
User Repository
Handles all database operations related to User model
"""

from typing import Optional, List
from tortoise.exceptions import IntegrityError
from ..model.user import User


class UserRepository:
    """Repository for User model operations"""

    @staticmethod
    async def get_by_id(user_id: int) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: ID of the user
            
        Returns:
            User object or None if not found
        """
        return await User.get_or_none(id=user_id)

    @staticmethod
    async def get_by_gmail(gmail: str) -> Optional[User]:
        """
        Get user by gmail address
        
        Args:
            gmail: gmail address of the user
            
        Returns:
            User object or None if not found
        """
        return await User.filter(gmail=gmail).first()

    @staticmethod
    async def get_by_firebase_uid(firebase_uid: str) -> Optional[User]:
        """
        Get user by Firebase UID
        
        Args:
            firebase_uid: Firebase Unique ID of the user
            
        Returns:
            User object or None if not found
        """
        return await User.get_or_none(firebase_uid=firebase_uid)

    @staticmethod
    async def get_by_username(username: str) -> Optional[User]:
        """
        Get user by username
        
        Args:
            username: username of the user
            
        Returns:
            User object or None if not found
        """
        return await User.filter(username=username).first()

    @staticmethod
    async def get_all(limit: int = 100, offset: int = 0) -> List[User]:
        """
        Get all users with pagination
        
        Args:
            limit: maximum number of users to return
            offset: offset for pagination
            
        Returns:
            List of User objects
        """
        return await User.all().limit(limit).offset(offset)

    @staticmethod
    async def create(firebase_uid: str, gmail: str, username: str) -> Optional[User]:
        """
        Create a new user.

        Args:
            firebase_uid: Firebase Unique ID of the user.
            gmail: Gmail address of the user (must be unique).
            username: Username of the user.

        Returns:
            The created User object, or None if a user with the same
            `firebase_uid` or `gmail` already exists.
        """
        try:
            return await User.create(firebase_uid=firebase_uid, gmail=gmail, username=username)
        except IntegrityError as e:
            print(f"Error creating user due to duplicate entry: {e}")
            return None

    @staticmethod
    async def update(user: User, **kwargs) -> User:
        """
        Update user fields
        
        Args:
            user: User object to update
            **kwargs: fields to update (e.g., username="new_username")
            
        Returns:
            Updated User object
        """
        # prevent updating primary key and unique identifiers
        kwargs.pop('id', None)
        kwargs.pop('firebase_uid', None)
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await user.save()
        return user

    @staticmethod
    async def update_by_id(user_id: int, **kwargs) -> Optional[User]:
        """
        Update user by ID
        
        Args:
            user_id: ID of the user to update
            **kwargs: fields to update
            
        Returns:
            Updated User object or None if not found
        """
        user = await UserRepository.get_by_id(user_id)
        if not user:
            return None
        return await UserRepository.update(user, **kwargs)

    @staticmethod
    async def delete(user_id: int) -> bool:
        """
        Delete user by ID
        
        Args:
            user_id: ID of the user to delete
            
        Returns:
            True if deleted, False if user not found
        """
        user = await User.get_or_none(id=user_id)
        if user:
            await user.delete()
            return True
        return False

    @staticmethod
    async def delete_by_gmail(gmail: str) -> bool:
        """
        Delete user by gmail address
        
        Args:
            gmail: gmail address of the user to delete
            
        Returns:
            True if deleted, False if user not found
        """
        user = await UserRepository.get_by_gmail(gmail)
        if user:
            await user.delete()
            return True
        return False

    @staticmethod
    async def count() -> int:
        """
        Get total count of users
        
        Returns:
            Total number of users
        """
        return await User.all().count()
