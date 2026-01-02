"""
User Domain Model
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from back.models.domain.preferences import UserPreferences


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    """
    User model representing a registered user in the system.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    hashed_password: str = Field(..., description="Hashed password")
    full_name: Optional[str] = Field(None, description="User full name")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Is the user active")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    daily_portrait_count: int = Field(default=0, description="Number of portraits generated today")
    last_portrait_date: Optional[datetime] = Field(None, description="Date of last portrait generation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "aragorn@gondor.com",
                "full_name": "Aragorn II Elessar",
                "role": "user",
                "is_active": True
            }
        }
    )
