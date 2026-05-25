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
from ..utils.Schema import KeyWordsExtractionResult, HouseFilters


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
    message: Annotated[Sequence[BaseMessage], add_messages]
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


