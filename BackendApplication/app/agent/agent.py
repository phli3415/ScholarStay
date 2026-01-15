# This file will contain the core logic for the LangChain Agent.
# It will be responsible for initializing the LLM, loading the tools,
# and running the agent execution chain.

import os
from dotenv import load_dotenv
from typing import AsyncGenerator
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from .persistent_memory import PersistentChatMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from .prompts import SYSTEM_PROMPT, HUMAN_PROMPT_TEMPLATE
from .agent_tools import (
    search_listings,
    compare_listings,
    get_listing_details,
    structured_search,
    advanced_filter,
    compare_listings_by_address
)

load_dotenv()

llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini") 
llm = ChatOpenAI(model=llm_model, temperature=0.1) 

tools = [
    search_listings,
    compare_listings,
    get_listing_details,
    structured_search,
    advanced_filter,
    compare_listings_by_address
]

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_tools_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True
)

async def run_agent(query: str, session_id: str, user_uid: int) -> AsyncGenerator[str, None]:
    """
    Runs the agent with streaming output using astream_events.
    Yields chunks of the response in real-time.
    Persists detailed messages with tool calls and results to database.
    """
    global memory
    # Create memory instance for this session
    memory = PersistentChatMemory(session_id=session_id, user_id=user_uid, memory_key="chat_history", return_messages=True)

    # Collect detailed message history with tool calls
    messages_history = [
        {
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # Track current assistant message with tool calls
    current_assistant_msg = {
        "role": "assistant",
        "content": "",
        "timestamp": datetime.now().isoformat(),
        "tool_calls": []
    }
    
    current_tool_call_id = None

    try:
        async for event in agent_executor.astream_events({"input": query}, version="v2"):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    current_assistant_msg["content"] += chunk.content
                    yield chunk.content
                    
                # Capture tool calls from chunk
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        current_assistant_msg["tool_calls"].append({
                            "id": tool_call.get("id", ""),
                            "function": tool_call.get("function", ""),
                            "args": str(tool_call.get("args", ""))
                        })
                        
            elif event["event"] == "on_tool_start":
                # Record tool call
                tool_name = event.get("name", "")
                current_tool_call_id = event.get("data", {}).get("id", "")
                
                tool_msg = f"\n[Using tool: {tool_name}]\n"
                current_assistant_msg["content"] += tool_msg
                yield tool_msg
                
            elif event["event"] == "on_tool_end":
                # Record tool result
                tool_result = event.get("data", {}).get("output", "")
                
                if current_tool_call_id:
                    # Add assistant message with tool calls
                    if current_assistant_msg["content"]:
                        messages_history.append(current_assistant_msg.copy())
                    
                    # Add tool result message
                    tool_result_msg = {
                        "role": "tool",
                        "tool_call_id": current_tool_call_id,
                        "content": str(tool_result),
                        "timestamp": datetime.now().isoformat()
                    }
                    messages_history.append(tool_result_msg)
                    
                    # Reset for next message
                    current_assistant_msg = {
                        "role": "assistant",
                        "content": "",
                        "timestamp": datetime.now().isoformat(),
                        "tool_calls": []
                    }
                    current_tool_call_id = None

        yield "\n"
        
        # Add final assistant message
        if current_assistant_msg["content"] or current_assistant_msg["tool_calls"]:
            messages_history.append(current_assistant_msg)
        
        # Save all messages with tool information
        await memory.save_context(
            inputs={"input": query},
            outputs={"output": ""},
            messages=messages_history
        )

    except Exception as e:
        error_msg = f"Error running agent: {str(e)}"
        current_assistant_msg["content"] += error_msg
        messages_history.append(current_assistant_msg)
        yield error_msg
        
        # Save error state
        try:
            await memory.save_context(
                inputs={"input": query},
                outputs={"output": error_msg},
                messages=messages_history
            )
        except Exception as save_err:
            print(f"Failed to save context after error: {save_err}")
