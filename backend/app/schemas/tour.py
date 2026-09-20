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
    price_amount: int = Field(default=0, ge=0, description="Giá tour bằng số nguyên VND")
    currency: str = Field(default="VND")
    pricing_version: int = Field(default=1)
    is_purchasable: bool = Field(default=False, description="Cờ mở bán tour")
    preview_enabled: bool = Field(default=True, description="Cho phép nghe thử 1 POI")
    preview_poi_ids: List[str] = Field(default_factory=list, description="Danh sách POI được phép nghe thử")

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
    price_amount: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = None
    is_purchasable: Optional[bool] = None
    preview_enabled: Optional[bool] = None
    preview_poi_ids: Optional[List[str]] = None


class TourPricingUpdateRequest(BaseModel):
    price_amount: Optional[int] = Field(None, ge=0, description="Giá bán mới của tour (VND)")
    price_vnd: Optional[int] = Field(None, ge=0)
    currency: str = Field(default="VND")
    is_purchasable: Optional[bool] = Field(None, description="Mở bán hoặc đóng bán")
    for_sale: Optional[bool] = None
    is_paid: Optional[bool] = None
    preview_enabled: bool = Field(default=True, description="Cho phép nghe thử")
    preview_poi_ids: Optional[List[str]] = Field(default=None, description="Danh sách POI nghe thử")

    @model_validator(mode="before")
    @classmethod
    def normalize_pricing_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "price_amount" not in data and "price_vnd" in data:
                data["price_amount"] = data["price_vnd"]
            if "price_amount" not in data and data.get("is_paid") is False:
                data["price_amount"] = 0
            if data.get("price_amount") is None:
                data["price_amount"] = 0

            if "is_purchasable" not in data:
                if "for_sale" in data:
                    data["is_purchasable"] = data["for_sale"]
                elif "is_paid" in data:
                    data["is_purchasable"] = data["is_paid"]
                else:
                    data["is_purchasable"] = True
        return data


class TourResponse(TourBase):
    id: str = Field(..., alias="_id")
    content_revision: int = 1
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }

