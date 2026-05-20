# This file will contain the data pipeline for RAG.
# It will include functions to:
# 1. Generate a descriptive text document from a house listing object.
# 2. Create a vector embedding from that text document.

import os
from dotenv import load_dotenv
from typing import List
from langchain_openai import OpenAIEmbeddings
from ..model.houses import Houses
from tortoise.expressions import RawSQL
import dotenv


# --- Model Loading (at module level for one-time execution) ---
# We load the model once when the application starts.
# This is much more efficient than loading it on every request.
dotenv.load_dotenv()

try:
    # The LangChain OpenAI client automatically finds the API key from the
    # OPENAI_API_KEY environment variable. We get the model name from env vars
    # for flexibility, with a sensible default.
    embedding_model_name = os.getenv("TEXT_EMBEDDING_MODEL", "text-embedding-3-small")

    embed_model = OpenAIEmbeddings(
        model=embedding_model_name
    )
    print(f"Successfully loaded embedding model: {embedding_model_name}")

except Exception as e:
    print(f"Error loading OpenAI embedding model: {e}")
    embed_model = None


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
    # Start with the core details like location, price, and distance.
    document_parts = [
        f"A property located in the city of {listing.city}, {listing.province}, on {listing.street} street, apt.{listing.house_number}.",
        f"The monthly rent is ${listing.monthly_rent:.2f}, and it is located {listing.distance_to_university} kilometer from the university."
    ]

    # Process boolean fields for amenities into natural language.
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

    # Combine all the information into a single, coherent paragraph.
    return " ".join(document_parts)


def create_embedding(text: str) -> list[float]:
    """
    Creates a vector embedding for a given text using the pre-loaded OpenAI model.

    Args:
        text: The text to be embedded.

    Returns:
        A list of floats representing the vector embedding, or an empty list if an error occurs.
    """
    if not embed_model:
        print("Embedding model is not available. Returning empty list.")
        return []
    
    try:
        # Use the pre-loaded model to create the embedding for the query text
        embedding_vector = embed_model.embed_query(text)
        return embedding_vector
    except Exception as e:
        print(f"Error creating embedding: {e}")
        return []

async def find_similar_listings(query: str, top_k: int = 5) -> List[str]:
    """
    Finds house listings using Tortoise ORM and pgvector, converts them to
    descriptive documents, and returns them.

    Args:
        query: The user's natural language query.
        top_k: The number of similar listings to return.

    Returns:
        A list of descriptive strings about the most relevant listings.
    """
    # 1. Create a vector for the user's query.
    query_vector = create_embedding(query)

    if not query_vector:
        print("Could not create query vector. Returning no listings.")
        return []

    try:
        # 2. Find the most similar House objects from the database using Tortoise ORM.
        # We use RawSQL to access the pgvector `<->` (L2 distance) operator.
        similar_listings_objects = await Houses.all() \
            .annotate(distance=RawSQL("embedding_vector <=> %s", [str(query_vector)])) \
            .filter(distance__lt=1) \
            .order_by("distance") \
            .limit(top_k)

        if not similar_listings_objects:
            return []

        # 3. Convert the House objects into descriptive document strings.
        listing_documents = [generate_listing_document(listing) for listing in similar_listings_objects]

        return listing_documents

    except Exception as e:
        print(f"Error during similarity search: {e}")
        return []
