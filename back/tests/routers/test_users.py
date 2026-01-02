from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.interfaces.user_manager_protocol import \
    UserManagerProtocol as UserManager
from back.models.domain.user import User, UserRole

# Mocks
MOCK_ADMIN = User(
    id=uuid4(),
    email="admin@test.com",
    hashed_password="hash",
    full_name="Admin User",
    role=UserRole.ADMIN,
    is_active=True,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

MOCK_USER = User(
    id=uuid4(),
    email="user@test.com",
    hashed_password="hash",
    full_name="Standard User",
    role=UserRole.USER,
    is_active=True,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Mock UserManager to return users list
mock_user_manager = MagicMock(spec=UserManager)
mock_user_manager.list_all = AsyncMock(return_value=[MOCK_ADMIN, MOCK_USER])

@pytest.fixture(autouse=True)
def setup_user_manager_binding():
    injector = app.state.injector

    try:
        real_service = injector.get(UserManager)
    except Exception:
        yield
        return

    original_get_all = real_service.list_all
    real_service.list_all = AsyncMock(return_value=[MOCK_ADMIN, MOCK_USER])
    
    yield
    
    real_service.list_all = original_get_all

@pytest.mark.asyncio
async def test_read_users_as_admin(async_client: AsyncClient):
    # Override auth to return Admin
    app.dependency_overrides[get_current_active_user] = lambda: MOCK_ADMIN
    response = await async_client.get("/api/users/")
    app.dependency_overrides = {} # Reset
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

@pytest.mark.asyncio
async def test_read_users_as_user_forbidden(async_client: AsyncClient):
    # Override auth to return User
    app.dependency_overrides[get_current_active_user] = lambda: MOCK_USER
    response = await async_client.get("/api/users/")
    app.dependency_overrides = {}
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_read_me(async_client: AsyncClient):
    # Override auth to return User
    app.dependency_overrides[get_current_active_user] = lambda: MOCK_USER
    response = await async_client.get("/api/user/me")
    app.dependency_overrides = {}
    
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
