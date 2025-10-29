from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

# Authentication Schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@example.com",
                "password": "securepassword123"
            }
        }
    }

class RefreshTokenRequest(BaseModel):
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "user-uuid-123",
                    "email": "admin@example.com",
                    "full_name": "Admin User",
                    "role": "SUPER_ADMIN",
                    "dependency_id": None
                }
            }
        }
    }

class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    dependency_id: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    dependency_id: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "newuser@example.com",
                "full_name": "Juan Pérez",
                "role": "WORKER",
                "dependency_id": "dep-uuid-123",
                "password": "securepassword123",
                "is_active": True
            }
        }
    }

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    dependency_id: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Juan Pérez García",
                "is_active": True
            }
        }
    }

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "user-uuid-123",
                "email": "juan.perez@example.com",
                "full_name": "Juan Pérez",
                "role": "WORKER",
                "dependency_id": "dep-uuid-123",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-12-01T14:20:00Z"
            }
        }
    }

class UserList(BaseModel):
    items: List[UserResponse]
    total: int

class UserFilters(BaseModel):
    role: Optional[str] = None
    dependency_id: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

# Error Response Schemas
class ErrorResponse(BaseModel):
    detail: str
    type: Optional[str] = None

class RateLimitResponse(BaseModel):
    detail: str
    retry_after: Optional[int] = None
    attempts_remaining: Optional[int] = None
