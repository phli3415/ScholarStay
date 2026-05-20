# This file will define the tools that the LangChain Agent can use.
# These tools will be functions that perform specific actions, such as
# searching for listings or comparing them.

import json
from typing import List, Dict, Any
from langchain.tools import tool
from ..core.rag_pipeline import create_embedding, find_similar_listings, generate_listing_document
from ..service.house_service import HouseService
from ..repository.house_repository import HouseRepository
from ..model.houses import Houses

house_service = HouseService(HouseRepository())

@tool
def search_listings(house_json: str, int top_k = 3) -> str:
    """
    Searches for house listings based on a house JSON description.
    The JSON should represent the user's ideal house preferences.

    Args:
        house_json: A JSON string describing the ideal house, e.g.,
                    '{"city': 'Toronto', 'province': 'Ontario', 'monthly_rent': 1000, 'distance_to_university': 1.0, 'has_kitchen': true, ...}'

    Returns:
        A JSON string of matching listings: [{"id": int, "description": str, "price": float, "distance": float}, ...]
    """
    try:
        # Parse the house JSON
        ideal_house = json.loads(house_json)

        # Create a temporary Houses object for document generation
        temp_house = Houses(**ideal_house)

        # Generate document and embedding
        document = generate_listing_document(temp_house)
        query_vector = create_embedding(document)

        if not query_vector:
           return json.dumps([])

        # Find similar listings
        similar_docs = await find_similar_listings(document, top_k) 


        # Return docs as list of strings in JSON
        return json.dumps(similar_docs)

    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def compare_listings(id1: int, id2: int) -> str:
    """
    Compares two house listings by their IDs.

    Args:
        id1: ID of the first listing.
        id2: ID of the second listing.

    Returns:
        A JSON string with comparison details: {"comparison": str, "details": {"listing1": {...}, "listing2": {...}}}
    """
    try:
        # Get listings from service
        listing1 = house_service.get_by_id(id1)
        listing2 = house_service.get_by_id(id2)

        if not listing1 or not listing2:
            return json.dumps({"error": "One or both listings not found"})

        # Generate comparison text
        comparison = f"Listing {id1}: {listing1.city}, ${listing1.monthly_rent}, {listing1.distance_to_university}km, amenities: kitchen={listing1.has_kitchen}, washer={listing1.has_washer}, parking={listing1.has_parking}. " \
                     f"Listing {id2}: {listing2.city}, ${listing2.monthly_rent}, {listing2.distance_to_university}km, amenities: kitchen={listing2.has_kitchen}, washer={listing2.has_washer}, parking={listing2.has_parking}. " \
                     f"Differences: Price diff ${listing1.monthly_rent - listing2.monthly_rent}, Distance diff {listing1.distance_to_university - listing2.distance_to_university}km."

        details = {
            "listing1": {
                "id": listing1.id,
                "city": listing1.city,
                "price": listing1.monthly_rent,
                "distance": listing1.distance_to_university,
                "has_kitchen": listing1.has_kitchen,
                "has_washer": listing1.has_washer,
                "has_parking": listing1.has_parking
            },
            "listing2": {
                "id": listing2.id,
                "city": listing2.city,
                "price": listing2.monthly_rent,
                "distance": listing2.distance_to_university,
                "has_kitchen": listing2.has_kitchen,
                "has_washer": listing2.has_washer,
                "has_parking": listing2.has_parking
            }
        }

        return json.dumps({"comparison": comparison, "details": details})

    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_listing_details(house_id: int) -> str:
    """
    Retrieves detailed information about a specific house listing by ID.

    Args:
        house_id: The ID of the house listing.

    Returns:
        A JSON string with the listing details or an error message.
    """
    try:
        listing = house_service.get_house_by_id(house_id)
        if not listing:
            return json.dumps({"error": "Listing not found"})

        details = {
            "id": listing.id,
            "owner_id": listing.owner_id,
            "province": listing.province,
            "city": listing.city,
            "street": listing.street,
            "house_number": listing.house_number,
            "monthly_rent": listing.monthly_rent,
            "distance_to_university": listing.distance_to_university,
            "has_kitchen": listing.has_kitchen,
            "has_washer": listing.has_washer,
            "has_parking": listing.has_parking,
            "is_rented": listing.is_rented,
            "description": listing.description,
            "landlord_phone_number": listing.landlord_phone_number
        }
        return json.dumps(details)

    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def structured_search(filters_json: str) -> str:
    """
    Searches for house listings using structured filters from house_service.search_houses.

    Args:
        filters_json: A JSON string with filters, e.g.,
                      '{"province': 'Ontario', 'city': 'Toronto', 'max_rent': 1000, 'has_kitchen': true, 'max_distance': 2.0, 'limit': 5}'

    Returns:
        A JSON string of matching listings: [{"id": int, "city": str, "price": float, ...}, ...]
    """
    try:
        filters = json.loads(filters_json)
        listings = house_service.search_houses(**filters)
        results = [
            {
                "id": l.id,
                "city": l.city,
                "price": l.monthly_rent,
                "distance": l.distance_to_university,
                "has_kitchen": l.has_kitchen,
                "has_washer": l.has_washer,
                "has_parking": l.has_parking,
                "is_rented": l.is_rented
            } for l in listings
        ]
        return json.dumps(results)

    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def advanced_filter(filters_json: str) -> str:
    """
    Filters house listings using advanced range filters from house_service.filter_houses.

    Args:
        filters_json: A JSON string with filters, e.g.,
                      '{"province': 'Ontario', 'min_monthly_rent': 500, 'max_monthly_rent': 1000, 'has_kitchen': true, 'limit': 5}'

    Returns:
        A JSON string of matching listings: [{"id": int, "city": str, "price": float, ...}, ...]
    """
    try:
        filters = json.loads(filters_json)
        listings = house_service.filter_houses(**filters)
        results = [
            {
                "id": l.id,
                "city": l.city,
                "price": l.monthly_rent,
                "distance": l.distance_to_university,
                "has_kitchen": l.has_kitchen,
                "has_washer": l.has_washer,
                "has_parking": l.has_parking,
                "is_rented": l.is_rented
            } for l in listings
        ]
        return json.dumps(results)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def compare_listings_by_address(address1_json: str, address2_json: str) -> str:
    """
    Compares two house listings by their addresses (province, city, street, house_number).

    Args:
        address1_json: A JSON string for the first address, e.g.,
                       '{"province': 'Ontario', 'city': 'Toronto', 'street': 'Main St', 'house_number': '101'}'
        address2_json: A JSON string for the second address, similar format.

    Returns:
        A JSON string with comparison details, or an error if addresses not found.
    """
    try:
        addr1 = json.loads(address1_json)
        addr2 = json.loads(address2_json)

        # Find listings by address using filter_houses (get all on the street)
        listing1_results = house_service.filter_houses(
            province=addr1.get("province"),
            city=addr1.get("city"),
            street=addr1.get("street"),
            limit = 150
        )
        listing1 = None
        for l in listing1_results:
            if l.house_number == addr1.get("house_number"):
                listing1 = l
                break

        listing2_results = house_service.filter_houses(
            province=addr2.get("province"),
            city=addr2.get("city"),
            street=addr2.get("street")
            limit = 150
        )
        listing2 = None
        for l in listing2_results:
            if l.house_number == addr2.get("house_number"):
                listing2 = l
                break

        if not listing1 or not listing2:
            return json.dumps({"error": "One or both addresses not found"})

        # Generate comparison text
        comparison = f"Listing at {listing1.city}, {listing1.street} {listing1.house_number}: ${listing1.monthly_rent}, {listing1.distance_to_university}km, amenities: kitchen={listing1.has_kitchen}, washer={listing1.has_washer}, parking={listing1.has_parking}. " \
                     f"Listing at {listing2.city}, {listing2.street} {listing2.house_number}: ${listing2.monthly_rent}, {listing2.distance_to_university}km, amenities: kitchen={listing2.has_kitchen}, washer={listing2.has_washer}, parking={listing2.has_parking}. " \
                     f"Differences: Price diff ${abs(listing1.monthly_rent - listing2.monthly_rent)}, Distance diff {abs(listing1.distance_to_university - listing2.distance_to_university)}km."

        details = {
            "listing1": {
                "id": listing1.id,
                "province": listing1.province,
                "city": listing1.city,
                "street": listing1.street,
                "house_number": listing1.house_number,
                "price": listing1.monthly_rent,
                "distance": listing1.distance_to_university,
                "has_kitchen": listing1.has_kitchen,
                "has_washer": listing1.has_washer,
                "has_parking": listing1.has_parking
            },
            "listing2": {
                "id": listing2.id,
                "province": listing2.province,
                "city": listing2.city,
                "street": listing2.street,
                "house_number": listing2.house_number,
                "price": listing2.monthly_rent,
                "distance": listing2.distance_to_university,
                "has_kitchen": listing2.has_kitchen,
                "has_washer": listing2.has_washer,
                "has_parking": listing2.has_parking
            }
        }

        return json.dumps({"comparison": comparison, "details": details})

    except Exception as e:
        return json.dumps({"error": str(e)})