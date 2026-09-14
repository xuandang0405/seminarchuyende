from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AdminUserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True


class AdminUserCreate(AdminUserBase):
    password: str = Field(..., min_length=6)


class AdminUserResponse(AdminUserBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminUserResponse
