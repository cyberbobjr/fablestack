from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.models.api.game import ActiveSessionsResponse
from back.models.domain.character import (Character, CharacterStatus,
                                          CombatStats, Skills, Stats)
from back.models.domain.user import User, UserRole
from back.models.enums import CharacterSex
from back.models.service.dtos import SessionStartResult, SessionSummary
from back.services.character_data_service import CharacterDataService
# Imports for binding
from back.services.game_session_service import GameSessionService

client = TestClient(app)

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

def test_list_active_sessions_success():
    """
    Test successful listing of active game sessions.
    """
    mock_session_id = uuid4()
    mock_character_id = uuid4()

    mock_sessions = [
        SessionSummary(
            session_id=str(mock_session_id),
            scenario_id="test_scenario.md",
            character_id=str(mock_character_id),
        )
    ]

    mock_stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    mock_skills = Skills()
    mock_combat_stats = CombatStats(max_hit_points=100, current_hit_points=100)

    mock_character = Character(
        id=mock_character_id,
        user_id=uuid4(),
        name="Test Character",
        race="Human",
        sex=CharacterSex.MALE,
        culture="Gondor",
        stats=mock_stats,
        skills=mock_skills,
        combat_stats=mock_combat_stats,
    )

    # Mock Services
    mock_session_service = AsyncMock(spec=GameSessionService)
    mock_session_service.list_all_sessions.return_value = mock_sessions
    
    # Explicitly create and bind mock for CharacterDataService to avoid leaks/patch issues
    mock_data_service = AsyncMock(spec=CharacterDataService)
    mock_data_service.load_character.return_value = mock_character

    injector = app.state.injector
    
    # Store original binding to restore later
    original_data_service_binding = None
    if CharacterDataService in injector.binder._bindings:
        original_data_service_binding = injector.binder._bindings[CharacterDataService]

    # Bind the mock
    try:
        injector.binder.bind(CharacterDataService, to=mock_data_service)
    except Exception:
        # Force overwrite if already bound (e.g. by test_creation leakage)
        injector.binder._bindings[CharacterDataService] = (mock_data_service, None)

    # Patch GameSessionService (static) and ScenarioService (static)
    with patch('back.routers.gamesession.GameSessionService.list_all_sessions', new_callable=AsyncMock) as mock_list, \
         patch('back.routers.gamesession.ScenarioService.get_scenario_title', new_callable=AsyncMock) as mock_title, \
         patch('back.routers.gamesession.ScenarioService.get_scenario_id', new_callable=AsyncMock) as mock_id:
         
        mock_title.return_value = "Test Scenario Title"
        mock_id.return_value = "test_scenario.md"
        mock_list.return_value = mock_sessions

        # Action
        response = client.get("/api/gamesession/sessions")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert len(data["sessions"]) == 1
    session = data["sessions"][0]
    assert session["session_id"] == str(mock_session_id)
    assert session["scenario_name"] == "Test Scenario Title"
    assert session["character_name"] == "Test Character"

    # Clean up the injector binding
    if original_data_service_binding:
        injector.binder._bindings[CharacterDataService] = original_data_service_binding
    else:
        del injector.binder._bindings[CharacterDataService]


def test_list_active_sessions_empty():
    """
    Test listing active sessions when none exist.
    """
    # Mock Service
    mock_session_service = AsyncMock(spec=GameSessionService)
    mock_session_service.list_all_sessions.return_value = []
    
    injector = app.state.injector
    try:
         injector.binder.bind(GameSessionService, to=mock_session_service)
    except Exception:
         injector.binder._bindings[GameSessionService] = (mock_session_service, None)

    response = client.get("/api/gamesession/sessions")

    assert response.status_code == 200
    active_sessions_response = ActiveSessionsResponse.model_validate(response.json())
    assert len(active_sessions_response.sessions) == 0

def test_list_active_sessions_character_not_found():
    """
    Test listing active sessions when a character is not found.
    """
    mock_session_id = uuid4()
    mock_character_id = uuid4()

    mock_sessions = [
        SessionSummary(
            session_id=str(mock_session_id),
            scenario_id="test_scenario.md",
            character_id=str(mock_character_id),
        )
    ]

    # Mock with patch
    with patch('back.routers.gamesession.GameSessionService.list_all_sessions', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_sessions
        
        # Injector binding for CharacterDataService (since it IS injected)
        mock_data = AsyncMock(spec=CharacterDataService)
        mock_data.load_character.side_effect = FileNotFoundError
        
        injector = app.state.injector
        injector.binder.bind(CharacterDataService, to=mock_data)
        
        # Patch ScenarioService calls as we did in main test
        with patch('back.routers.gamesession.ScenarioService.get_scenario_title', new_callable=AsyncMock) as mock_title, \
             patch('back.routers.gamesession.ScenarioService.get_scenario_id', new_callable=AsyncMock) as mock_id:
            mock_title.return_value = "Test Scenario Title"
            mock_id.return_value = "test_scenario.md"
            
            response = client.get("/api/gamesession/sessions")

        assert response.status_code == 200
        active_sessions_response = ActiveSessionsResponse.model_validate(response.json())
        assert len(active_sessions_response.sessions) == 1
        session_info = active_sessions_response.sessions[0]
        assert session_info.character_name == "Unknown"

def test_start_scenario_success():
    """
    Test successfully starting a new scenario using /start endpoint.
    """
    mock_session_id = uuid4()
    mock_character_id = uuid4()
    mock_scenario_name = "Test Scenario"

    start_scenario_response = SessionStartResult(
        session_id=str(mock_session_id),
        scenario_name=mock_scenario_name,
        character_id=str(mock_character_id),
        message="Session started"
    )

    # Mock Data Service
    mock_data = AsyncMock(spec=CharacterDataService)
    mock_char = MagicMock()
    mock_char.status = CharacterStatus.ACTIVE
    mock_char.user_id = MOCK_USER_ID
    mock_data.load_character.return_value = mock_char

    # Injector binding
    injector = app.state.injector
    
    real_data_service = None
    
    try:
        try:
            real_data_service = injector.get(CharacterDataService)
        except Exception:
            injector.binder.bind(CharacterDataService, to=mock_data)
        
        # Patch load_character on real service if it exists (Singleton patching)
        original_load = None
        if real_data_service:
            original_load = real_data_service.load_character
            real_data_service.load_character = mock_data.load_character

        # Patch GameSessionService.start_scenario (static method)
        with patch('back.routers.gamesession.GameSessionService.start_scenario', new_callable=AsyncMock) as mock_start:
            mock_start.return_value = start_scenario_response

            request_data = {
                "scenario_name": mock_scenario_name,
                "character_id": str(mock_character_id)
            }
            # Note: The endpoint is /start not /play for starting now (explicitly) or /play-stream
            response = client.post("/api/gamesession/start", json=request_data)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["session_id"] == str(mock_session_id)
            assert response_data["message"] == "Session started"
            
    finally:
        if real_data_service and original_load:
            real_data_service.load_character = original_load


