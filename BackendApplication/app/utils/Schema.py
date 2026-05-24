from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class HouseFilters(BaseModel):
    province: Optional[str] = Field(default=None, description="name of the province")
    city: Optional[str] = Field(default=None, description="name of the city")
    street: Optional[str] = Field(default=None, description="name of the street")

    max_monthly_rent: Optional[float] = Field(default=None, description="maximum rent the user can afford")
    has_kitchen: Optional[bool] = Field(default=None, description="kitchen needed")
    has_washer: Optional[bool] = Field(default=None, description="laundry washer needed")
    has_parking: Optional[bool] = Field(default=None, description="parking slots needed")
    max_distance_to_university: Optional[float] = Field(default=None, description="the maximum distance to university (in kilometers)")


class KeyWordsExtractionResult(BaseModel):
    intent_type: Literal["house_recommendation", "chitchat", "out_of_service"] = Field(
        description="user's intent verification：house_recommendation, chitchat, out_of_service"
    )
    filters: HouseFilters = Field(description="The filter requirements extracted from user input")
    missing_fields_to_clarify: List[
        Literal["max_monthly_rent", "max_distance_to_university", "general_preference"]] = Field(
        default=[],
        description="If the intent is to rent an apartment(house_recommendation) and the user is missing core key information (such as budget, distance, or general preferences), it needs to be listed here for subsequent follow-up. If no information is missing, leave it as an empty list."


    )