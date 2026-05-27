# Import the logging module to record information during program execution
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler

# Import the OS interface module to handle file paths and environment variables
import os
# Import the system module to handle system-related operations, such as exiting the program
import sys
import threading
import time
# Import the UUID module to generate unique identifiers
import uuid
# Import the escape function from the html module to escape HTML special characters
from html import escape
# Import type hinting tools from the typing module
from typing import Literal, Annotated, Sequence, Optional
# Import TypedDict from typing_extensions to define typed dictionaries
from typing_extensions import TypedDict
# Import LangChain's prompt template classes
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
# Import LangChain's base message class
from langchain_core.messages import BaseMessage
# Import the message utility function to append messages
from langgraph.graph.message import add_messages
# Import pre-built tool conditions and tool nodes
from langgraph.prebuilt import tools_condition, ToolNode
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.messages import ToolMessage
# Import definitions for the state graph and START/END nodes
from langgraph.graph import StateGraph, START, END
# Import the base store interface
from langgraph.store.base import BaseStore
# Import the runnable configuration class
from langchain_core.runnables import RunnableConfig
# Import the Postgres store class
from langgraph.store.postgres import PostgresStore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
# Import psycopg2's OperationalError class to capture database connection errors
from psycopg2 import OperationalError
# Import the Postgres checkpointer class
from langgraph.checkpoint.postgres import PostgresSaver
# Import the PostgreSQL connection pool class
from psycopg_pool import ConnectionPool
# Import Pydantic's base model and field definition tools
from pydantic import BaseModel, Field
# Import the custom get_llm function to retrieve the LLM model
from ..utils.llms import get_embedding_models, get_chat_models
# Import the tool configuration module
from ..utils.tools_config import get_tools
# Import the unified Config class
from ..utils.config import Config
from ..utils.Schema import KeyWordsExtractionResult, HouseFilters, HouseRelevanceScore, RecomendationText



#Set logger config.Set LEVEL to DEBUG or INFO

logger = logging.getLogger(__name__)

#Set logging level to DEBUG
logger.setLevel(logging.DEBUG)

logger.handlers = [] #Clear default handlers
handler = ConcurrentRotatingFileHandler(
    Config.LOG_FILE,
    maxBytes=Config.MAX_BYTES,
    backupCount=Config.BACKUP_COUNT
)

handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger.addHandler(handler)


#Message state, use TypedDict for attribute annotation

class MessageState (TypedDict):
    # Define user_input, str, user's original input
    user_input: Annotated[str, "user's original input"]
    # Define Message, BaseMessage List. Use add_messages to handle message append
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Define intent_type, str, to record user intent.
    intent_type: Annotated[Literal["house_recommendation", "chitchat", "out_of_service"], "User_Intent, 'house_recommendation', 'chitchat', or 'out_of_service'"]
    # Define original_requirement, HouseFilters, to record user's original requirement
    original_requirement: Annotated[HouseFilters, "User's original requirement"]
    # Define current_requirement, HouseFilters, to record current requirement
    current_requirement: Annotated[HouseFilters, "current requirement after user's original requirement can not produce valid result"]
    # Define missing_fields_to_clarify: List[str]. Record a list of attribute the AI should clarify.
    missing_fields_to_clarify: Annotated[list[Literal["max_monthly_rent", "max_distance_to_university", "general_preference"]], "Missing important attributes that requires clarification 'max_monthly_rent', 'max_distance_to_university', 'general_preference'"]
    # Define sql_house_ids: List[int]. The id of houses that meet the current_requirement.
    sql_house_ids: Annotated[list[int], "SQL House IDs"]
    # Define top_matched_ids : List[int]. The id of top three houses that best fit user's input.
    sql_house_ids: Annotated[list[int], "House IDs that best fit user's input"]
    # Define rewrite_counter: int, The number of times loosen_requirement has been triggered
    rewrite_counter: Annotated[int, "The number of times loosen_requirement has been triggered"]
    # Define relevance_score: List[str]], whether each houses meet user's requirement.
    relevance_score: Annotated[list[Literal["yes", "No"]], "Whether each houses meet user's requirement"]
    # Define recommendation: List[str]], the reason why each house are recommended.
    recommendation: Annotated[list[str], "why each house are recommended"]


