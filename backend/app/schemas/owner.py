from datetime import datetime
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field

SubmissionStatus = Literal["pending", "approved", "rejected"]
SubmissionType = Literal["new_poi", "update_poi", "menu_update"]


class OwnerSubmissionCreate(BaseModel):
    poi_id: Optional[str] = None
    submission_type: SubmissionType = "update_poi"
    title: str
    proposed_content: Dict[str, Any]
    owner_notes: Optional[str] = None


class OwnerSubmissionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    owner_id: str
    poi_id: Optional[str] = None
    submission_type: SubmissionType
    title: str
    proposed_content: Dict[str, Any]
    owner_notes: Optional[str] = None
    status: SubmissionStatus = "pending"
    admin_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }


class OwnerReviewAction(BaseModel):
    action: Literal["approve", "reject"]
    admin_notes: Optional[str] = None
