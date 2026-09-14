import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.database import get_database
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.schemas.user import AdminUserCreate, AdminUserResponse, LoginRequest, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_admin(token: str = Depends(oauth2_scheme)):
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


@router.post("/register", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(user_in: AdminUserCreate):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    # Check if user already exists
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
        "is_active": user_in.is_active,
        "created_at": now,
        "updated_at": now
    }

    await db["admin_users"].insert_one(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

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
            detail="User account is inactive"
        )

    access_token = create_access_token(
        subject=user["_id"],
        claims={"email": user["email"], "name": user["full_name"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=AdminUserResponse)
async def get_me(current_user: dict = Depends(get_current_admin)):
    return current_user
