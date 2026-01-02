
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.models.domain.rules_manager import RulesManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager
from back.models.domain.user import User, UserRole
from back.routers.creation import TranslationResult
from back.services.character_data_service import CharacterDataService
from back.services.image_generation_service import ImageGenerationService
# Service imports for binding
from back.services.races_data_service import RacesDataService

client = TestClient(app)

@pytest.fixture
def mock_creation_context():
    # Create Mocks
    races_mock = MagicMock(spec=RacesDataService)
    char_mock = AsyncMock(spec=CharacterDataService)
    rules_mock = MagicMock(spec=RulesManager)
    # rules_mock.get_stats_creation_rules is a method
    
    skills_mgr_mock = MagicMock(spec=UnifiedSkillsManager)
    image_mock = AsyncMock(spec=ImageGenerationService)
    
    # Configure Mocks
    # Races
    mock_race = MagicMock()
    mock_race.id = "humans"
    races_mock.get_race_by_id.return_value = mock_race
    races_mock.get_complete_character_bonuses.return_value = {}
    
    # Rules
    rules_mock.get_stats_creation_rules.return_value = {
        'budget': 999, 'start_value': 8, 'costs': {8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:6, 15:7, 16:8, 17:9, 18:10}
    }
    rules_mock.get_sex_bonuses.return_value = {}
    
    # Image
    image_mock.generate_character_portrait.return_value = "http://mock/url.png"

    # Bind to Injector
    injector = app.state.injector
    bindings = [
        (RacesDataService, races_mock),
        (CharacterDataService, char_mock),
        (RulesManager, rules_mock),
        (UnifiedSkillsManager, skills_mgr_mock),
        (ImageGenerationService, image_mock)
    ]
    
    for cls, mock_inst in bindings:
        try:
            injector.binder.bind(cls, to=mock_inst)
        except Exception:
            injector.binder._bindings[cls] = (mock_inst, None)

    # We still need to patch the Agent function because it's imported directly
    with patch("back.routers.creation.build_simple_gm_agent") as MockAgent:
         yield {
            "agent": MockAgent,
            "races": races_mock,
            "char_service": char_mock,
            "rules": rules_mock,
            "skills": skills_mgr_mock,
            "image": image_mock
        }

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

def test_create_character_auto_translation(mock_creation_context):
    """Test that localized background/description are translated to English on creation."""
    mock_agent_builder = mock_creation_context["agent"]
    mock_char_service = mock_creation_context["char_service"]
    
    # Setup Async Mock for Agent
    mock_agent_instance = AsyncMock()
    mock_agent_builder.return_value = mock_agent_instance
    
    # Mock Translation Result
    trans_output = TranslationResult(
        background_english="Translated Background",
        physical_description_english="Translated Phys Desc"
    )
    mock_agent_instance.run.return_value = MagicMock(output=trans_output)

    payload = {
        "name": "Test Char",
        "sex": "male",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {"strength": 10, "constitution": 10, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
        "skills": {"general": {"perception": 1}},
        "background_localized": "Histoire locale",
        "physical_description_localized": "Description locale"
    }

    response = client.post("/api/creation/create", json=payload)
    
    assert response.status_code == 200, response.text
    
    # Verify Agent Call
    mock_agent_instance.run.assert_called_once()
    call_args = mock_agent_instance.run.call_args[0][0]
    assert "Translate the following" in call_args
    assert "Histoire locale" in call_args
    assert "Description locale" in call_args
    
    # Verify Saved Character has translated values
    mock_char_service.save_character.assert_called_once()
    saved_character = mock_char_service.save_character.call_args[0][0]
    
    assert saved_character.description == "Translated Background"
    assert saved_character.physical_description == "Translated Phys Desc"
    assert saved_character.description_localized == "Histoire locale"
    assert saved_character.physical_description_localized == "Description locale"

def test_create_character_auto_translation_partial(mock_creation_context):
    """Test translation when only one field is provided."""
    mock_agent_builder = mock_creation_context["agent"]
    
    mock_agent_instance = AsyncMock()
    mock_agent_builder.return_value = mock_agent_instance
    
    trans_output = TranslationResult(
        background_english="Translated Background Only",
        physical_description_english=None
    )
    mock_agent_instance.run.return_value = MagicMock(output=trans_output)

    payload = {
        "name": "Test Char 2",
        "sex": "female",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {"strength": 10, "constitution": 10, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
        "background_localized": "Histoire locale seulement"
    }

    response = client.post("/api/creation/create", json=payload)
    assert response.status_code == 200
    
    mock_agent_instance.run.assert_called_once()
    call_args = mock_agent_instance.run.call_args[0][0]
    assert "Localized Background:" in call_args
    assert "Localized Physical Description:" not in call_args

    # Check saved data
    mock_char_service = mock_creation_context["char_service"]
    saved_character = mock_char_service.save_character.call_args[0][0]
    assert saved_character.description == "Translated Background Only"
    assert saved_character.physical_description is None # Default
