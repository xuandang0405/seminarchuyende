from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field

UserRole = Literal["super_admin", "admin", "owner", "tourist"]
OwnerStatus = Literal["pending", "approved", "rejected"]


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = "admin"
    is_active: bool = True
    phone: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    owner_status: Optional[OwnerStatus] = None
    admin_notes: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class OwnerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    phone: str
    store_name: str
    store_address: str
    notes: Optional[str] = None


class AdminUserCreate(UserCreate):
    pass


class AdminUserResponse(UserBase):
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
