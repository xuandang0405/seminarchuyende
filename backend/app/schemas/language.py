from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LanguageBase(BaseModel):
    code: str = Field(..., description="Language code (e.g., 'vi', 'en')")
    name: str = Field(..., description="Language name in English (e.g., 'Vietnamese')")
    native_name: str = Field(..., description="Language name in native tongue (e.g., 'Tiếng Việt')")
    is_enabled: bool = True


class LanguageCreate(LanguageBase):
    pass


class LanguageResponse(LanguageBase):
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
