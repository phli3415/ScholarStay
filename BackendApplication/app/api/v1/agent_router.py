# Agent Router - API endpoints for agent operations
# Uses three-layer architecture: Controller -> Service -> Repository
# Handles chat interactions, session management, and agent operations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from ...core.firebase_auth import get_current_user
from ...model.user import User
from ...controller.agent_controller import AgentController

router = APIRouter()
controller = AgentController()


class ChatRequest(BaseModel):
    query: str
    session_id: str


class ChatV2Response(BaseModel):
    reply: str
    intent_type: Optional[str] = None
    recommendation: List[str] = []


class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionsListResponse(BaseModel):
    sessions: List[ChatSessionResponse]
    total: int
    limit: int
    offset: int


@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest, 
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the AI agent - streaming response
    
    Args:
        request: ChatRequest with query and session_id
        current_user: Authenticated user from Firebase
        
    Returns:
        StreamingResponse with real-time agent response chunks
    """
    
    async def generate_response():
        """Generate and stream response from agent"""
        async for chunk in controller.chat_with_agent(
            request.query, 
            request.session_id, 
            current_user
        ):
            yield chunk

    return StreamingResponse(generate_response(), media_type="text/plain")


@router.post("/chat/v2", response_model=ChatV2Response)
async def chat_with_agent_v2(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the new LangGraph-based agentic workflow (non-streaming, experimental).

    Runs alongside `/chat` (the original AgentExecutor) so the new workflow can be
    validated on its own before it replaces `/chat`.

    Args:
        request: ChatRequest with query and session_id
        http_request: Used to reach the compiled workflow graph on app.state
        current_user: Authenticated user from Firebase

    Returns:
        ChatV2Response with the assistant's reply and a few workflow fields
    """
    graph = getattr(http_request.app.state, "graph", None)
    return await controller.chat_with_workflow(
        request.query,
        request.session_id,
        current_user,
        graph,
    )


@router.get("/chat/sessions", response_model=SessionsListResponse)
async def get_user_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """
    Get all chat sessions for the current user
    
    Args:
        limit: Maximum number of sessions (default 20, max 100)
        offset: Pagination offset
        current_user: Authenticated user
        
    Returns:
        List of session summaries with pagination info
    """
    return await controller.get_user_sessions(current_user, limit, offset)


@router.get("/chat/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get full details of a specific chat session
    
    Args:
        session_id: Session identifier
        current_user: Authenticated user
        
    Returns:
        Full session details including messages
    """
    return await controller.get_session_detail(session_id, current_user)


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a chat session
    
    Args:
        session_id: Session identifier
        current_user: Authenticated user
        
    Returns:
        Success message
    """
    return await controller.delete_session(session_id, current_user)
