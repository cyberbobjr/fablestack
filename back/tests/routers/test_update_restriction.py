from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from back.auth_dependencies import get_current_active_user
from back.main import app
from back.models.domain.character import Character
from back.models.domain.user import User, UserRole
from back.models.enums import CharacterStatus
from back.services.character_data_service import CharacterDataService

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
def clean_overrides():
    # Force mock user override
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    yield
    # Clean and restore
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user


import pytest_asyncio


@pytest_asyncio.fixture
async def test_character():
    # Create a dummy character
    char_data = {
        "name": "Test Character",
        "race": "humans",
        "sex": "male",
        "culture": "gondorians",
        "stats": {
            "strength": 10,
            "constitution": 10,
            "agility": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        },
        "skills": {
            "general": {"perception": 1}
        },
        "combat_stats": {
            "max_hit_points": 10,
            "current_hit_points": 10,
            "max_mana_points": 10,
            "current_mana_points": 10,
            "armor_class": 10,
            "attack_bonus": 0
        },
        "status": CharacterStatus.DRAFT
    }
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", **char_data)
    await CharacterDataService().save_character(character, str(character.id))
    yield character
    # Cleanup
    try:
        await CharacterDataService().delete_character(str(character.id))
    except:
        pass

@pytest.mark.asyncio
async def test_update_character_success(async_client, test_character):
    """Test that a draft character can be updated"""
    payload = {
        "character_id": str(test_character.id),
        "name": "Updated Name"
    }
    response = await async_client.post("/api/creation/update", json=payload)
    assert response.status_code == 200
    assert response.json()["character"]["name"] == "Updated Name"

@pytest.mark.asyncio
async def test_update_character_in_game_failure(async_client, test_character):
    """Test that an IN_GAME character cannot be updated"""
    # Set character status to IN_GAME
    test_character.status = CharacterStatus.IN_GAME
    
    # We will force the app to use a mock that returns this specific character
    mock_data_service = AsyncMock(spec=CharacterDataService)
    mock_data_service.load_character.return_value = test_character
    
    injector = app.state.injector
    
    try:
        # Bind our mock - no need to save original as this is per-test isolation
        # The injector binding is ephemeral for this test context
            
        # Bind our mock
        injector.binder.bind(CharacterDataService, to=mock_data_service)
        
        payload = {
            "character_id": str(test_character.id),
            "name": "Should Fail"
        }
        response = await async_client.post("/api/creation/update", json=payload)
    finally:
        # We can't easily restore correct state of injector if we overwrote binding in a complex way without access to scope.
        # But for tests, usually resetting or letting it be is okay if we use `clean_test_data_dir` or if bindings are scoped.
        # However, to be safe, we can try to re-bind a real instance or simple cleanup.
        # Since other tests might rely on real service, we should probably unbind?
        # injector.binder.unbind? No such method usually.
        # We can bind back to a fresh CharacterDataService instance?
        injector.binder.bind(CharacterDataService, to=CharacterDataService())

    
    # Needs to be implemented: Expecting 400 Bad Request
    assert response.status_code == 400
    assert "adventure" in response.json()["detail"].lower()
