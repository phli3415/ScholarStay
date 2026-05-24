import os
from dotenv import load_dotenv
from typing import List
from langchain_openai import OpenAIEmbeddings
from ..model.houses import Houses
from tortoise.expressions import RawSQL
import dotenv
import logging
from ..utils.llms import initialize_embedding, LLMInitializationError

# Create logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)




# --- Model Loading ---
dotenv.load_dotenv()
embed_model = None
try:
    embed_model = initialize_embedding(os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
except Exception as e:
    logger.warning(f"Could not initialize embedding model: {str(e)}")


def generate_listing_document(listing: Houses) -> str:
    """
    Generates a text document for a single house listing.

    This document is intended to be used for creating semantic embeddings. It combines
    structured data into a natural language format.

    Args:
        listing: A Houses object from the database.

    Returns:
        A descriptive string about the listing.
    """
    document_parts = [
        f"A property located in the city of {listing.city}, {listing.province}, on {listing.street} street, apt.{listing.house_number}.",
        f"The monthly rent is ${listing.monthly_rent:.2f}, and it is located {listing.distance_to_university} kilometer from the university."
    ]

    amenities = []
    not_include = []
    if listing.has_kitchen:
        amenities.append("a kitchen")
    else:
        not_include.append("a kitchen")
    if listing.has_washer:
        amenities.append("a washer")
    else:
        not_include.append("a washer")
    if listing.has_parking:
        amenities.append("a dedicated parking spot")
    else:
        not_include.append("a dedicated parking spot")

    if amenities:
        document_parts.append(f"Key amenities include: {', '.join(amenities)}.")
        if not_include:
            document_parts.append(f"This house doesn't include: {', '.join(not_include)}.")
    
    else:
        document_parts.append("The listing does not specify common amenities like a kitchen, washer, or parking.")

    if listing.is_rented:
        document_parts.append("This house is already rented.")
    else:
        document_parts.append("This house has not be rented.")

    # Append the original, user-provided description for more detail.
    if listing.description:
        document_parts.append(f"Additional details from the provider: {listing.description}")

    logger.info(f"Document embedding created for House with id {listing.id}")

    return " ".join(document_parts)


def create_embedding(text: str) -> list[float]:
    """
    Creates a vector embedding for a given text using the pre-loaded OpenAI model.

    Args:
        text: The text to be embedded.

    Returns:
        A list of floats representing the vector embedding, or an empty list if an error occurs.
    """
    global embed_model
    if embed_model is None:
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        logger.warning(f"Embedding model is missing. Attempting to re-initialize with {model_name}...")
        try:
            embed_model = initialize_embedding(model_name)
        except LLMInitializationError as e:
            logger.error(f"Failed to re-initialize embedding model: {e}, returning empty list")
            embed_model = None
            return []
    
    try:
        embedding_vector = embed_model.embed_query(text)
        return embedding_vector
    except Exception as e:
        logger.error(f"Error creating embedding: {e}, returning empty list")
        return []

async def find_similar_listings(query: str, ids: list[int],   top_k: int = 3) -> List[int]:
    """
    Finds house listings from pgvector with semantic embeddings.

    Args:
        query: The user's natural language query.
        ids: The list of arrays of house ids.
        top_k: The number of similar listings to return.

    Returns:
        A list of descriptive strings about the most relevant listings.
    """

    # Create a vector for the user's query.
    query_vector = create_embedding(query)

    if not query_vector:
        logger.error("Could not create query vector. Returning no listings.")
        return []

    try:
        # Find the most similar House objects from the database.
        similar_listings_objects = await Houses.filter(id__in=ids) \
            .annotate(distance=RawSQL("embedding_vector <=> %s", [str(query_vector)])) \
            .filter(distance__lt=1) \
            .order_by("distance") \
            .limit(top_k) \
            .values_list("id", flat=True)

        if not similar_listings_objects:
            return []


        return similar_listings_objects

    except Exception as e:
        logger.error(f"Error during similarity search: {e}, returning empty list")
        return []
