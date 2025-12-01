"""
Controller Layer
API Layer - handles HTTP requests and responses
"""

from user_controller import router as user_router
from house_controller import router as house_router
from bookmark_controller import router as bookmark_router

__all__ = [
    "user_router",
    "house_router",
    "bookmark_router",
]

