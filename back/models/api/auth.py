"""
API Schemas for Authentication and User Management.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# --- USER & AUTH SCHEMAS ---

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class MagicLoginRequest(BaseModel):
    email: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    password: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "gandalf@whitecouncil.org",
                "full_name": "Gandalf the White",
                "password": "you_shall_not_pass",
                "avatar_url": "https://example.com/gandalf.jpg"
            }
        }
    }

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None # Admin only

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "saruman@isengard.com",
                "full_name": "Saruman of Many Colors",
                "is_active": True,
                "role": "user"
            }
        }
    }

class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: Any # datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
