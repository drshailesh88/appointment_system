"""
Authentication API endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    db: DbSession,
    user_in: UserCreate,
) -> User:
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(
        select(User).where(
            or_(User.email == user_in.email, User.phone == user_in.phone)
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.email == user_in.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    # Create user
    user = User(
        email=user_in.email,
        phone=user_in.phone,
        name=user_in.name,
        role=user_in.role.value,
        password_hash=get_password_hash(user_in.password),
        clinic_id=user_in.clinic_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict:
    """Login with email/phone and password."""
    # Username can be email or phone
    result = await db.execute(
        select(User).where(
            or_(User.email == form_data.username, User.phone == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Create tokens
    extra_claims = {
        "clinic_id": str(user.clinic_id) if user.clinic_id else None,
        "role": user.role,
    }

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims=extra_claims,
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    # Update last login and store refresh token
    user.last_login = datetime.now(timezone.utc)
    user.refresh_token = refresh_token
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/login/json", response_model=Token)
async def login_json(
    db: DbSession,
    credentials: UserLogin,
) -> dict:
    """Login with JSON body (email/phone and password)."""
    identifier = credentials.email or credentials.phone

    result = await db.execute(
        select(User).where(
            or_(User.email == identifier, User.phone == identifier)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/phone or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    extra_claims = {
        "clinic_id": str(user.clinic_id) if user.clinic_id else None,
        "role": user.role,
    }

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims=extra_claims,
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    user.last_login = datetime.now(timezone.utc)
    user.refresh_token = refresh_token
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: DbSession,
    refresh_token: str,
) -> dict:
    """Refresh access token."""
    payload = decode_token(refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or user.refresh_token != refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Create new tokens
    extra_claims = {
        "clinic_id": str(user.clinic_id) if user.clinic_id else None,
        "role": user.role,
    }

    new_access_token = create_access_token(
        subject=str(user.id),
        extra_claims=extra_claims,
    )
    new_refresh_token = create_refresh_token(subject=str(user.id))

    user.refresh_token = new_refresh_token
    await db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/logout")
async def logout(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Logout and invalidate refresh token."""
    current_user.refresh_token = None
    await db.commit()

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> User:
    """Get current user information."""
    return current_user
