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

# memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_tools_agent(llm, tools, prompt)

# agent_executor = AgentExecutor(
#     agent=agent,
#     tools=tools,
#     memory=memory,
#     verbose=True,
#     handle_parsing_errors=True
# )

async def run_agent(query: str, session_id: str, user_id: int) -> AsyncGenerator[str, None]:
    """
    Runs the agent with streaming output using astream_events.
    Yields chunks of the response in real-time.
    Persists detailed messages with tool calls and results to database.
    """
    global memory
    # Create memory instance for this session
    memory = PersistentChatMemory(session_id=session_id, user_id=user_id, memory_key="chat_history", return_messages=True)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True
    )

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

    # current_tool_msg = {
    #     "role": "tool",
    #     "tool_call_id": "",
    #     "content": "",
    #     "timestamp": datetime.now().isoformat(),
    #     "tool_calls": []
    # }
    
    current_tool_call_id = None
    try:
        messages_history = [] 
        current_tool_call_id = None

        async for event in agent_executor.astream_events({"input": query}, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    current_assistant_msg["content"] += content
                    yield content

            elif kind == "on_tool_start":
                t_id = event.get("run_id") 
                t_name = event.get("name")
                t_input = event["data"].get("input")

                current_assistant_msg["tool_calls"].append({
                    "id": t_id,
                    "function": t_name,
                    "args": str(t_input)
                })
                current_tool_call_id = t_id
                
                tool_msg = f"\n[Using tool: {t_name}]\n"
                yield tool_msg

            elif kind == "on_tool_end":
                t_output = event["data"].get("output")
                
                if current_assistant_msg["tool_calls"] or current_assistant_msg["content"]:
                    messages_history.append(current_assistant_msg.copy())
                
                messages_history.append({
                    "role": "tool",
                    "tool_call_id": current_tool_call_id,
                    "content": str(t_output),
                    "timestamp": datetime.now().isoformat()
                })
                
                current_assistant_msg = {
                    "role": "assistant",
                    "content": "",
                    "timestamp": datetime.now().isoformat(),
                    "tool_calls": []
                }
                current_tool_call_id = None

        yield "\n"

        if current_assistant_msg["content"] or current_assistant_msg["tool_calls"]:
            messages_history.append(current_assistant_msg)

        await memory.save_context(
            messages_list=messages_history,
            user_input=query
        )


    except Exception as e:
        error_msg = f"Error running agent: {str(e)}"
        current_assistant_msg["content"] += error_msg
        messages_history.append(current_assistant_msg)
        yield error_msg
        
        # Save error state
        try:
            await memory.save_context(
                messages_list=messages_history,
                user_input=query
            )
        except Exception as save_err:
            print(f"Failed to save context after error: {save_err}")
