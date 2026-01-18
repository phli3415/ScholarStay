# Agent Controller
# Handles HTTP endpoints for agent and chat operations

from typing import AsyncGenerator
from fastapi import HTTPException, status
from ..model.user import User
from ..service.chat_history_service import ChatHistoryService
from ..agent.agent import run_agent


class AgentController:
    """Controller for agent-related operations"""

    def __init__(self):
        self.chat_service = ChatHistoryService()

    async def get_user_sessions(self, user: User, limit: int = 20, offset: int = 0):
        """
        Get all chat sessions for the current user
        
        Args:
            user: Current user
            limit: Maximum number of sessions
            offset: Pagination offset
            
        Returns:
            List of session summaries
        """
        try:
            sessions = await self.chat_service.get_user_sessions(user, limit, offset)
            total_count = await self.chat_service.get_session_count(user)
            
            return {
                "sessions": sessions,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve sessions: {str(e)}"
            )

    async def get_session_detail(self, session_id: str, user: User):
        """
        Get full details of a chat session
        
        Args:
            session_id: Session identifier
            user: Current user
            
        Returns:
            Full session details with messages
        """
        try:
            session = await self.chat_service.get_session_detail(session_id, user)
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or access denied"
                )
            
            return session
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve session: {str(e)}"
            )

    async def delete_session(self, session_id: str, user: User):
        """
        Delete a chat session
        
        Args:
            session_id: Session identifier
            user: Current user
            
        Returns:
            Success message
        """
        try:
            deleted = await self.chat_service.delete_session(session_id, user)
            
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or access denied"
                )
            
            return {"message": "Session deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete session: {str(e)}"
            )

    async def chat_with_agent(self, query: str, session_id: str, user: User) -> AsyncGenerator:
        """
        Chat with agent and stream responses
        
        Args:
            query: User's query message
            session_id: Chat session identifier
            user: Current user
            
        Yields:
            Stream of response chunks
        """
        try:
            # Stream agent response
            async for chunk in run_agent(query, session_id, user.id):
                yield chunk
                
        except Exception as e:
            error_msg = f"Chat error: {str(e)}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
