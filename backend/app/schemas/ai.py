from typing import List, Optional
from pydantic import BaseModel, Field


class AINarrationRequest(BaseModel):
    poi_name: str
    category: str = "food"
    address: Optional[str] = None
    specialties: List[str] = Field(default_factory=list, description="Notable dishes or historic features")
    tone: str = "engaging"  # "historic", "engaging", "concise", "humorous"
    weather: Optional[str] = None  # e.g., "sunny", "rainy", "cool evening"
    language_code: str = "vi"


class AINarrationResponse(BaseModel):
    title: str
    description: str
    narration_text: str
    suggested_voice: str
    weather_context_applied: Optional[str] = None


class POIAssistantRequest(BaseModel):
    poi_name: str
    address_hint: Optional[str] = None
    category_hint: Optional[str] = None
    context: Optional[str] = None


class POIAssistantResponse(BaseModel):
    name: str
    category: str = "food_drink"
    address: str = ""
    description: str = ""
    narration_script: str = ""
    specialties: List[str] = Field(default_factory=list)
    latitude: Optional[float] = 10.7635
    longitude: Optional[float] = 106.7042
    confidence: Optional[str] = "high"


class AIRefineDescriptionRequest(BaseModel):
    poi_name: str
    current_description: Optional[str] = ""
    category: Optional[str] = "food_drink"
    address: Optional[str] = None
    tone: Optional[str] = "cuốn hút"  # "cuốn hút", "lịch sử", "hài hước", "ngắn gọn"


class AIRefineDescriptionResponse(BaseModel):
    poi_name: str
    refined_description: str
    suggested_title: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    narration_script: Optional[str] = None


class MultilingualItem(BaseModel):
    name: str
    description: str


class AIMultilingualTranslateRequest(BaseModel):
    poi_id: Optional[str] = None
    poi_name: str
    description: str
    category: Optional[str] = "food_drink"


class AIMultilingualTranslateResponse(BaseModel):
    poi_id: Optional[str] = None
    translations: dict[str, MultilingualItem]

