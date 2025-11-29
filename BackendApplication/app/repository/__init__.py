"""
Repository Layer
Data Access Layer - handles all database CRUD operations
"""

from user_repository import UserRepository
from house_repository import HouseRepository
from bookmark_repository import BookmarkRepository

__all__ = [
    "UserRepository",
    "HouseRepository",
    "BookmarkRepository",
]

