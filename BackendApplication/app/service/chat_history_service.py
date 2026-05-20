# Chat History Service
# Handles business logic for chat operations

from typing import List, Optional, Dict, Any
from datetime import datetime
from ..model.user import User
from ..model.chat_history import ChatHistory
from ..repository.chat_history_repository import ChatHistoryRepository


class ChatHistoryService:
    """Service for chat history business logic"""

    def __init__(self):
        self.repository = ChatHistoryRepository()

    async def get_user_sessions(self, user: User, limit: int = 30, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all chat sessions for a user with metadata
        
        Args:
            user: User object
            limit: Maximum number of sessions
            offset: Pagination offset
            
        Returns:
            List of session dicts with {session_id, title, created_at, updated_at, message_count}
        """
        sessions = await self.repository.get_all_by_user(user, limit, offset)
        
        return [
            {
                "session_id": session.session_id,
                "title": session.title or "Untitled",
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "message_count": len(session.messages) if session.messages else 0
            }
            for session in sessions
        ]

    async def get_session_detail(self, session_id: str, user: User) -> Optional[Dict[str, Any]]:
        """
        Get full details of a chat session
        
        Args:
            session_id: Session identifier
            user: User object
            
        Returns:
            Session dict with all data or None if not found/not owned
        """
        chat_session = await self.repository.get_by_session_id(session_id, user)
        
        if not chat_session:
            return None
        
        return {
            "session_id": chat_session.session_id,
            "title": chat_session.title,
            "messages": chat_session.messages,
            "metadata": chat_session.metadata,
            "created_at": chat_session.created_at,
            "updated_at": chat_session.updated_at
        }

    async def delete_session(self, session_id: str, user: User) -> bool:
        """
        Delete a chat session
        
        Args:
            session_id: Session identifier
            user: User object
            
        Returns:
            True if deleted, False if not found/not owned
        """
        return await self.repository.delete_by_session_id(session_id, user)

    async def save_chat_messages(self, session_id: str, user: User, messages: List[Dict[str, Any]], 
                                user_input: str = "") -> ChatHistory:
        """
        Save or update chat messages
        
        Args:
            session_id: Session identifier
            user: User object
            messages: List of message dicts with detailed structure
            user_input: User input for title generation
            
        Returns:
            Updated ChatHistory object
        """
        chat_record = await self.repository.get_by_session_id(session_id, user)
        
        # Create new session if doesn't exist
        if not chat_record:
            title = await self._generate_title(user_input) if user_input else "Agent Chat Session"
            chat_record = await self.repository.create_or_update(
                session_id=session_id,
                user=user,
                title=title,
                messages=messages
            )
        else:
            # Append to existing messages
            await self.repository.append_messages(session_id, user, messages)
            chat_record = await self.repository.get_by_session_id(session_id, user)
        
        return chat_record

    async def get_session_count(self, user: User) -> int:
        """
        Get total count of sessions for a user
        
        Args:
            user: User object
            
        Returns:
            Number of sessions
        """
        return await self.repository.count_by_user(user)

    async def _generate_title(self, user_input: str) -> str:
        """
        Generate a title for the chat session based on user input
        
        Args:
            user_input: User's query text
            
        Returns:
            Generated title string
        """
        # Limit to first 50 characters or first sentence
        title = user_input[:50] if len(user_input) > 50 else user_input
        if "。" in user_input:
            title = user_input.split("。")[0]
        elif "." in user_input:
            title = user_input.split(".")[0]
        return title.strip() if title else "Agent Chat Session"
