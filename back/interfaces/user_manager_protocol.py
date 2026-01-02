from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID

from back.models.domain.user import User


@runtime_checkable
class UserManagerProtocol(Protocol):
    """
    Interface for User Management Persistence.
    Supports dependency injection for different backends (JSON, SQLite).
    """

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by email."""
        ...

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Retrieve a user by ID."""
        ...

    async def create(self, user: User) -> User:
        """Create a new user."""
        ...

    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID."""
        ...

    async def list_all(self) -> List[User]:
        """List all users."""
        ...
