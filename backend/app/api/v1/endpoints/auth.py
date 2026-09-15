import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.database import get_database
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.schemas.user import (
    AdminUserCreate,
    AdminUserResponse,
    OwnerRegisterRequest,
    LoginRequest,
    Token
)

router = APIRouter(prefix="/auth", tags=["Authentication & Roles"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    user = await db["admin_users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role", "admin")
    if role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required"
        )
    return current_user


async def get_current_owner(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in ("owner", "admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner account required"
        )
    return current_user


@router.post("/register", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(user_in: AdminUserCreate, current_admin: dict = Depends(get_current_super_admin)):
    """Only Super Admin can register internal admins."""
    db = get_database()
    existing = await db["admin_users"].find_one({"email": user_in.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    now = datetime.now(timezone.utc)
    new_user = {
        "_id": str(uuid.uuid4()),
        "email": user_in.email,
        "full_name": user_in.full_name,
        "password_hash": get_password_hash(user_in.password),
        "role": user_in.role or "admin",
        "is_active": user_in.is_active,
        "created_at": now,
        "updated_at": now
    }
    await db["admin_users"].insert_one(new_user)
    return new_user


@router.post("/owner-register", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def register_owner(req: OwnerRegisterRequest):
    """Public registration for Restaurant / Store Owners (Chủ quán). Awaits admin approval."""
    db = get_database()
    existing = await db["admin_users"].find_one({"email": req.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    now = datetime.now(timezone.utc)
    new_owner = {
        "_id": str(uuid.uuid4()),
        "email": req.email,
        "full_name": req.full_name,
        "password_hash": get_password_hash(req.password),
        "role": "owner",
        "phone": req.phone,
        "store_name": req.store_name,
        "store_address": req.store_address,
        "owner_status": "pending",
        "admin_notes": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    await db["admin_users"].insert_one(new_owner)
    return new_owner


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    db = get_database()
    user = await db["admin_users"].find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )

    access_token = create_access_token(
        subject=user["_id"],
        claims={
            "email": user["email"],
            "name": user["full_name"],
            "role": user.get("role", "admin"),
            "owner_status": user.get("owner_status")
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=AdminUserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
