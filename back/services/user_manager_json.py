import json
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import aiofiles

from back.config import get_data_dir
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.user import User
from back.utils.logger import get_logger

logger = get_logger(__name__)

class JsonUserManager(UserManagerProtocol):
    """
    JSON implementation of UserManagerProtocol.
    Stores users in a single JSON file.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or get_data_dir()
        self.file_path = Path(self.data_dir) / "users.json"
        
        # Ensure file exists
        if not self.file_path.exists():
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    async def _load_users(self) -> List[User]:
        if not self.file_path.exists():
            return []
        
        async with aiofiles.open(self.file_path, 'r') as f:
            content = await f.read()
            if not content.strip():
                return []
            data = json.loads(content)
            return [User(**user_data) for user_data in data]

    async def _save_users(self, users: List[User]) -> None:
        async with aiofiles.open(self.file_path, 'w') as f:
            # Create a list of dicts, let Pydantic handle serialization of UUID/Dates
            data = [user.model_dump(mode='json') for user in users]
            await f.write(json.dumps(data, indent=2))

    async def get_by_email(self, email: str) -> Optional[User]:
        users = await self._load_users()
        for user in users:
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        users = await self._load_users()
        for user in users:
            if user.id == user_id:
                return user
        return None

    async def create(self, user: User) -> User:
        users = await self._load_users()
        # Check consistency
        for u in users:
            if u.email.lower() == user.email.lower():
                raise ValueError(f"User with email {user.email} already exists")
        
        users.append(user)
        await self._save_users(users)
        return user

    async def update(self, user: User) -> User:
        users = await self._load_users()
        for i, u in enumerate(users):
            if u.id == user.id:
                users[i] = user
                await self._save_users(users)
                return user
        raise ValueError(f"User with id {user.id} not found")

    async def delete(self, user_id: UUID) -> bool:
        users = await self._load_users()
        initial_len = len(users)
        users = [u for u in users if u.id != user_id]
        if len(users) < initial_len:
            await self._save_users(users)
            return True
        return False

    async def list_all(self) -> List[User]:
        return await self._load_users()
