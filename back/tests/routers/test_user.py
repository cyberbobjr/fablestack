from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.interfaces.user_manager_protocol import \
    UserManagerProtocol as UserManager
from back.models.domain.user import User, UserRole

# Mock User
MOCK_USER_ID = uuid4()
MOCK_USER = User(
    id=MOCK_USER_ID,
    email="test@example.com", 
    hashed_password="hash", 
    full_name="Test User",
    role=UserRole.USER,
    is_active=True,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

async def mock_get_current_active_user():
    return MOCK_USER

@pytest.fixture(autouse=True)
def setup_dependencies():
    # Auth Override
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    
    injector = app.state.injector
    try:
        real_service = injector.get(UserManager)
    except Exception:
         yield
         app.dependency_overrides = {}
         return

    # Patch update method
    original_update = real_service.update
    
    async def update_side_effect(user_arg):
        # Update global mock user state
        MOCK_USER.preferences = user_arg.preferences
        return MOCK_USER
        
    real_service.update = AsyncMock(side_effect=update_side_effect)

    yield
    
    # Restore
    real_service.update = original_update
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_preferences(async_client: AsyncClient, user_token: str):
    """
    Test GET /api/user/preference
    """
    response = await async_client.get("/api/user/preference", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "language" in data
    # Default might be defined in UserPreferences model, assume English if not registered with specific prefs?
    # Actually register endpoint sets defaults.

@pytest.mark.asyncio
async def test_update_preferences(async_client: AsyncClient, user_token: str):
    """
    Test PUT /api/user/preference
    """
    payload = {"language": "French"}
    response = await async_client.put("/api/user/preference", json=payload, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "French"
    
    # Verify persistence via GET
    response = await async_client.get("/api/user/preference", headers={"Authorization": f"Bearer {user_token}"})
    assert response.json()["language"] == "French"

@pytest.mark.asyncio
async def test_update_preferences_with_theme(async_client: AsyncClient, user_token: str):
    """
    Test PUT /api/user/preference with theme
    """
    payload = {"language": "English", "theme": "light"}
    response = await async_client.put("/api/user/preference", json=payload, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "light"
    
    # Verify persistence via GET
    response = await async_client.get("/api/user/preference", headers={"Authorization": f"Bearer {user_token}"})
    assert response.json()["theme"] == "light"
