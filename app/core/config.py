import os
import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 30 days * 3 months = 3 months
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30 * 3
    # CORS settings - Allow all origins for development
    CORS_ORIGINS: List[str] = ["*"]

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "Rancetxe Fabric Store Management System"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/rancetxe"
    
    # Users
    FIRST_SUPERUSER_EMAIL: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    FIRST_SUPERUSER_FIRST_NAME: str = "مدیر"
    FIRST_SUPERUSER_LAST_NAME: str = "سیستم"
    FIRST_ACCOUNTANT_EMAIL: str = "accountant@example.com"
    FIRST_ACCOUNTANT_PASSWORD: str = "accountant"
    FIRST_ACCOUNTANT_FIRST_NAME: str = "حسابدار"
    FIRST_ACCOUNTANT_LAST_NAME: str = "سیستم"
    FIRST_WAREHOUSE_EMAIL: str = "warehouse@example.com"
    FIRST_WAREHOUSE_PASSWORD: str = "warehouse"
    FIRST_WAREHOUSE_FIRST_NAME: str = "انباردار"
    FIRST_WAREHOUSE_LAST_NAME: str = "سیستم"
    
    # File uploads
    UPLOADS_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".pdf"]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()