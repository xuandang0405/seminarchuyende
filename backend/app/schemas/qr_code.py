from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class QRCodeBase(BaseModel):
    poi_id: str
    label: str
    is_active: bool = True


class QRCodeCreate(QRCodeBase):
    pass


class QRCodeResponse(QRCodeBase):
    id: str = Field(..., alias="_id")
    qr_uri: str = Field(..., description="tourguide://qr/<_id>")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }


class QRResolveResponse(BaseModel):
    qr_id: str
    poi_id: str
    poi: Dict[str, Any]
    content: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
