"""
Tests for characters router endpoints.

Tests all endpoints in back/routers/characters.py with comprehensive coverage
of success cases, error cases, and edge cases. Mocks external services.
"""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.auth_dependencies import get_current_active_user
from back.models.domain.character import (Character, CharacterStatus,
                                          CombatStats, Equipment, Skills,
                                          Spells, Stats)
from back.models.domain.items import EquipmentItem
from back.models.domain.user import User, UserRole
from back.models.enums import CharacterSex
from back.services.character_data_service import CharacterDataService

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

@pytest.fixture
def mock_data_service():
    mock = AsyncMock(spec=CharacterDataService)
    # Retrieve injector
    injector = app.state.injector
    try:
        injector.binder.bind(CharacterDataService, to=mock)
    except Exception:
        # Fallback for existing binding modification
        injector.binder._bindings[CharacterDataService] = (mock, None)
    
    yield mock
    # No cleanup required for mock object, but we rely on test isolation or
    # subsequence tests overwriting this binding.Ideally we should restore,
    # but since unit tests run sequentially and re-bind, it works.


# Mock character data
MOCK_CHARACTER_1 = Character(
    id=uuid4(),
    user_id=uuid4(),
    name="Aragorn",
    race="Human",
    sex=CharacterSex.MALE,
    culture="Gondor",
    stats=Stats(strength=16, constitution=14, agility=15, intelligence=12, wisdom=14, charisma=16),
    skills=Skills(combat={"sword_combat": 7, "archery": 5}),
    combat_stats=CombatStats(max_hit_points=60, current_hit_points=60, max_mana_points=15, current_mana_points=15, armor_class=17, attack_bonus=5),
    equipment=Equipment(gold=100),
    spells=Spells(),
    level=5,
    status=CharacterStatus.ACTIVE,
    experience_points=4500,
    physical_description="Tall, weathered, dark-haired, with keen grey eyes."
)

MOCK_CHARACTER_2 = Character(
    id=uuid4(),
    user_id=uuid4(),
    name="Legolas",
    race="Elf",
    sex=CharacterSex.MALE,
    culture="Mirkwood",
    stats=Stats(strength=14, constitution=12, agility=18, intelligence=15, wisdom=16, charisma=14),
    skills=Skills(combat={"archery": 9, "sword_combat": 6}),
    combat_stats=CombatStats(max_hit_points=50, current_hit_points=50, max_mana_points=20, current_mana_points=20, armor_class=19, attack_bonus=4),
    equipment=Equipment(gold=200),
    spells=Spells(),
    level=4,
    status=CharacterStatus.ACTIVE,
    experience_points=3200,
    physical_description="Graceful elf with sharp features and pointed ears."
)


