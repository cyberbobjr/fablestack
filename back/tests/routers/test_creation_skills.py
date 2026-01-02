
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.models.domain.rules_manager import RulesManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager
from back.models.domain.user import User, UserRole
from back.services.character_data_service import CharacterDataService
from back.services.image_generation_service import ImageGenerationService
from back.services.races_data_service import RacesDataService

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



# Mock data
MOCK_RACE_DATA = MagicMock(
    id="humans", 
    name="Humans", 
    description="Human race", 
    cultures=[
        MagicMock(
            id="gondorians", 
            name="Gondorians", 
            description="People of Gondor",
            free_skill_points=5  # Crucial for this test
        )
    ]
)

@pytest.fixture(autouse=True)
def clean_overrides():
    # Force mock user override
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    yield
    # Clean and restore
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

def set_overrides(mocks: Dict[Any, Any]):
    injector = app.state.injector
    for cls, mock_inst in mocks.items():
        try:
            injector.binder.bind(cls, to=mock_inst)
        except Exception:
            injector.binder._bindings[cls] = (mock_inst, None)

def test_create_character_with_free_skill_points():
    """
    Test that creation accepts more than 40 skill points if culture provides free points.
    Current bug: Hardcoded limit of 40 ignores free_skill_points.
    """
    # Setup Mocks
    mock_races = MagicMock(spec=RacesDataService)
    mock_races.get_race_by_id.return_value = MOCK_RACE_DATA
    mock_races.get_complete_character_bonuses.return_value = {}

    mock_rules = MagicMock(spec=RulesManager)
    mock_rules.get_sex_bonuses.return_value = {'stats': {'strength': 1}}
    mock_rules.get_stats_creation_rules.return_value = {
        'start_value': 8,
        'budget': 999, # high budget to ignore stat cost validation
        'costs': {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    }

    mock_skills = MagicMock(spec=UnifiedSkillsManager)
    mock_skills.get_skill_data.return_value = {'category': 'combat', 'id': 'melee_weapons'}

    mock_data = AsyncMock(spec=CharacterDataService)
    async def save_side_effect(data, cid):
        return data
    mock_data.save_character.side_effect = save_side_effect
    
    mock_image = AsyncMock(spec=ImageGenerationService)
    mock_image.generate_character_portrait.return_value = None

    set_overrides({
        RacesDataService: mock_races,
        RulesManager: mock_rules,
        UnifiedSkillsManager: mock_skills,
        CharacterDataService: mock_data,
        ImageGenerationService: mock_image
    })

    # Create request with 45 skill points (40 base + 5 free)
    request_data = {
        "name": "Skillful Hero",
        "sex": "male",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {"strength": 10, "constitution": 10, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
        "skills": {
            "combat": {
                "melee_weapons": 10,
                "weapon_handling": 10
            },
            "general": {
                "perception": 10,
                "stealth": 10,
                "athletics": 5
            }
        },
        "background": "A test hero",
        "physical_description": "A test description"
    }

    response = client.post("/api/creation/create", json=request_data)
    
    assert response.status_code == 200, f"Expected 200 OK but got {response.status_code}: {response.json()}"
