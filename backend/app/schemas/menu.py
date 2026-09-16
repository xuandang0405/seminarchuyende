"""Pydantic v2 schemas for MenuItem collection.

Adheres to Section 25 ERD Baseline.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = ""
    price: int = Field(..., ge=0, description="Price in lowest integer unit (VND)")
    currency: str = Field(default="VND")
    image_url: Optional[str] = None
    is_active: bool = Field(default=True)


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    expected_version: Optional[int] = None


class MenuItemResponse(BaseModel):
    id: str = Field(..., alias="_id")
    poi_id: str
    name: str
    description: Optional[str] = ""
    price: int
    currency: str
    image_url: Optional[str] = None
    is_active: bool
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}