# Define the tool configuration management class to manage tools and their routing configurations
class ToolConfig:
    # Initialization method, takes a list of tools and sets up relevant attributes
    def __init__(self, tools):
        # Store the passed-in tool list into the instance variable self.tools
        self.tools = tools
        # Create a set containing the names of all tools, using a set comprehension to extract the name attribute from tools
        self.tool_names = {tool.name for tool in tools}
        # Call the internal method _build_routing_config to dynamically generate the tool routing configuration and store it in self.tool_routing_config
        self.tool_routing_config = self._build_routing_config(tools)
        # Log an informational message showing the initialized tool names set and routing configuration for debugging and verification
        logger.info(f"Initialized ToolConfig with tools: {self.tool_names}, routing: {self.tool_routing_config}")

    # Internal method to dynamically build the routing configuration based on tool definitions
    def _build_routing_config(self, tools):
        # Create an empty dictionary to store the mapping from tool names to target nodes
        routing_config = {}
        # Iterate through the passed-in tool list to process each tool one by one
        for tool in tools:
            # Convert the tool name to lowercase to ensure case-insensitive matching
            tool_name = tool.name.lower()

            if "find_most_similar_house" in tool_name:
                # If it is a retrieval tool, set its routing target to "result_grading_agent" (requires grading)
                routing_config[tool_name] = "result_grading_agent"
                # Log a debug message
                logger.debug(f"Tool '{tool_name}' routed to 'result_grading_agent' (retrieval tool)")

            elif "filter_houses" in tool_name:
                # Set its routing target to "find_most_similar_house"
                routing_config[tool_name] = "find_most_similar_house"
                # Log a debug message
                logger.debug(f"Tool '{tool_name}' routed to 'find_most_similar_house'")

            else:
                # Set its routing target to "filter_houses"
                routing_config[tool_name] = "filter_houses"
                # Log a debug message
                logger.debug(f"Tool '{tool_name}' routed to 'find_most_similar_house'")

        # Check if the routing configuration dictionary is empty (i.e., no tools were processed)
        if not routing_config:
            # If empty, log a warning message indicating the tool list might be empty or wasn't processed correctly
            logger.warning("No tools provided or routing config is empty")
        # Return the generated routing configuration dictionary
        return routing_config

    # Method to get the tool list, returns the tools stored in the instance
    def get_tools(self):
        # Directly return self.tools, providing an external interface to access the tool list
        return self.tools

    # Method to get the set of tool names, returns the tool_names stored in the instance
    def get_tool_names(self):
        # Directly return self.tool_names, providing an external interface to access the tool names set
        return self.tool_names

    # Method to get the tool routing configuration, returns the dynamically generated routing configuration
    def get_tool_routing_config(self):
        # Directly return self.tool_routing_config, providing an external interface to access the routing configuration
        return self.tool_routing_config




# Custom exception indicating a database connection pool initialization or state abnormality
class ConnectionPoolError(Exception):
    """Custom exception indicating a database connection pool initialization or state abnormality."""

    pass


# Redefine ToolNode to support concurrent handling of tool calls
class ParallelToolNode(ToolNode):
    # Initialization method, inherits from ToolNode, takes the tools list and max threads parameter
    def __init__(self, tools, max_workers: int = 5):
        # Call the parent class ToolNode's initialization method, passing the tools list
        super().__init__(tools)
        # Set the instance variable max_workers, defining the maximum number of worker threads for the pool, defaulting to 5
        self.max_workers = max_workers  # Maximum number of worker threads for the thread pool

    # Define a private method to execute a single tool call, returning a ToolMessage object
    def _run_single_tool(self, tool_call: dict, tool_map: dict) -> ToolMessage:
        """Executes a single tool call."""
        # Use a try-except block to catch exceptions during tool execution
        try:
            # Extract the tool name from the tool_call dictionary
            tool_name = tool_call["name"]
            # Get the corresponding tool instance from the tool_map, returning None if it doesn't exist
            tool = tool_map.get(tool_name)
            # Check if the tool exists; if not, raise a ValueError exception
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            # Call the tool's invoke method, passing the tool arguments, to execute the tool logic
            result = tool.invoke(tool_call["args"])
            # Create and return a ToolMessage object containing the execution result, call ID, and tool name
            return ToolMessage(
                content=str(result), tool_call_id=tool_call["id"], name=tool_name
            )
        # Catch all exceptions, log the error, and return a ToolMessage containing the error information
        except Exception as e:
            # Log an error message for the failed tool execution, including the tool name and exception details
            logger.error(
                f"Error executing tool {tool_call.get('name', 'unknown')}: {e}"
            )
            # Return a ToolMessage object containing the error content for state tracking/updates
            return ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=tool_call["id"],
                name=tool_call.get("name", "unknown"),
            )

    # Define a callable method to allow instances to be called directly, enabling parallel execution of all tool calls
    def __call__(self, state: dict) -> dict:
        """Executes all tool calls in parallel."""
        # Log an informational message indicating that ParallelToolNode has started processing tool calls
        logger.info("ParallelToolNode processing tool calls")
        # Get the last message from the state dictionary
        last_message = state["messages"][-1]
        # Retrieve the tool calls list from the last message, returning an empty list if it doesn't exist
        tool_calls = getattr(last_message, "tool_calls", [])
        # Check if the tool calls list is empty; if so, log a warning and return an empty messages list
        if not tool_calls:
            logger.warning("No tool calls found in state")
            return {"messages": []}

        # Create a mapping dictionary from tool names to tool instances for fast lookups
        tool_map = {tool.name: tool for tool in self.tools}
        # Initialize the results list to store return messages from all tool calls
        results = []

        # Use a thread pool to manage parallel tasks, with max_workers controlling the maximum concurrent threads
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Use a dictionary comprehension to submit all tool call tasks to the thread pool, mapping futures to their tool calls
            future_to_tool = {
                executor.submit(
                    self._run_single_tool, tool_call, tool_map
                ): tool_call
                for tool_call in tool_calls
            }
            # Iterate through completed future objects, gathering results in the order they finish
            for future in as_completed(future_to_tool):
                # Use a try-except block to handle exceptions thrown during thread execution
                try:
                    # Retrieve the result of the future, which is the return message of the tool call
                    result = future.result()
                    # Append the result to the results list
                    results.append(result)
                # Catch thread execution failures, log the error, and append an error message to the results
                except Exception as e:
                    # Log an error message for the failed tool execution along with the exception details
                    logger.error(f"Tool execution failed: {e}")
                    # Retrieve the tool_call associated with the failed task
                    tool_call = future_to_tool[future]
                    # Create a ToolMessage containing the unexpected error info and append it to the results list
                    results.append(
                        ToolMessage(
                            content=f"Unexpected error: {str(e)}",
                            tool_call_id=tool_call["id"],
                            name=tool_call.get("name", "unknown"),
                        )
                    )

        # Log an informational message indicating all tool calls are completed, including the count
        logger.info(f"Completed {len(results)} tool calls")
        # Return the updated state dictionary containing all the tool execution result messages
        return {"messages": results}

# Define a helper function to get the latest question
def get_latest_question(state: MessageState) -> Optional[str]:
    """Safely retrieves the latest user question from the state.

    Args:
        state: The current conversation state containing the message history.

    Returns:
        Optional[str]: The content of the latest question, or None if it cannot
        be retrieved.
    """
    try:
        # Check if the state contains a valid, non-empty list or tuple of messages
        if (
            not state.get("messages")
            or not isinstance(state["messages"], (list, tuple))
            or len(state["messages"]) == 0
        ):
            logger.warning(
                "No valid messages found in state for getting latest question"
            )
            return None

        # Iterate through messages in reverse order to find the most recent HumanMessage (user input)
        for message in reversed(state["messages"]):
            if (
                message.__class__.__name__ == "HumanMessage"
                and hasattr(message, "content")
            ):
                return message.content

        # Return None if no HumanMessage is found
        logger.info("No HumanMessage found in state")
        return None

    except Exception as e:
        logger.error(f"Error getting latest question: {e}")
        return None


# Define a message filtering function for persistent in-thread storage
def filter_messages(messages: list) -> list:
    """Filters the message list to retain only AIMessage and HumanMessage types."""
    # Filter out messages that belong to AIMessage or HumanMessage classes
    filtered = [
        msg
        for msg in messages
        if msg.__class__.__name__ in ["AIMessage", "HumanMessage"]
    ]
    # If the filtered list exceeds N items, return the last N items; otherwise, return the complete filtered list
    return filtered[-5:] if len(filtered) > 5 else filtered

# Define the storage and filtering function for cross-thread persistent storage
def store_memory(question: BaseMessage, config: RunnableConfig, store: BaseStore) -> str:
    """Stores memory information from the user input.

    Args:
        question: The message input by the user.
        config: The runtime configuration.
        store: The data store instance.

    Returns:
        str: A string containing the relevant memory information of the user.
    """
    namespace = ("memories", config["configurable"]["user_id"])
    try:
        # Search for relevant memories in the cross-thread storage database
        memories = store.search(namespace, query=str(question.content))
        user_info = "\n".join([d.value["data"] for d in memories])

        # If the input contains "remember" or memorize, store it as a new memory
        if "memorize" in question.content.lower() or "remember" in question.content.lower():
            memory = escape(question.content)
            store.put(namespace, str(uuid.uuid4()), {"data": memory})
            logger.info(f"Stored memory: {memory}")

        return user_info
    except Exception as e:
        logger.error(f"Error in store_memory: {e}")
        return ""


# Define the function to create a processing chain
def create_chain(llm_chat, template_file: str, structured_output=None):
    """Creates an LLM processing chain, loads the prompt template, and binds the model,
    using caching to avoid duplicate file reads.

    Args:
        llm_chat: The language model instance.
        template_file: The file path to the prompt template.
        structured_output: Optional structured output model.

    Returns:
        Runnable: The configured processing chain.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    # Define static cache and lock (initialized only on the first function call)
    if not hasattr(create_chain, "prompt_cache"):
        # Cache dictionary
        create_chain.prompt_cache = {}
        # Thread lock to ensure thread-safe access to the cache
        create_chain.lock = threading.Lock()

    try:
        # Check cache first without acquiring the lock (lock-free read attempt)
        if template_file in create_chain.prompt_cache:
            prompt_template = create_chain.prompt_cache[template_file]
            logger.info(f"Using cached prompt template for {template_file}")
        else:
            # Protect cache access with a lock
            with create_chain.lock:
                # Double-check if the template was cached by another thread while waiting for the lock
                if template_file not in create_chain.prompt_cache:
                    logger.info(f"Loading and caching prompt template from {template_file}")
                    # Load the prompt template from the file and store it in the cache
                    create_chain.prompt_cache[template_file] = PromptTemplate.from_file(template_file, encoding="utf-8")
                # Retrieve the prompt template from the cache
                prompt_template = create_chain.prompt_cache[template_file]

        # Create a chat prompt template using the template content
        prompt = ChatPromptTemplate.from_messages([("human", prompt_template.template)])
        # Return the combined chain of the prompt template and the LLM, binding structured output if provided
        return prompt | (llm_chat.with_structured_output(structured_output) if structured_output else llm_chat)
    except FileNotFoundError:
        logger.error(f"Template file {template_file} not found")
        raise


# Database retry mechanism: retries up to 3 times with exponential backoff waiting 2-10 seconds.
# This retries only when an OperationalError occurs during database operations.
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(OperationalError))
def test_connection(db_connection_pool: ConnectionPool) -> bool:
    """Tests whether the connection pool is available."""
    with db_connection_pool.getconn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result != (1,):
                raise ConnectionPoolError("Connection pool test query failed; returned an abnormal result.")
    return True


# Define the key_word_extraction_agent Node function
def key_word_extraction_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function that determines whether to clarifications are needed, attract keywords or chitchat based on the user's question.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("key word extraction agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])

        target_tool_name = 'filter_houses'

        # Bind the tools to the LLM
        single_tool = next((tool for tool in tool_config.get_tools() if tool.name == target_tool_name), None)

        # tool not found: raise error
        if not single_tool:
            raise ValueError(f"target tool: '{target_tool_name}' not found.")
        llm_chat_with_tool = llm_chat.bind_tools(single_tool)

        # Create the agent processing chain
        agent_chain = create_chain(llm_chat_with_tool, Config.PROMPT_TEMPLATE_TXT_KEYWORD, HouseFilters)

        # Invoke the agent chain to process the messages
        response = agent_chain.invoke({"question": question, "messages": messages, "userInfo": user_info})
        # logger.info(f"Agent response: {response}")

        # Return the updated conversation state
        return {"filtered value": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in key_word_extraction_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}



# Define the clarification_generation_agent Node function
def clarification_generation_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function generate a clarification message when needed.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("clarification generation agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])

        # Create the agent processing chain
        agent_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_CLARIFICATION)

        # Invoke the agent chain to process the messages
        response = agent_chain.invoke({"question": question, "messages": messages, "userInfo": user_info})
        # logger.info(f"clarification generation agent response: {response}")

        # Return the updated conversation state
        return {"message": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in clarification_generation_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}

# Define the clarification_generation_agent Node function
def clarification_generation_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function generate a clarification message when needed.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("clarification generation agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])

        # Create the agent processing chain
        agent_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_CLARIFICATION)

        # Invoke the agent chain to process the messages
        response = agent_chain.invoke({"question": question, "messages": messages, "userInfo": user_info})
        # logger.info(f"clarification generation agent response: {response}")

        # Return the updated conversation state
        return {"message": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in clarification_generation_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}


# Define the chitchat_agent Node function
def chitchat_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function generate a chitchat message when needed.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("chitchat generation agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])

        # Create the agent processing chain
        agent_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_CHITCHAT)

        # Invoke the agent chain to process the messages
        response = agent_chain.invoke({"question": question, "messages": messages, "userInfo": user_info})
        # logger.info(f"clarification generation agent response: {response}")

        # Return the updated conversation state
        return {"message": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in chitchat_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}


# Define the Grading Node function
def result_grading_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function that compare the similarity of house sources and user input.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("result grading generation agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])

        # Create the agent processing chain
        agent_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_GRADE, HouseRelevanceScore)

        # Invoke the agent chain to process the messages

        # TODO: extract houses from vector DB
        # response = agent_chain.invoke({"messages": messages, "houses": , "userInfo": user_info})
        # logger.info(f"clarification generation agent response: {response}")

        # Return the updated conversation state
        return {"relevance_score": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in result_grading_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}


# Define the recommendation_generation_agent Node function
def recommendation_generation_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function generate a chitchat message when needed.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("chitchat generation agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])

        # Create the agent processing chain
        agent_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_CHITCHAT, RecomendationText)

        # Invoke the agent chain to process the messages
        response = agent_chain.invoke({"question": question, "messages": messages, "userInfo": user_info})
        # logger.info(f"clarification generation agent response: {response}")

        # Return the updated conversation state
        return {"recommendation": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in recommendation_generation_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}

# Define the memory_summarization_agent Node function
def memory_summarization_agent(state: MessageState, config: RunnableConfig, *, store: BaseStore, llm_chat, tool_config: ToolConfig) -> dict:
    """Agent function generate a chitchat message when needed.

    Args:
        state: The current conversation state.
        config: Runtime configuration.
        store: Data store instance.
        llm_chat: The Chat model instance.
        tool_config: Tool configuration parameters.

    Returns:
        dict: The updated conversation state.
    """
    # Log that the agent has started processing the query
    logger.info("chitchat generation agent processing user query")

    # Define the storage namespace using the user ID
    namespace = ("memories", config["configurable"]["user_id"])

    # Try to execute the following block of code
    try:
        # Get the last message, which represents the user's question
        question = state["messages"][-1]
        logger.info(f"agent question:{question}")

        # Retrieve relevant information using custom cross-thread persistent memory storage
        user_info = store_memory(question, config, store)

        # Filter messages using custom in-thread storage logic
        messages = filter_messages(state["messages"])


        # Create the agent processing chain
        agent_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_CHITCHAT)

        # Invoke the agent chain to process the messages
        response = agent_chain.invoke({"question": question, "messages": messages, "userInfo": user_info})
        # logger.info(f"clarification generation agent response: {response}")

        state["messages"] = state["messages"][-3:]
        # Return the updated conversation state
        return {"message": [response]}

    # Catch any exceptions
    except Exception as e:
        # Log the error details
        logger.error(f"Error in memory_summarization_agent processing: {e}")

        # Return an error message state
        return {"messages": [{"role": "system", "content": "An error occurred while processing the request"}]}
