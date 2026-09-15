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
