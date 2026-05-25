import os
import logging
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

#log settings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

#Model Config
MODEL_CONFIGS = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "chat_model": os.getenv("OPENAI_LLM_MODEL"),
        "embedding_model": "text-embedding-3-small"
    }
}

#Default Settings
DEFAULT_LLM_MODEL = "openai"
DEFAULT_TEMPERATURE = 0.6

class LLMInitializationError(Exception):
    """LLM Initialization Error"""
    pass

def initialize_llm(llm_type: str = DEFAULT_LLM_MODEL, temperature: float = DEFAULT_TEMPERATURE)-> ChatOpenAI:
    """
    Initialize a LLM chat model

    Args:
        llm_type (str): LLM types
        temperature (float): temperature

    Returns:
        ChatOpenAI: ChatOpenAI

    Raises:
        LLMInitializationError: If LLM initialization fails
    """

    try:
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(f"Do not support {llm_type}, Avaliable types are {list(MODEL_CONFIGS.keys())}")

        config = MODEL_CONFIGS[llm_type]

        llm_chat = ChatOpenAI(
            api_key = config["api_key"],
            model = config["chat_model"],
            temperature = temperature,
            timeout = 90,
            max_retries = 2
        )

        logger.info(f"Successfully Initialized {llm_type} chat model")
        return llm_chat
    except ValueError as ve:
        logger.error(f"LLM config error: {str(ve)}")
        raise LLMInitializationError(f"LLM config error: {str(ve)}")
    except Exception as ex:
        logger.error(f"LLM initialization failed: {str(ex)}")
        raise LLMInitializationError(f"LLM initialization failed: {str(ex)}")



def initialize_embedding(llm_type: str = DEFAULT_LLM_MODEL)-> OpenAIEmbeddings:
    """
    Initialize an Embedding model

    Args:
        llm_type (str): LLM types

    Returns:
        OpenAIEmbeddings: OpenAIEmbeddings

    Raises:
        LLMInitializationError: If LLM initialization fails
    """

    try:
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(f"Do not support {llm_type}, Avaliable types are {list(MODEL_CONFIGS.keys())}")

        config = MODEL_CONFIGS[llm_type]

        llm_embedding = OpenAIEmbeddings(
            api_key=config["api_key"],
            model=config["embedding_model"],
            deployment=config["embedding_model"],
            check_embedding_ctx_length=False
        )

        logger.info(f"Successfully Initialized {llm_type} chat model")
        return llm_embedding
    except ValueError as ve:
        logger.error(f"LLM config error: {str(ve)}")
        raise LLMInitializationError(f"LLM config error: {str(ve)}")
    except Exception as ex:
        logger.error(f"LLM initialization failed: {str(ex)}")
        raise LLMInitializationError(f"LLM initialization failed: {str(ex)}")


def get_chat_models(llm_type: str = DEFAULT_LLM_MODEL) -> ChatOpenAI:
    """
    return a llm instance, provide default value and error handling

    Args:
        llm_type (str): LLM types

    Returns:
        OpenAIEmbeddings: LLM Instance
    """
    try:
        return initialize_llm(llm_type)
    except LLMInitializationError as e:
        logger.warning(f"LLM initialization failed. Retry with default settings: {str(e)}")
        if llm_type != DEFAULT_LLM_MODEL:
            return initialize_llm(DEFAULT_LLM_MODEL)
        raise


def get_embedding_models(embedding_type: str = DEFAULT_LLM_MODEL) -> OpenAIEmbeddings:
    """
    return an embeddings instance, provide default value and error handling

    Args:
        embedding_type (str): Embedding Model types

    Returns:
        OpenAIEmbeddings: Embedding Model Instance
    """
    try:
        return initialize_embedding(embedding_type)
    except LLMInitializationError as e:
        logger.warning(f"Embedding initialization failed. Retry with default settings: {str(e)}")
        if embedding_type != DEFAULT_LLM_MODEL:
            return initialize_embedding(DEFAULT_LLM_MODEL)
        raise