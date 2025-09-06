from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.post("/login", response_model=schemas.TokenWithRole)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    result = await db.execute(select(models.User).where(models.User.email == form_data.username))
    user = result.scalars().first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور نادرست است",  # Incorrect username or password
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="کاربر غیرفعال است",  # Inactive user
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "role": user.role,
    }


@router.post("/register", response_model=schemas.User)
async def register_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Create new user (admin only)
    """
    # Check if user with this email exists
    result = await db.execute(select(models.User).where(models.User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="کاربری با این ایمیل قبلاً ثبت شده است",  # A user with this email already exists
        )
    
    # Create new user
    user = models.User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        role=user_in.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user
    """
    return current_user