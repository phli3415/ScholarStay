"""
User Service
Business logic for user operations
"""

from typing import Optional
from ..model.user import User
from ..repository.user_repository import UserRepository


class UserService:
    """Service for user business logic"""
    
    def __init__(self):
        self.repository = UserRepository()
    
    async def register_user(self, gmail: str, username: str, password: str) -> User:
        """
        Register a new user with validation
        
        Args:
            gmail: user's gmail address
            username: username
            password: password (stored as plain text for simplicity)
            
        Returns:
            Created User object
            
        Raises:
            ValueError: if gmail or username already exists
        """
        # Check if gmail already exists
        existing_user = await self.repository.get_by_gmail(gmail)
        if existing_user:
            raise ValueError(f"User with gmail {gmail} already exists")
        
        # Check if username already exists
        existing_user = await self.repository.get_by_username(username)
        if existing_user:
            raise ValueError(f"Username {username} is already taken")
        
        # Create user (password stored as plain text)
        return await self.repository.create(gmail=gmail, username=username, password=password)
    
    async def authenticate_user(self, gmail: str, password: str) -> Optional[User]:
        """
        Authenticate user with gmail and password
        
        Args:
            gmail: user's gmail address
            password: password to verify
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = await self.repository.get_by_gmail(gmail)
        if not user:
            return None
        
        # Simple string comparison for password (no hashing)
        if user.password == password:
            return user
        return None
    
    async def verify_password(self, user: User, password: str) -> bool:
        """
        Verify if the given password matches user's password
        
        Args:
            user: User object
            password: password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return user.password == password
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: ID of the user
            
        Returns:
            User object or None if not found
        """
        return await self.repository.get_by_id(user_id)
    
    async def get_user_by_gmail(self, gmail: str) -> Optional[User]:
        """
        Get user by gmail address
        
        Args:
            gmail: gmail address of the user
            
        Returns:
            User object or None if not found
        """
        return await self.repository.get_by_gmail(gmail)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username
        
        Args:
            username: username of the user
            
        Returns:
            User object or None if not found
        """
        return await self.repository.get_by_username(username)
    
    async def user_exists(self, gmail: Optional[str] = None, username: Optional[str] = None) -> bool:
        """
        Check if a user exists by gmail or username
        
        Args:
            gmail: gmail address to check (optional)
            username: username to check (optional)
            
        Returns:
            True if user exists, False otherwise
        """
        if gmail:
            user = await self.repository.get_by_gmail(gmail)
            if user:
                return True
        
        if username:
            user = await self.repository.get_by_username(username)
            if user:
                return True
        
        return False
    
    async def update_user_profile(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Update user profile information
        
        Args:
            user_id: ID of the user to update
            **kwargs: fields to update (e.g., username="new_username", password="new_password")
            
        Returns:
            Updated User object or None if user not found
            
        Raises:
            ValueError: if trying to update username to one that already exists
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            return None
        
        # If updating username, check if new username is already taken
        if 'username' in kwargs and kwargs['username'] != user.username:
            existing_user = await self.repository.get_by_username(kwargs['username'])
            if existing_user:
                raise ValueError(f"Username {kwargs['username']} is already taken")
        
        # Update user fields
        return await self.repository.update(user, **kwargs)
    
    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password
        
        Args:
            user_id: ID of the user
            old_password: current password
            new_password: new password
            
        Returns:
            True if password changed successfully, False if old password is incorrect or user not found
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False
        
        # Verify old password (simple string comparison)
        if user.password != old_password:
            return False
        
        # Update to new password
        await self.repository.update(user, password=new_password)
        return True
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user
        
        Args:
            user_id: ID of the user to delete
            
        Returns:
            True if deleted successfully, False if user not found
        """
        return await self.repository.delete(user_id)
    
    async def delete_user_by_gmail(self, gmail: str) -> bool:
        """
        Delete a user by gmail address
        
        Args:
            gmail: gmail address of the user to delete
            
        Returns:
            True if deleted successfully, False if user not found
        """
        return await self.repository.delete_by_gmail(gmail)

