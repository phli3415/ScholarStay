"""
House Controller
Handles HTTP requests/responses for house/listing operations
"""

from fastapi import APIRouter, HTTPException, status, Query, File, UploadFile, Form, Depends
from pydantic import BaseModel, ValidationError
from typing import Optional, List
import base64
import json

from ..service.house_service import HouseService
from ..model.houses import Houses
from ..model.user import User
from ..core.firebase_auth import get_current_user

router = APIRouter(prefix="/houses", tags=["Houses"])
service = HouseService()


# Request Models
class HouseCreateRequest(BaseModel):
    # owner_id is removed. It will be determined from the authenticated user.
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
    landlord_phone_number: Optional[str] = None
    embedding_vector: Optional[str] = None


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
    landlord_phone_number: Optional[str] = None
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
    landlord_phone_number: Optional[str]
    image_data: Optional[str]  # Base64 encoded image
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

def house_to_response(house: Houses) -> HouseResponse:
    """Convert Houses model to HouseResponse"""
    image_data_b64 = None
    if house.image_data:
        image_data_b64 = base64.b64encode(house.image_data).decode('utf-8')

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
        landlord_phone_number=house.landlord_phone_number,
        embedding_vector=None, # embedding_vector is not sent to the client
        image_data=image_data_b64,
        created_at=house.created_at.isoformat(),
        updated_at=house.updated_at.isoformat()
    )


# Endpoints
@router.post("/", response_model=HouseResponse, status_code=status.HTTP_201_CREATED)
async def create_house(
    current_user: User = Depends(get_current_user),
    house_data_str: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Create a new house listing. User must be authenticated."""
    try:
        house_data_dict = json.loads(house_data_str)
        house_data = HouseCreateRequest(**house_data_dict)
        image_bytes = await image.read() if image else None

        # owner_id is now taken from the authenticated user
        house = await service.create_house(
            owner_id=current_user.id,  # Securely set owner_id
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
            landlord_phone_number=house_data.landlord_phone_number,
            embedding_vector=house_data.embedding_vector,
            image_data=image_bytes
        )
        return house_to_response(house)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{house_id}", response_model=HouseResponse)
async def update_house(
    house_id: int,
    current_user: User = Depends(get_current_user),
    house_data_str: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Update a house listing. User must be the owner."""
    # First, check if the house exists and if the user is the owner
    existing_house = await service.get_house_by_id(house_id)
    if not existing_house:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"House with ID {house_id} not found")
    if existing_house.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this house")

    try:
        update_data_dict = json.loads(house_data_str)
        house_data = HouseUpdateRequest(**update_data_dict)
        update_dict = house_data.dict(exclude_unset=True)
        if image:
            update_dict['image_data'] = await image.read()

        if not update_dict and not image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        house = await service.update_house(house_id, **update_dict)
        if not house:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"House with ID {house_id} not found during update"
            )
        return house_to_response(house)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{house_id}", status_code=status.HTTP_200_OK)
async def delete_house(house_id: int, current_user: User = Depends(get_current_user)):
    """Delete a house listing. User must be the owner."""
    # First, check if the house exists and if the user is the owner
    existing_house = await service.get_house_by_id(house_id)
    if not existing_house:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"House with ID {house_id} not found")
    if existing_house.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this house")

    success = await service.delete_house(house_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"House with ID {house_id} not found during deletion")
    return {"message": "House deleted successfully"}

# --- Public, non-authenticated endpoints ---

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

@router.get("/filter/list", response_model=List[HouseResponse])
async def filter_houses(
    province: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    street: Optional[str] = Query(default=None),
    min_id: Optional[int] = Query(default=None, ge=0),
    max_id: Optional[int] = Query(default=None, ge=0),
    min_owner_id: Optional[int] = Query(default=None, ge=0),
    max_owner_id: Optional[int] = Query(default=None, ge=0),
    min_monthly_rent: Optional[float] = Query(default=None, ge=0),
    max_monthly_rent: Optional[float] = Query(default=None, ge=0),
    min_distance_to_university: Optional[float] = Query(default=None, ge=0),
    max_distance_to_university: Optional[float] = Query(default=None, ge=0),
    has_kitchen: Optional[bool] = Query(default=None),
    has_washer: Optional[bool] = Query(default=None),
    has_parking: Optional[bool] = Query(default=None),
    is_rented: Optional[bool] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Filter houses with various filters"""
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

@router.get("/filter/count", response_model=int)
async def count_filtered_houses(
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
):
    """
    Count houses with range filters for int/float fields, exact filters for boolean fields,
    and exact filters for string fields (province, city, street).
    """
    return await service.count_filtered_houses(
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
    )
