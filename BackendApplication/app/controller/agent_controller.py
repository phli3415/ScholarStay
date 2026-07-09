# Agent Controller
# Handles HTTP endpoints for agent and chat operations

import logging
from typing import AsyncGenerator, Optional
from fastapi import HTTPException, status
from langchain_core.messages import HumanMessage
from ..model.user import User
from ..service.chat_history_service import ChatHistoryService

logger = logging.getLogger(__name__)

# The legacy AgentExecutor agent depends on agent_tools.py, which was deprecated
# (its tool functions are all commented out) without agent.py being updated to
# match. Import it defensively so a broken legacy module doesn't take down the
# whole app — /chat just returns 503 instead.
try:
    from ..agent.agent import run_agent
except Exception as e:
    logger.error(f"Legacy AgentExecutor agent unavailable: {e}")
    run_agent = None


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
        if run_agent is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Legacy agent is unavailable"
            )

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

    async def chat_with_workflow(self, query: str, session_id: str, user: User, graph: Optional[object]) -> dict:
        """
        Chat with the new LangGraph-based agentic workflow (non-streaming).

        Runs alongside `chat_with_agent` (the original AgentExecutor) so the new
        workflow can be validated independently before it replaces `/chat`.

        Args:
            query: User's query message
            session_id: Chat session identifier, used as the LangGraph thread_id
            user: Current user
            graph: The compiled workflow graph (app.state.graph), or None if it
                failed to initialize at startup

        Returns:
            dict with the assistant's reply text and a few workflow fields
        """
        if graph is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agentic workflow is not available"
            )

        try:
            config = {"configurable": {"thread_id": session_id, "user_id": str(user.id)}}
            result = await graph.ainvoke(
                {"user_input": query, "messages": [HumanMessage(content=query)]},
                config=config,
            )
            messages = result.get("messages", [])
            reply = messages[-1].content if messages else ""
            return {
                "reply": reply,
                "intent_type": result.get("intent_type"),
                "recommendation": result.get("recommendation", []),
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow error: {str(e)}"
            )
