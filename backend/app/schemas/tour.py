from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

TourStatus = Literal["draft", "published", "archived"]


class TourTranslation(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""


class TourStop(BaseModel):
    poi_id: str
    stop_order: int = Field(..., ge=1)


class TourBase(BaseModel):
    code: str = Field(..., description="Unique Tour code, e.g., 'TOUR_HCM_01'")
    estimated_duration_minutes: int = Field(default=60, ge=0)
    status: TourStatus = "draft"
    translations: Dict[str, TourTranslation] = Field(
        default_factory=dict,
        description="Translations by language code, e.g., {'vi': {'title': '...', 'description': '...'}}"
    )
    stops: List[TourStop] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_stops(self):
        poi_ids = [s.poi_id for s in self.stops]
        if len(poi_ids) != len(set(poi_ids)):
            raise ValueError("All POIs in stops must be unique")
        orders = [s.stop_order for s in self.stops]
        if len(orders) != len(set(orders)):
            raise ValueError("All stop_orders in stops must be unique")
        return self


class TourCreate(TourBase):
    pass


class TourUpdate(BaseModel):
    code: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=0)
    status: Optional[TourStatus] = None
    translations: Optional[Dict[str, TourTranslation]] = None
    stops: Optional[List[TourStop]] = None


class TourResponse(TourBase):
    id: str = Field(..., alias="_id")
    content_revision: int = 1
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
