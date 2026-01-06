"""
House Service
Business logic for house/listing operations
"""

from typing import Optional, List, Dict
from ..model.houses import Houses
from ..repository.house_repository import HouseRepository
from ..repository.user_repository import UserRepository
from ..core.rag_pipeline import generate_listing_document, create_embedding


class HouseService:
    """Service for house business logic"""
    
    def __init__(self):
        self.repository = HouseRepository()
        self.user_repository = UserRepository()
    
    async def get_house_by_id(self, house_id: int) -> Optional[Houses]:
        """
        Get house by ID
        
        Args:
            house_id: ID of the house
            
        Returns:
            Houses object or None if not found
        """
        return await self.repository.get_by_id(house_id)
    
    async def get_all_houses(self, limit: int = 20, offset: int = 0) -> List[Houses]:
        """
        Get all houses with pagination
        
        Args:
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of Houses objects
        """
        return await self.repository.get_all(limit=limit, offset=offset)
    
    async def get_houses_by_owner(self, owner_id: int, limit: int = 20, offset: int = 0) -> List[Houses]:
        """
        Get all houses owned by a user
        
        Args:
            owner_id: ID of the owner
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of Houses objects
        """
        return await self.repository.get_by_owner(owner_id, limit=limit, offset=offset)
    
    async def get_available_houses(self, limit: int = 20, offset: int = 0) -> List[Houses]:
        """
        Get all available houses (not rented)
        
        Args:
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of available Houses objects
        """
        return await self.repository.get_available(limit=limit, offset=offset)
    
    async def create_house(
        self,
        owner_id: int,
        province: str,
        city: str,
        street: str,
        house_number: str,
        monthly_rent: float,
        distance_to_university: float,
        has_kitchen: bool = False,
        has_washer: bool = False,
        has_parking: bool = False,
        is_rented: bool = False,
        description: Optional[str] = None,
    ) -> Houses:
        """
        Create a new house listing, automatically generating the embedding vector.
        
        Args:
            owner_id: ID of the user creating the listing
            province: province of the house
            city: city of the house
            street: street of the house
            house_number: house number
            monthly_rent: monthly rent amount
            distance_to_university: distance to university in km
            has_kitchen: whether the house has a kitchen
            has_washer: whether the house has a washer
            has_parking: whether the house has parking
            is_rented: whether the house is currently rented
            description: description text of the house
            
        Returns:
            Created Houses object
            
        Raises:
            ValueError: if owner does not exist
        """
        # Verify owner exists
        owner = await self.user_repository.get_by_id(owner_id)
        if not owner:
            raise ValueError(f"User with ID {owner_id} does not exist")
        
        # Create a temporary House object to generate the document
        temp_house = Houses(
            owner_id=owner_id, province=province, city=city, street=street,
            house_number=house_number, monthly_rent=monthly_rent,
            distance_to_university=distance_to_university, has_kitchen=has_kitchen,
            has_washer=has_washer, has_parking=has_parking, is_rented=is_rented,
            description=description
        )

        # Generate the document and then the embedding vector
        document = generate_listing_document(temp_house)
        embedding_vector = create_embedding(document)
        
        return await self.repository.create(
            owner_id=owner_id,
            province=province,
            city=city,
            street=street,
            house_number=house_number,
            monthly_rent=monthly_rent,
            distance_to_university=distance_to_university,
            has_kitchen=has_kitchen,
            has_washer=has_washer,
            has_parking=has_parking,
            is_rented=is_rented,
            description=description,
            embedding_vector=embedding_vector, # Use the generated vector
        )
    
    async def update_house(self, house_id: int, **kwargs) -> Optional[Houses]:
        """
        Update house information
        
        Args:
            house_id: ID of the house to update
            **kwargs: fields to update
            
        Returns:
            Updated Houses object or None if house not found
        """
        return await self.repository.update_by_id(house_id, **kwargs)
    
    async def delete_house(self, house_id: int) -> bool:
        """
        Delete house listing
        
        Args:
            house_id: ID of the house to delete
            
        Returns:
            True if deleted successfully, False if house not found
        """
        return await self.repository.delete(house_id)

    async def regenerate_house_embedding(self, house_id: int) -> Optional[Houses]:
        """
        Regenerate the embedding vector for a specific house.

        Args:
            house_id: The ID of the house to update.

        Returns:
            The updated Houses object or None if the house was not found.

        Raises:
            ValueError: if the house does not exist.
        """
        # 1. Fetch the existing house object.
        house = await self.repository.get_by_id(house_id)
        if not house:
            raise ValueError(f"House with ID {house_id} not found")

        # 2. Generate a new document and embedding from its data.
        document = generate_listing_document(house)
        new_embedding_vector = create_embedding(document)

        # 3. Update the house with the new vector.
        if not new_embedding_vector:
            # Handle case where embedding fails
            print(f"Failed to generate embedding for house ID {house_id}. Vector not updated.")
            return house # Return the original object without update

        updated_house = await self.repository.update_by_id(
            house_id, embedding_vector=new_embedding_vector
        )
        
        return updated_house

    async def regenerate_all_embeddings(self) -> Dict[str, int]:
        """
        Regenerate the embedding vector for ALL houses in the database.
        This is a potentially long-running and resource-intensive operation.

        Returns:
            A dictionary with a summary of the operation (succeeded and failed counts).
        """
        # A more robust implementation would use pagination to handle very large datasets.
        # For now, we fetch a large number of records, assuming it covers all listings.
        all_houses = await self.repository.get_all(limit=100000, offset=0)
        
        success_count = 0
        failure_count = 0

        print(f"Starting embedding regeneration for {len(all_houses)} houses...")

        for house in all_houses:
            try:
                document = generate_listing_document(house)
                new_embedding_vector = create_embedding(document)

                if new_embedding_vector:
                    await self.repository.update_by_id(
                        house.id, embedding_vector=new_embedding_vector
                    )
                    success_count += 1
                else:
                    print(f"Failed to generate embedding for house ID {house.id}. Skipping update.")
                    failure_count += 1
            except Exception as e:
                print(f"An error occurred while processing house ID {house.id}: {e}")
                failure_count += 1
        
        summary = {"succeeded": success_count, "failed": failure_count}
        print(f"Embedding regeneration complete. Summary: {summary}")
        return summary

    async def search_houses(
        self,
        province: Optional[str] = None,
        city: Optional[str] = None,
        max_rent: Optional[float] = None,
        min_rent: Optional[float] = None,
        has_kitchen: Optional[bool] = None,
        has_washer: Optional[bool] = None,
        has_parking: Optional[bool] = None,
        is_rented: Optional[bool] = None,
        max_distance: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Houses]:
        """
        Search houses with various filters
        
        Args:
            province: province filter
            city: city filter
            max_rent: maximum rent
            min_rent: minimum rent
            has_kitchen: has kitchen filter
            has_washer: has washer filter
            has_parking: has parking filter
            is_rented: is rented filter
            max_distance: maximum distance to university (km)
            limit: limit of results
            offset: offset for pagination
            
        Returns:
            List of houses matching the filters
        """
        return await self.repository.search(
            province=province,
            city=city,
            max_rent=max_rent,
            min_rent=min_rent,
            has_kitchen=has_kitchen,
            has_washer=has_washer,
            has_parking=has_parking,
            is_rented=is_rented,
            max_distance=max_distance,
            limit=limit,
            offset=offset,
        )
    
    async def get_house_count(self) -> int:
        """
        Get total count of houses
        
        Returns:
            Total number of houses
        """
        return await self.repository.count()
    
    async def get_house_count_by_owner(self, owner_id: int) -> int:
        """
        Get count of houses owned by a user
        
        Args:
            owner_id: ID of the owner
            
        Returns:
            Number of houses owned by the user
        """
        return await self.repository.count_by_owner(owner_id)
    
    async def filter_houses(
        self,
        # String filters
        province: Optional[str] = None,
        city: Optional[str] = None,
        street: Optional[str] = None,
        # Integer range filters
        min_id: Optional[int] = None,
        max_id: Optional[int] = None,
        min_owner_id: Optional[int] = None,
        max_owner_id: Optional[int] = None,
        # Float range filters
        min_monthly_rent: Optional[float] = None,
        max_monthly_rent: Optional[float] = None,
        min_distance_to_university: Optional[float] = None,
        max_distance_to_university: Optional[float] = None,
        # Boolean filters
        has_kitchen: Optional[bool] = None,
        has_washer: Optional[bool] = None,
        has_parking: Optional[bool] = None,
        is_rented: Optional[bool] = None,
        # Pagination
        limit: int = 20,
        offset: int = 0,
    ) -> List[Houses]:
        """
        Filter houses with range filters for int/float fields, exact filters for boolean fields,
        and exact filters for string fields (province, city, street)
        
        Args:
            province: filter by exact province name
            city: filter by exact city name
            street: filter by exact street name
            min_id: minimum house ID
            max_id: maximum house ID
            min_owner_id: minimum owner ID
            max_owner_id: maximum owner ID
            min_monthly_rent: minimum monthly rent
            max_monthly_rent: maximum monthly rent
            min_distance_to_university: minimum distance to university
            max_distance_to_university: maximum distance to university
            has_kitchen: filter by has_kitchen (True/False/None)
            has_washer: filter by has_washer (True/False/None)
            has_parking: filter by has_parking (True/False/None)
            is_rented: filter by is_rented (True/False/None)
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of Houses objects matching the filters
        """
        return await self.repository.filter_houses(
            province=province,
            city=city,
            street=street,
            min_id=min_id,
            max_id=max_id,
            min_owner_id=min_owner_id,
            max_owner_id=max_owner_id,
            min_monthly_rent=min_monthly_rent,
            max_monthly_rent=max_monthly_rent,
            min_distance_to_university=min_distance_to_university,
            max_distance_to_university=max_distance_to_university,
            has_kitchen=has_kitchen,
            has_washer=has_washer,
            has_parking=has_parking,
            is_rented=is_rented,
            limit=limit,
            offset=offset,
        )