def test_list_characters_success(mock_data_service):
    """
    Test successful listing of characters.
    """
    # Override return value
    mock_data_service.get_all_characters.return_value = [MOCK_CHARACTER_1, MOCK_CHARACTER_2]

    response = client.get("/api/characters/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "Aragorn"
    assert data[1]["name"] == "Legolas"

    mock_data_service.get_all_characters.assert_awaited_once()


def test_list_characters_empty(mock_data_service):
    """
    Test listing characters when no characters exist.
    """
    mock_data_service.get_all_characters.return_value = []

    response = client.get("/api/characters/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

    mock_data_service.get_all_characters.assert_awaited_once()


def test_list_characters_service_error(mock_data_service):
    """
    Test listing characters when service raises an exception.
    """
    mock_data_service.get_all_characters.side_effect = Exception("Database error")

    response = client.get("/api/characters/")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Erreur lors de la récupération des personnages" in data["detail"]

    mock_data_service.get_all_characters.assert_awaited_once()


def test_get_character_detail_success(mock_data_service):
    """
    Test successful retrieval of character details.
    """
    # Mock the persistence service to return our character
    mock_data_service.load_character.return_value = MOCK_CHARACTER_1

    character_id = str(MOCK_CHARACTER_1.id)
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "loaded"
    assert data["character"]["id"] == character_id
    assert data["character"]["name"] == "Aragorn"
    assert data["character"]["race"] == "Human"
    assert data["character"]["culture"] == "Gondor"
    assert data["character"]["combat_stats"]["current_hit_points"] == 60
    assert data["character"]["equipment"]["gold"] == 100

    # Verify the service was called
    mock_data_service.load_character.assert_awaited_once()


def test_get_character_detail_not_found(mock_data_service):
    """
    Test retrieval of non-existent character.
    """
    character_id = str(uuid4())
    # Mock the persistence service to raise FileNotFoundError
    mock_data_service.load_character.side_effect = FileNotFoundError(f"Character {character_id} does not exist.")
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert character_id in data["detail"]

    mock_data_service.load_character.assert_awaited_once()


def test_get_character_detail_service_error(mock_data_service):
    """
    Test character detail retrieval when service raises unexpected error.
    """
    # Mock the persistence service to raise an exception
    mock_data_service.load_character.side_effect = Exception("Unexpected error")

    character_id = str(uuid4())
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Character retrieval failed" in data["detail"]

    mock_data_service.load_character.assert_awaited_once()


def test_get_character_detail_invalid_uuid(mock_data_service):
    """
    Test character detail retrieval with invalid UUID format.
    """
    invalid_id = "not-a-uuid"
    # Configure mock to raise FileNotFoundError for this call
    # Note: The service raises FileNotFoundError if file missing, regardless of UUID format validity check in some layers.
    # If we want to test ValueError for invalid format, we'd raise ValueError.
    # The current test assertion expects 404 (Not Found).
    mock_data_service.load_character.side_effect = FileNotFoundError(f"Character {invalid_id} not found")

    response = client.get(f"/api/characters/{invalid_id}")

    # The service tries to load the character, but since it's not a valid UUID, it becomes a FileNotFoundError
    # Or proper handling leads to 404.
    assert response.status_code == 404  # Not found


def test_get_character_detail_empty_id():
    """
    Test character detail retrieval with empty ID.
    """
    response = client.get("/api/characters/")

    # This should route to list_characters, not get_character_detail
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_character_detail_with_inventory(mock_data_service):
    """
    Test character detail retrieval with complex inventory data.
    """
    character_with_inventory = MOCK_CHARACTER_1.model_copy()
    character_with_inventory.equipment.weapons = [
        EquipmentItem(
            id=str(uuid4()),
            item_id="weapon_longsword",
            name="Longsword",
            category="weapons",
            cost_gold=150, cost_silver=0, cost_copper=0,
            weight=1.5,
            quantity=1,
            equipped=True,
            damage="1d8+4"
        )
    ]
    character_with_inventory.equipment.armor = [
        EquipmentItem(
            id=str(uuid4()),
            item_id="armor_chainmail",
            name="Chain Mail",
            category="armor",
            cost_gold=300, cost_silver=0, cost_copper=0,
            weight=10.0,
            quantity=1,
            equipped=True,
            protection=4
        )
    ]

    mock_data_service.load_character.return_value = character_with_inventory

    character_id = str(character_with_inventory.id)
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "loaded"
    assert "equipment" in data["character"]
    assert len(data["character"]["equipment"]["weapons"]) == 1
    assert len(data["character"]["equipment"]["armor"]) == 1
    assert data["character"]["equipment"]["weapons"][0]["name"] == "Longsword"


def test_get_character_detail_with_spells(mock_data_service):
    """
    Test character detail retrieval with spell data.
    """
    character_with_spells = MOCK_CHARACTER_1.model_copy()
    character_with_spells.spells.known_spells = ["fireball", "heal", "shield"]
    character_with_spells.spells.spell_slots = {1: 3, 2: 2}

    mock_data_service.load_character.return_value = character_with_spells

    character_id = str(character_with_spells.id)
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "loaded"
    assert "spells" in data["character"]
    assert len(data["character"]["spells"]["known_spells"]) == 3
    assert data["character"]["spells"]["spell_slots"]["1"] == 3


def test_get_character_detail_draft_status(mock_data_service):
    """
    Test character detail retrieval for character in draft status.
    """
    draft_character = MOCK_CHARACTER_1.model_copy()
    draft_character.status = CharacterStatus.DRAFT

    mock_data_service.load_character.return_value = draft_character

    character_id = str(draft_character.id)
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "loaded"
    assert data["character"]["status"] == "draft"


def test_list_characters_with_mixed_status(mock_data_service):
    """
    Test listing characters with mixed statuses.
    """
    active_char = MOCK_CHARACTER_1.model_copy()
    active_char.status = CharacterStatus.ACTIVE

    draft_char = MOCK_CHARACTER_2.model_copy()
    draft_char.status = CharacterStatus.DRAFT

    mock_data_service.get_all_characters.return_value = [active_char, draft_char]

    response = client.get("/api/characters/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["status"] == "active"
    assert data[1]["status"] == "draft"


def test_get_character_detail_max_level(mock_data_service):
    """
    Test character detail retrieval for max level character.
    """
    max_level_char = MOCK_CHARACTER_1.model_copy()
    max_level_char.level = 20
    max_level_char.experience_points = 100000

    mock_data_service.load_character.return_value = max_level_char

    character_id = str(max_level_char.id)
    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "loaded"
    assert data["character"]["level"] == 20
    assert data["character"]["experience_points"] == 100000


def test_list_characters_large_dataset(mock_data_service):
    """
    Test listing a large number of characters.
    """
    characters = [MOCK_CHARACTER_1.model_copy() for _ in range(50)]
    for i, char in enumerate(characters):
        char.id = uuid4()
        char.name = f"Character {i+1}"

    mock_data_service.get_all_characters.return_value = characters

    response = client.get("/api/characters/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 50
    assert data[0]["name"] == "Character 1"
    assert data[49]["name"] == "Character 50"


def test_delete_character_success(mock_data_service):
    """
    Test successful deletion of a character.
    """
    character_id = str(uuid4())
    # Mock the persistence service to return a character (exists)
    mock_data_service.load_character.return_value = MOCK_CHARACTER_1

    response = client.delete(f"/api/characters/{character_id}")

    assert response.status_code == 204
    # Verify both methods were called
    mock_data_service.load_character.assert_awaited_once()
    mock_data_service.delete_character.assert_awaited_once()


def test_delete_character_not_found(mock_data_service):
    """
    Test deletion of non-existent character.
    """
    character_id = str(uuid4())
    # Mock the persistence service to raise FileNotFoundError (character not found)
    mock_data_service.load_character.side_effect = FileNotFoundError(f"Character {character_id} does not exist.")

    response = client.delete(f"/api/characters/{character_id}")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert character_id in data["detail"]
    # Ensure delete was not called
    mock_data_service.delete_character.assert_not_called()