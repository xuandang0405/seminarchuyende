from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LanguageBase(BaseModel):
    name: str = Field(..., description="Language name in English (e.g., 'Vietnamese')")
    native_name: str = Field(..., description="Language name in native tongue (e.g., 'Tiếng Việt')")
    is_enabled: bool = True


class LanguageCreate(LanguageBase):
    code: str = Field(..., description="Language code (e.g., 'vi', 'en')")


class LanguageUpdate(BaseModel):
    name: Optional[str] = None
    native_name: Optional[str] = None
    is_enabled: Optional[bool] = None


class LanguageResponse(LanguageBase):
    id: str = Field(..., alias="_id")
    code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
