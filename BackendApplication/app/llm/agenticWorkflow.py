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
from ..utils.llms import get_llm
# Import the tool configuration module
from ..utils.tools_config import get_tools
# Import the unified Config class
from ..utils.config import Config