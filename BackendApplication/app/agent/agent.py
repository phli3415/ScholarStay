# This file will contain the core logic for the LangChain Agent.
# It will be responsible for initializing the LLM, loading the tools,
# and running the agent execution chain.

import os
from dotenv import load_dotenv
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

async def run_agent(query: str, session_id: str, user_id: int) -> str:
    """
    Runs the agent with the given user query, session, and user.

    Args:
        query: The user's input query.
        session_id: Unique session identifier.
        user_id: User ID for persistence.

    Returns:
        The agent's response as a string.
    """
    global memory
    # Update memory with session/user
    memory = PersistentChatMemory(session_id=session_id, user_id=user_id, memory_key="chat_history", return_messages=True)

    try:
        response = await agent_executor.ainvoke({"input": query})
        return response["output"]
    except Exception as e:
        return f"Error running agent: {str(e)}"
