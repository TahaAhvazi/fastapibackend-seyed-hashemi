from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    WAREHOUSE = "warehouse"


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = True
    role: Optional[UserRole] = None


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123",
                "first_name": "محمد",  # Mohammad
                "last_name": "احمدی",  # Ahmadi
                "role": "warehouse"
            }
        }


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "first_name": "علی",  # Ali
                "last_name": "محمدی",  # Mohammadi
                "email": "ali@example.com",
                "role": "accountant",
                "is_active": True
            }
        }


# Properties to return via API
class User(UserBase):
    id: int

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "first_name": "محمد",  # Mohammad
                "last_name": "احمدی",  # Ahmadi
                "role": "warehouse",
                "is_active": True
            }
        }


# Additional schemas for authentication
class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class TokenPayload(BaseModel):
    sub: Optional[str] = None


class Login(BaseModel):
    email: EmailStr
    password: str

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123"
            }
        }