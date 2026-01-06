"""
House Controller
Handles HTTP requests/responses for house/listing operations
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from ..service.house_service import HouseService
from ..model.houses import Houses

router = APIRouter(prefix="/houses", tags=["houses"])
service = HouseService()


# Request Models
class HouseCreateRequest(BaseModel):
    owner_id: int
    province: str
    city: str
    street: str
    house_number: str
    monthly_rent: float
    distance_to_university: float
    has_kitchen: bool = False
    has_washer: bool = False
    has_parking: bool = False
    is_rented: bool = False
    description: Optional[str] = None


class HouseUpdateRequest(BaseModel):
    province: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    monthly_rent: Optional[float] = None
    distance_to_university: Optional[float] = None
    has_kitchen: Optional[bool] = None
    has_washer: Optional[bool] = None
    has_parking: Optional[bool] = None
    is_rented: Optional[bool] = None
    description: Optional[str] = None
    embedding_vector: Optional[str] = None


# Response Models
class HouseResponse(BaseModel):
    id: int
    owner_id: int
    province: str
    city: str
    street: str
    house_number: str
    monthly_rent: float
    distance_to_university: float
    has_kitchen: bool
    has_washer: bool
    has_parking: bool
    is_rented: bool
    description: Optional[str]
    embedding_vector: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


def house_to_response(house: Houses) -> HouseResponse:
    """Convert Houses model to HouseResponse"""
    return HouseResponse(
        id=house.id,
        owner_id=house.owner_id,
        province=house.province,
        city=house.city,
        street=house.street,
        house_number=house.house_number,
        monthly_rent=float(house.monthly_rent),
        distance_to_university=float(house.distance_to_university),
        has_kitchen=house.has_kitchen,
        has_washer=house.has_washer,
        has_parking=house.has_parking,
        is_rented=house.is_rented,
        description=house.description,
        embedding_vector=house.embedding_vector,
        created_at=house.created_at.isoformat(),
        updated_at=house.updated_at.isoformat()
    )


# Endpoints
@router.post("/", response_model=HouseResponse, status_code=status.HTTP_201_CREATED)
async def create_house(house_data: HouseCreateRequest):
    """Create a new house listing"""
    try:
        house = await service.create_house(
            owner_id=house_data.owner_id,
            province=house_data.province,
            city=house_data.city,
            street=house_data.street,
            house_number=house_data.house_number,
            monthly_rent=house_data.monthly_rent,
            distance_to_university=house_data.distance_to_university,
            has_kitchen=house_data.has_kitchen,
            has_washer=house_data.has_washer,
            has_parking=house_data.has_parking,
            is_rented=house_data.is_rented,
            description=house_data.description,
        )
        return house_to_response(house)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{house_id}", response_model=HouseResponse)
async def get_house(house_id: int):
    """Get house by ID"""
    house = await service.get_house_by_id(house_id)
    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"House with ID {house_id} not found"
        )
    return house_to_response(house)


@router.get("/", response_model=List[HouseResponse])
async def get_all_houses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get all houses with pagination"""
    houses = await service.get_all_houses(limit=limit, offset=offset)
    return [house_to_response(house) for house in houses]


@router.get("/owner/{owner_id}", response_model=List[HouseResponse])
async def get_houses_by_owner(
    owner_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get all houses owned by a user"""
    houses = await service.get_houses_by_owner(owner_id, limit=limit, offset=offset)
    return [house_to_response(house) for house in houses]


@router.get("/available/list", response_model=List[HouseResponse])
async def get_available_houses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get all available houses (not rented)"""
    houses = await service.get_available_houses(limit=limit, offset=offset)
    return [house_to_response(house) for house in houses]


@router.get("/search/list", response_model=List[HouseResponse])
async def search_houses(
    province: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    max_rent: Optional[float] = Query(default=None, ge=0),
    min_rent: Optional[float] = Query(default=None, ge=0),
    has_kitchen: Optional[bool] = Query(default=None),
    has_washer: Optional[bool] = Query(default=None),
    has_parking: Optional[bool] = Query(default=None),
    is_rented: Optional[bool] = Query(default=None),
    max_distance: Optional[float] = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Search houses with various filters"""
    houses = await service.search_houses(
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
    return [house_to_response(house) for house in houses]


@router.put("/{house_id}", response_model=HouseResponse)
async def update_house(house_id: int, house_data: HouseUpdateRequest):
    """Update house information"""
    update_dict = house_data.dict(exclude_unset=True)
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    house = await service.update_house(house_id, **update_dict)
    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"House with ID {house_id} not found"
        )
    return house_to_response(house)


@router.delete("/{house_id}", status_code=status.HTTP_200_OK)
async def delete_house(house_id: int):
    """Delete house listing"""
    success = await service.delete_house(house_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"House with ID {house_id} not found"
        )
    return {"message": "House deleted successfully"}


@router.get("/filter/list", response_model=List[HouseResponse])
async def filter_houses(
    # String filters
    province: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    street: Optional[str] = Query(default=None),
    # Integer range filters
    min_id: Optional[int] = Query(default=None, ge=0),
    max_id: Optional[int] = Query(default=None, ge=0),
    min_owner_id: Optional[int] = Query(default=None, ge=0),
    max_owner_id: Optional[int] = Query(default=None, ge=0),
    # Float range filters
    min_monthly_rent: Optional[float] = Query(default=None, ge=0),
    max_monthly_rent: Optional[float] = Query(default=None, ge=0),
    min_distance_to_university: Optional[float] = Query(default=None, ge=0),
    max_distance_to_university: Optional[float] = Query(default=None, ge=0),
    # Boolean filters
    has_kitchen: Optional[bool] = Query(default=None),
    has_washer: Optional[bool] = Query(default=None),
    has_parking: Optional[bool] = Query(default=None),
    is_rented: Optional[bool] = Query(default=None),
    # Pagination
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Filter houses with range filters for int/float fields, exact filters for boolean fields,
    and exact filters for string fields (province, city, street).
    All filter parameters are optional (can be null). 
    For int/float fields, you can specify min and/or max values.
    For boolean fields, you can specify True, False, or None (no filter).
    For string fields (province, city, street), you can specify an exact string value.
    """
    houses = await service.filter_houses(
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
    return [house_to_response(house) for house in houses]