from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.character import (Character, CharacterStatus,
                                          CombatStats, Equipment, Skills,
                                          Spells, Stats)
from back.models.domain.preferences import UserPreferences
from back.models.domain.user import User, UserRole
from back.models.enums import CharacterSex
from back.services.character_data_service import CharacterDataService

client = TestClient(app)

# Mock Data
MOCK_USER_ID = uuid4()
MOCK_USER = User(
    id=MOCK_USER_ID,
    email="test@example.com",
    hashed_password="hash",
    full_name="Test User",
    role=UserRole.USER,
    is_active=True,
    daily_portrait_count=0,
    last_portrait_date=None,
    preferences=UserPreferences(language="French"),
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc)
)

MOCK_CHARACTER = Character(
    id=uuid4(),
    user_id=MOCK_USER_ID,
    name="Aragorn",
    race="Human",
    sex=CharacterSex.MALE,
    culture="Gondor",
    stats=Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10),
    skills=Skills(),
    combat_stats=CombatStats(max_hit_points=10, current_hit_points=10, max_mana_points=10, current_mana_points=10, armor_class=10, attack_bonus=0),
    equipment=Equipment(),
    spells=Spells(),
    level=1,
    status=CharacterStatus.ACTIVE,
    experience_points=0,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc)
)

async def mock_get_current_active_user() -> User:
    """Mock function to return the test user."""
    return MOCK_USER

@pytest.fixture(autouse=True)
def clean_overrides() -> None:
    """Fixture to override dependencies and clean up after tests."""
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_services() -> tuple[AsyncMock, AsyncMock]:
    """Fixture to provide mocked services for character and user management."""
    data_mock = AsyncMock(spec=CharacterDataService)
    user_mock = AsyncMock(spec=UserManagerProtocol)
    
    # Bind mocks
    injector = app.state.injector
    
    try:
        injector.binder.bind(CharacterDataService, to=data_mock)
    except Exception:
        injector.binder._bindings[CharacterDataService] = (data_mock, None)

    try:
        injector.binder.bind(UserManagerProtocol, to=user_mock)
    except Exception:
        injector.binder._bindings[UserManagerProtocol] = (user_mock, None)
    
    return data_mock, user_mock

@pytest.mark.asyncio
async def test_regenerate_portrait_rate_limit(mock_services: tuple[AsyncMock, AsyncMock]) -> None:
    """Test daily portrait regeneration rate limiting including successful generation, limit enforcement at the daily maximum, and automatic reset on a new day."""
    data_mock, user_mock = mock_services
    data_mock.load_character.return_value = MOCK_CHARACTER
    data_mock.save_character.return_value = None
    user_mock.update.return_value = MOCK_USER
    
    # Mock ImageGenerationService
    # We patch the class where it is defined. Local import in router will get this mock from sys.modules
    with patch("back.services.image_generation_service.ImageGenerationService") as MockServiceCls:
        instance = MockServiceCls.return_value
        instance.generate_character_portrait = AsyncMock(return_value="http://new-image.png")

        # Ensure config is read with limit=5 (default in our updated config.yaml)
        # If for some reason it fails, we can mock get_image_generation_config too.

        # --- Test 1: Successful generation (Count 0 -> 1) ---
        MOCK_USER.daily_portrait_count = 0
        MOCK_USER.last_portrait_date = datetime.now(timezone.utc)

        response = client.post(f"/api/characters/{MOCK_CHARACTER.id}/portrait")
        assert response.status_code == 200
        assert MOCK_USER.daily_portrait_count == 1

        # --- Test 2: Reach Limit (Count 5 -> Blocked) ---
        # Set count to limit (assigned in config.yaml as 5)
        MOCK_USER.daily_portrait_count = 5
        # Same day
        MOCK_USER.last_portrait_date = datetime.now(timezone.utc)

        response = client.post(f"/api/characters/{MOCK_CHARACTER.id}/portrait")
        assert response.status_code == 429
        assert "La limite quotidienne de 5 régénérations est atteinte. Revenez demain !" in response.json()["detail"]

        # --- Test 3: Reset on new day (Date yesterday -> Reset to 0 -> Increment to 1) ---
        MOCK_USER.daily_portrait_count = 5
        MOCK_USER.last_portrait_date = datetime.now(timezone.utc) - timedelta(days=1)

        response = client.post(f"/api/characters/{MOCK_CHARACTER.id}/portrait")
        assert response.status_code == 200

        # Validate reset and increment
        assert MOCK_USER.daily_portrait_count == 1
        # Date should be today now
        assert MOCK_USER.last_portrait_date.date() == datetime.now(timezone.utc).date()


@pytest.mark.asyncio
async def test_regenerate_portrait_rate_limit_english(mock_services: tuple[AsyncMock, AsyncMock]) -> None:
    """Test that English language users receive the error message in English when the daily portrait regeneration limit is reached."""
    data_mock, user_mock = mock_services
    
    # Create a user with English language preference
    # Note: Using "English" instead of "en" to test that LocalizationService.detect_language() 
    # correctly handles user-friendly language names
    english_user = User(
        id=MOCK_USER_ID,
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        daily_portrait_count=5,  # Already at limit
        last_portrait_date=datetime.now(timezone.utc),
        preferences=UserPreferences(language="English"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    data_mock.load_character.return_value = MOCK_CHARACTER
    data_mock.save_character.return_value = None
    user_mock.update.return_value = english_user
    
    # Override the dependency to return English user
    async def mock_get_english_user() -> User:
        return english_user
    
    app.dependency_overrides[get_current_active_user] = mock_get_english_user
    
    try:
        with patch("back.services.image_generation_service.ImageGenerationService") as MockServiceCls:
            instance = MockServiceCls.return_value
            instance.generate_character_portrait = AsyncMock(return_value="http://new-image.png")
            
            # Test that limit is enforced with English message
            response = client.post(f"/api/characters/{MOCK_CHARACTER.id}/portrait")
            assert response.status_code == 429
            assert "Daily portrait regeneration limit of 5 reached. Please come back tomorrow!" in response.json()["detail"]
    finally:
        # Restore original override
        app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
