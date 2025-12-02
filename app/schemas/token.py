from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class TokenWithRole(BaseModel):
    access_token: str
    token_type: str
    role: str

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "role": "admin"
            }
        }


class TokenPayload(BaseModel):
    sub: Optional[str] = None


class CustomerLogin(BaseModel):
    phone_number: str  # شماره موبایل یا تلفن
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "09121234567",
                "password": "123456789"
            }
        }


class CustomerToken(BaseModel):
    access_token: str
    token_type: str
    customer_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "customer_id": 1
            }
        }