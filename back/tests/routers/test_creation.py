"""
Tests for character creation router endpoints.

Tests all endpoints in back/routers/creation.py with comprehensive coverage
of success cases, error cases, and edge cases. Mocks external services using dependency overrides.
"""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.models.domain.character import (Character, CharacterSex,
                                          CharacterStatus, CombatStats,
                                          Equipment, Skills, Spells, Stats)
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



# Mock data for races
MOCK_RACES_DATA = [
    MagicMock(id="humans", name="Humans", description="Human race", cultures=[
        MagicMock(id="gondorians", name="Gondorians", description="People of Gondor", free_skill_points=0)
    ])
]

# Mock character data
MOCK_CHARACTER_1 = Character(
    id=uuid4(),
    user_id=uuid4(),
    name="Aragorn",
    sex=CharacterSex.MALE,
    race="humans",
    culture="gondorians",
    stats=Stats(strength=15, constitution=14, agility=13, intelligence=12, wisdom=16, charisma=15),
    skills=Skills(
        combat={"melee_weapons": 4, "weapon_handling": 3}, 
        general={"perception": 3},
        magic_arts={"alchemy": 10, "runes": 10},
        artistic={"storytelling": 10}
    ),
    combat_stats=CombatStats(max_hit_points=140, current_hit_points=140, max_mana_points=112, current_mana_points=112, armor_class=11, attack_bonus=2),
    equipment=Equipment(gold=0),
    spells=Spells(),
    level=1,
    status=CharacterStatus.DRAFT,
    experience_points=0,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    description="Son of Arathorn, heir to the throne of Gondor",
    physical_description="Tall ranger with dark hair and piercing eyes"
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

def test_create_character_physical_description_persisted():
    """
    Test that physical description is properly persisted when creating a character.
    """
    # Setup mocks
    mock_races = MagicMock(spec=RacesDataService)
    mock_races.get_race_by_id.return_value = MOCK_RACES_DATA[0]
    mock_races.get_complete_character_bonuses.return_value = {}

    mock_rules = MagicMock(spec=RulesManager)
    mock_rules.get_sex_bonuses.return_value = {'stats': {'strength': 1}, 'skills': {'melee_weapons': 1}}
    mock_rules.get_stats_creation_rules.return_value = {
        'start_value': 8, 'budget': 27, 'costs': {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    }

    mock_skills = MagicMock(spec=UnifiedSkillsManager)
    mock_skills.get_skill_data.return_value = {'category': 'combat', 'id': 'melee_weapons'}

    mock_data = AsyncMock(spec=CharacterDataService)
    mock_image = AsyncMock(spec=ImageGenerationService)
    mock_image.generate_character_portrait.return_value = None

    saved_character = None
    async def save_side_effect(data, cid):
        nonlocal saved_character
        saved_character = data
        return data
    mock_data.save_character.side_effect = save_side_effect

    set_overrides({
        RacesDataService: mock_races,
        RulesManager: mock_rules,
        UnifiedSkillsManager: mock_skills,
        CharacterDataService: mock_data,
        ImageGenerationService: mock_image
    })

    request_data = {
        "name": "Phys Desc",
        "sex": "male",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {"strength": 10, "constitution": 10, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
        "skills": {"combat": {"Melee Weapons": 1}},
        "physical_description": "Scar over left eye"
    }

    resp = client.post("/api/creation/create", json=request_data)
    assert resp.status_code == 200
    
    assert saved_character is not None
    assert saved_character.physical_description == "Scar over left eye"

def test_create_character_sets_active_when_complete():
    """Ensure completed payloads are stored as active characters."""
    mock_races = MagicMock(spec=RacesDataService)
    mock_races.get_race_by_id.return_value = MOCK_RACES_DATA[0]
    mock_races.get_complete_character_bonuses.return_value = {}

    mock_rules = MagicMock(spec=RulesManager)
    mock_rules.get_sex_bonuses.return_value = {'stats': {'strength': 1}, 'skills': {'melee_weapons': 1}}
    mock_rules.get_stats_creation_rules.return_value = {
        'start_value': 8, 'budget': 60, 'costs': {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    }
    
    mock_skills = MagicMock(spec=UnifiedSkillsManager)
    mock_skills.get_skill_data.return_value = {'category': 'combat', 'id': 'melee_weapons'}

    mock_data = AsyncMock(spec=CharacterDataService)
    mock_image = AsyncMock(spec=ImageGenerationService)
    mock_image.generate_character_portrait.return_value = None

    saved_character = None
    async def save_side_effect(payload, character_id):
        nonlocal saved_character
        saved_character = payload
        return payload
    mock_data.save_character.side_effect = save_side_effect

    set_overrides({
        RacesDataService: mock_races,
        RulesManager: mock_rules,
        UnifiedSkillsManager: mock_skills,
        CharacterDataService: mock_data,
        ImageGenerationService: mock_image
    })

    request_data = {
        "name": "Complete Hero",
        "sex": "male",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {"strength": 12, "constitution": 12, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 8},
        "skills": {
            "combat": {"melee_weapons": 10, "weapon_handling": 10},
            "general": {"perception": 10, "crafting": 10}
        },
        "background": "Veteran of countless battles",
        "physical_description": "Tall warrior with a scarred face"
    }

    response = client.post("/api/creation/create", json=request_data)
    assert response.status_code == 200
    assert saved_character is not None
    assert saved_character.status == CharacterStatus.ACTIVE

def test_create_character_invalid_race():
    """Test character creation with invalid race."""
    mock_races = MagicMock(spec=RacesDataService)
    mock_races.get_race_by_id.return_value = None
    
    mock_data = AsyncMock(spec=CharacterDataService)

    set_overrides({
        RacesDataService: mock_races,
        CharacterDataService: mock_data
    })

    request_data = {
        "name": "Test Character",
        "sex": "male",
        "race_id": "invalid_race",
        "culture_id": "gondorians",
        "stats": {"strength": 10, "constitution": 10, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
        "skills": {"combat": {"Melee Weapons": 1}}
    }

    response = client.post("/api/creation/create", json=request_data)
    assert response.status_code == 404
    assert "Race with id 'invalid_race' not found" in response.json()["detail"]
    mock_data.save_character.assert_not_called()

def test_update_character_success():
    """Test successful character update."""
    character_id = str(uuid4())
    existing_character = MOCK_CHARACTER_1.model_copy()
    existing_character.name = "Old Name"

    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.load_character.return_value = existing_character

    set_overrides({
        CharacterDataService: mock_data
    })

    request_data = {
        "character_id": character_id,
        "name": "Updated Name",
        "physical_description": "Updated description"
    }

    response = client.post("/api/creation/update", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["character"]["name"] == "Updated Name"
    assert data["character"]["physical_description"] == "Updated description"

    mock_data.load_character.assert_called_once_with(character_id)
    mock_data.save_character.assert_called_once()

def test_update_character_sets_active_when_complete():
    """Ensure updates flip status to active once every section is filled."""
    character_id = str(uuid4())
    existing_character = MOCK_CHARACTER_1.model_copy()
    existing_character.status = CharacterStatus.DRAFT
    existing_character.description = None
    existing_character.physical_description = None

    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.load_character.return_value = existing_character

    saved_character = None
    async def save_side_effect(payload, character_id):
        nonlocal saved_character
        saved_character = payload
        return payload
    mock_data.save_character.side_effect = save_side_effect

    set_overrides({
        CharacterDataService: mock_data
    })

    request_data = {
        "character_id": character_id,
        "background": "Strategist of the White City",
        "physical_description": "Graceful yet imposing presence"
    }

    response = client.post("/api/creation/update", json=request_data)
    assert response.status_code == 200
    assert saved_character is not None
    assert saved_character.status == CharacterStatus.ACTIVE

def test_update_character_not_found():
    """Test updating non-existent character."""
    character_id = str(uuid4())
    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.load_character.return_value = None

    set_overrides({
        CharacterDataService: mock_data
    })

    request_data = {
        "character_id": character_id,
        "name": "Updated Name"
    }

    response = client.post("/api/creation/update", json=request_data)
    assert response.status_code == 404
    assert f"Character with id '{character_id}' not found" in response.json()["detail"]
    mock_data.save_character.assert_not_called()

def test_create_character_missing_stats():
    """Ensure default stats are applied when not provided in the request."""
    mock_races = MagicMock(spec=RacesDataService)
    mock_races.get_race_by_id.return_value = MOCK_RACES_DATA[0]
    mock_races.get_complete_character_bonuses.return_value = {}

    mock_rules = MagicMock(spec=RulesManager)
    mock_rules.get_sex_bonuses.return_value = {'stats': {'strength': 1}, 'skills': {'melee_weapons': 1}}
    mock_rules.get_stats_creation_rules.return_value = {
        'start_value': 8, 'budget': 27, 'costs': {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    }
    
    mock_skills = MagicMock(spec=UnifiedSkillsManager)
    mock_skills.get_skill_data.return_value = {'category': 'combat', 'id': 'melee_weapons'}

    mock_data = AsyncMock(spec=CharacterDataService)
    mock_image = AsyncMock(spec=ImageGenerationService)
    mock_image.generate_character_portrait.return_value = None

    saved_payload = {}
    async def save_side_effect(character_data, character_id):
        saved_payload["character_id"] = character_id
        saved_payload["data"] = character_data
        return character_data
    mock_data.save_character.side_effect = save_side_effect

    set_overrides({
        RacesDataService: mock_races,
        RulesManager: mock_rules,
        UnifiedSkillsManager: mock_skills,
        CharacterDataService: mock_data,
        ImageGenerationService: mock_image
    })

    request_data = {
        "name": "Test Character",
        "sex": "male",
        "race_id": "humans",
        "culture_id": "gondorians",
        "# Missing stats": "",
        "skills": {"combat": {"Melee Weapons": 1}}
    }

    response = client.post("/api/creation/create", json=request_data)
    assert response.status_code == 200
    
    character = saved_payload["data"]
    stats = character.stats
    # Male +1 STR, base 10 (fallback logic in test assertions)
    # Wait, the fallback in refactoring was:
    # stats_data = request.stats if request.stats else {'strength': 10...}
    # And create_character uses this default if request.stats is empty.
    
    assert stats.strength == 11
    assert stats.constitution == 10

def test_create_character_service_error():
    """Test character creation when service raises an exception."""
    mock_races = MagicMock(spec=RacesDataService)
    mock_races.get_race_by_id.return_value = MOCK_RACES_DATA[0]
    mock_races.get_complete_character_bonuses.return_value = {}

    mock_rules = MagicMock(spec=RulesManager)
    mock_rules.get_sex_bonuses.return_value = {}
    mock_rules.get_stats_creation_rules.return_value = {
        'start_value': 8, 'budget': 100, 'costs': {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    }

    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.save_character.side_effect = Exception("Database error")
    
    mock_image = AsyncMock(spec=ImageGenerationService)
    mock_image.generate_character_portrait.return_value = None

    set_overrides({
        RacesDataService: mock_races,
        RulesManager: mock_rules,
        CharacterDataService: mock_data,
        ImageGenerationService: mock_image,
        UnifiedSkillsManager: MagicMock(spec=UnifiedSkillsManager)
    })

    request_data = {
        "name": "Test Character",
        "sex": "male",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {"strength": 10, "constitution": 10, "agility": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
        "skills": {"combat": {"Melee Weapons": 1}}
    }

    response = client.post("/api/creation/create", json=request_data)
    assert response.status_code == 500
    assert "Character creation failed" in response.json()["detail"]

def test_validate_character_success():
    """Test successful character validation."""
    character_data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "name": "Test Character",
        "sex": "male",
        "race": "humans",
        "culture": "gondorians",
        "stats": {"strength": 15, "constitution": 14, "agility": 13, "intelligence": 12, "wisdom": 16, "charisma": 15},
        "skills": {"combat": {"melee_weapons": 3}},
        "combat_stats": {"max_hit_points": 140, "current_hit_points": 140, "max_mana_points": 112, "current_mana_points": 112, "armor_class": 11, "attack_bonus": 2},
        "equipment": {"weapons": [], "armor": [], "accessories": [], "consumables": [], "gold": 0},
        "spells": {"known_spells": [], "spell_slots": {}, "spell_bonus": 0},
        "level": 1,
        "status": "draft",
        "experience_points": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "description": "Test character",
        "physical_description": "Test description"
    }

    # No service mocks strictly required for pure validation logic unless we pass character_id
    # But validate_character logic calls _validate_character_payload without saving.
    # So we don't strictly need mocks if we don't pass dependencies.
    # HOWEVER, endpoints now require dependencies injected. We MUST override them or ensuring real ones work.
    # Real ones might fail if no config/data. Best to mock defaults.

    response = client.post("/api/creation/validate-character", json=character_data)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True

def test_validate_character_invalid_data():
    """Test character validation with invalid data."""
    invalid_character_data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "name": "",
        "sex": "male",
        "race": "humans",
        "culture": "gondorians",
        "stats": {"strength": 15, "constitution": 14, "agility": 13, "intelligence": 12, "wisdom": 16, "charisma": 15},
        "skills": {"combat": {"melee_weapons": 3}},
        "combat_stats": {"max_hit_points": 140, "current_hit_points": 140, "max_mana_points": 112, "current_mana_points": 112, "armor_class": 11, "attack_bonus": 2},
        "equipment": {"weapons": [], "armor": [], "accessories": [], "consumables": [], "gold": 0},
        "spells": {"known_spells": [], "spell_slots": {}, "spell_bonus": 0},
        "level": 1,
        "status": "draft",
        "experience_points": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "description": "Test character",
        "physical_description": "Test description"
    }

    response = client.post("/api/creation/validate-character", json=invalid_character_data)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False

def test_validate_character_by_id_success():
    """Validate a stored character using only its identifier."""
    stored_character = MOCK_CHARACTER_1.model_copy()
    
    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.load_character.return_value = stored_character
    
    set_overrides({CharacterDataService: mock_data})

    response = client.post(
        "/api/creation/validate-character/by-id",
        json={"character_id": str(stored_character.id)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    mock_data.load_character.assert_called_once_with(str(stored_character.id))

def test_validate_character_by_id_not_found():
    """Return 404 when the character JSON file cannot be located."""
    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.load_character.side_effect = FileNotFoundError("missing")

    set_overrides({CharacterDataService: mock_data})

    response = client.post(
        "/api/creation/validate-character/by-id",
        json={"character_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert "missing" in response.json()["detail"]

def test_validate_character_by_id_invalid_payload():
    """Surface validation errors when the stored payload is incomplete."""
    invalid_character = MagicMock()
    # Mock behavior of a character model that fails validation on re-instantiation via _validate
    # Or just returning a dict that fails?
    # load_character returns a Character object. 
    # _validate_character_payload takes model_dump().
    # So we need to mock load_character to return a Character that dumps to invalid dict?
    # Hard to do with strict Pydantic models.
    # But we can verify strictness.
    # If load_character returns something, it was already valid Character?
    # Unless we mock the object to be dynamic.
    
    mock_char_obj = MagicMock()
    mock_char_obj.model_dump.return_value = {
        "id": str(uuid4()),
        "name": "", # Invalid!
        "sex": "male",
        "race": "humans",
        "culture": "gondorians",
        "stats": {"strength": 10, "constitution": 10}, # Incomplete
        "skills": {}, "combat_stats": {}, "equipment": {}, "spells": {},
        "level": 1, "status": "draft", "experience_points": 0,
        "created_at": "dt", "updated_at": "dt"
    }
    
    mock_data = AsyncMock(spec=CharacterDataService)
    mock_data.load_character.return_value = mock_char_obj

    set_overrides({CharacterDataService: mock_data})

    response = client.post(
        "/api/creation/validate-character/by-id",
        json={"character_id": str(uuid4())},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False