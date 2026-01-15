# This file will define the API router for the agent.
# It will expose an endpoint (e.g., /chat) that the front end can call.
# This router will handle incoming requests, invoke the agent, and send back
# the agent's response in streaming format for better UX.

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..dependencies import get_current_user  # Assuming Firebase auth dependency
from ...agent.agent import run_agent

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    session_id: str

@router.post("/chat")
async def chat_with_agent(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Endpoint for chatting with the AI agent.
    Returns a streaming response for real-time updates.
    Messages are persisted to database automatically by run_agent.
    Requires authentication.
    """
    try:
        uid = current_user["uid"]

        async def generate_response():
            # Stream response from agent (persistence handled in run_agent)
            async for chunk in run_agent(request.query, request.session_id, uid):
                yield chunk

        return StreamingResponse(generate_response(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
