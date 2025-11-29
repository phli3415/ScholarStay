"""
House Repository
Handles all database operations related to Houses model
"""

from typing import Optional, List
from ..model.houses import Houses


class HouseRepository:
    """Repository for Houses model operations"""
    
    @staticmethod
    async def get_by_id(house_id: int) -> Optional[Houses]:
        """
        Get house by ID
        
        Args:
            house_id: ID of the house
            
        Returns:
            Houses object or None if not found
        """
        return await Houses.get_or_none(id=house_id)
    
    @staticmethod
    async def get_all(limit: int = 100, offset: int = 0) -> List[Houses]:
        """
        Get all houses with pagination
        
        Args:
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of Houses objects
        """
        return await Houses.all().limit(limit).offset(offset)
    
    @staticmethod
    async def get_by_owner(owner_id: int, limit: int = 100, offset: int = 0) -> List[Houses]:
        """
        Get all houses owned by a user
        
        Args:
            owner_id: ID of the owner
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of Houses objects
        """
        return await Houses.filter(owner_id=owner_id).limit(limit).offset(offset)
    
    @staticmethod
    async def get_available(limit: int = 100, offset: int = 0) -> List[Houses]:
        """
        Get all available houses (not rented)
        
        Args:
            limit: maximum number of houses to return
            offset: offset for pagination
            
        Returns:
            List of available Houses objects
        """
        return await Houses.filter(is_rented=False).limit(limit).offset(offset)
    
    @staticmethod
    async def create(
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
        embedding_vector: Optional[str] = None,
    ) -> Houses:
        """
        Create a new house listing
        
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
            embedding_vector: vector representation for RAG
            
        Returns:
            Created Houses object
        """
        return await Houses.create(
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
            embedding_vector=embedding_vector,
        )
    
    @staticmethod
    async def update(house: Houses, **kwargs) -> Houses:
        """
        Update house fields
        
        Args:
            house: Houses object to update
            **kwargs: fields to update
            
        Returns:
            Updated Houses object
        """
        for key, value in kwargs.items():
            if hasattr(house, key):
                setattr(house, key, value)
        await house.save()
        return house
    
    @staticmethod
    async def update_by_id(house_id: int, **kwargs) -> Optional[Houses]:
        """
        Update house by ID
        
        Args:
            house_id: ID of the house to update
            **kwargs: fields to update
            
        Returns:
            Updated Houses object or None if not found
        """
        house = await HouseRepository.get_by_id(house_id)
        if not house:
            return None
        return await HouseRepository.update(house, **kwargs)
    
    @staticmethod
    async def delete(house_id: int) -> bool:
        """
        Delete house by ID
        
        Args:
            house_id: ID of the house to delete
            
        Returns:
            True if deleted, False if house not found
        """
        house = await Houses.get_or_none(id=house_id)
        if house:
            await house.delete()
            return True
        return False
    
    @staticmethod
    async def search(
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
        query = Houses.all()
        
        if province:
            query = query.filter(province=province)
        if city:
            query = query.filter(city=city)
        if max_rent:
            query = query.filter(monthly_rent__lte=max_rent)
        if min_rent:
            query = query.filter(monthly_rent__gte=min_rent)
        if has_kitchen is not None:
            query = query.filter(has_kitchen=has_kitchen)
        if has_washer is not None:
            query = query.filter(has_washer=has_washer)
        if has_parking is not None:
            query = query.filter(has_parking=has_parking)
        if is_rented is not None:
            query = query.filter(is_rented=is_rented)
        if max_distance:
            query = query.filter(distance_to_university__lte=max_distance)
        
        return await query.limit(limit).offset(offset).all()
    
    @staticmethod
    async def count() -> int:
        """
        Get total count of houses
        
        Returns:
            Total number of houses
        """
        return await Houses.all().count()
    
    @staticmethod
    async def count_by_owner(owner_id: int) -> int:
        """
        Get count of houses owned by a user
        
        Args:
            owner_id: ID of the owner
            
        Returns:
            Number of houses owned by the user
        """
        return await Houses.filter(owner_id=owner_id).count()

