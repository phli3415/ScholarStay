"""
User Service
Business logic for user operations, adapted for Firebase Authentication.
"""

from typing import Optional
from ..model.user import User
from ..repository.user_repository import UserRepository


class UserService:
    """Service for user business logic, assuming authentication is handled by Firebase."""

    def __init__(self):
        self.repository = UserRepository()

    async def register_user(self, firebase_uid: str, gmail: str, username: str) -> User:
        """
        Registers a new user profile in the database.
        Relies on the repository to handle potential race conditions during creation.

        Args:
            firebase_uid: The unique ID from Firebase.
            gmail: The user's email address from Firebase.
            username: The username chosen by the user.

        Returns:
            The created User object.

        Raises:
            ValueError: If a user with the given firebase_uid or gmail already exists.
        """
        user = await self.repository.create(firebase_uid=firebase_uid, gmail=gmail, username=username)

        if user is None:
            # This indicates an IntegrityError was caught in the repository,
            # meaning a user with the same unique key (firebase_uid or gmail) already exists.
            raise ValueError("User with this Firebase UID or Gmail already exists.")

        return user

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """
        Retrieves a user by their Firebase UID.

        Args:
            firebase_uid: The Firebase Unique ID.

        Returns:
            User object or None if not found.
        """
        return await self.repository.get_by_firebase_uid(firebase_uid)

    async def update_user_profile(self, firebase_uid: str, **kwargs) -> Optional[User]:
        """
        Updates a user's profile information.

        Args:
            firebase_uid: The Firebase UID of the user to update.
            **kwargs: Fields to update (e.g., username="new_username").

        Returns:
            The updated User object or None if the user is not found.

        Raises:
            ValueError: If the new username is already taken.
        """
        user = await self.repository.get_by_firebase_uid(firebase_uid)
        if not user:
            return None

        if 'username' in kwargs and kwargs['username'] != user.username:
            if await self.repository.get_by_username(kwargs['username']):
                raise ValueError(f"Username '{kwargs['username']}' is already taken.")

        return await self.repository.update(user, **kwargs)

    async def delete_user(self, firebase_uid: str) -> bool:
        """
        Deletes a user from the database by their Firebase UID.

        Args:
            firebase_uid: The Firebase UID of the user to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        user = await self.repository.get_by_firebase_uid(firebase_uid)
        if not user:
            return False

        return await self.repository.delete(user.id)