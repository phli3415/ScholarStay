"""
Chat History Repository
Handles all database operations for chat history
"""

from typing import List, Optional
from ..model.chat_history import ChatHistory
from ..model.user import User


class ChatHistoryRepository:
    """Repository for ChatHistory model operations"""

    async def get_all_by_user(self, user: User, limit: int = 30, offset: int = 0) -> List[ChatHistory]:
        """
        Get all chat sessions for a user with pagination
        
        Args:
            user: User object
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of ChatHistory records
        """
        return await ChatHistory.filter(user=user).order_by("-created_at").limit(limit).offset(offset)

    async def get_by_session_id(self, session_id: str, user: User) -> Optional[ChatHistory]:
        """
        Get a specific chat session by ID, verified to belong to the user
        
        Args:
            session_id: Session identifier
            user: User object for ownership verification
            
        Returns:
            ChatHistory object or None if not found
        """
        return await ChatHistory.get_or_none(session_id=session_id, user=user)

    async def create_or_update(self, session_id: str, user: User, title: str = None, 
                              messages: List = None, metadata: dict = None) -> ChatHistory:
        """
        Create or update a chat session
        
        Args:
            session_id: Session identifier
            user: User object
            title: Session title
            messages: Message list
            metadata: Additional metadata
            
        Returns:
            ChatHistory object
        """
        chat_record, created = await ChatHistory.get_or_create(
            session_id=session_id,
            user=user,
            defaults={"title": title or "Agent Chat Session"}
        )
        
        if messages is not None:
            chat_record.messages = messages
        if metadata is not None:
            chat_record.metadata = metadata
        if title is not None:
            chat_record.title = title
            
        await chat_record.save()
        return chat_record

    async def delete_by_session_id(self, session_id: str, user: User) -> bool:
        """
        Delete a chat session by ID, verified to belong to the user
        
        Args:
            session_id: Session identifier
            user: User object for ownership verification
            
        Returns:
            True if deleted, False if not found
        """
        chat_record = await ChatHistory.get_or_none(session_id=session_id, user=user)
        if chat_record:
            await chat_record.delete()
            return True
        return False

    async def append_messages(self, session_id: str, user: User, messages: List) -> Optional[ChatHistory]:
        """
        Append messages to an existing chat session
        
        Args:
            session_id: Session identifier
            user: User object
            messages: Message list to append
            
        Returns:
            Updated ChatHistory object or None if not found
        """
        chat_record = await ChatHistory.get_or_none(session_id=session_id, user=user)
        if chat_record:
            existing_messages = chat_record.messages or []
            existing_messages.extend(messages)
            chat_record.messages = existing_messages
            await chat_record.save()
        return chat_record

    async def count_by_user(self, user: User) -> int:
        """
        Count chat sessions for a user
        
        Args:
            user: User object
            
        Returns:
            Number of sessions
        """
        return await ChatHistory.filter(user=user).count()
