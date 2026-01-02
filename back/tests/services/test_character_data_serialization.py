"""
Tests for Character serialization in CharacterDataService.
Validates that Character objects are correctly serialized to JSON and deserialized back.
"""

import json
import os
from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from back.models.domain.character import Character, CharacterStatus
from back.services.character_data_service import CharacterDataService


@pytest.fixture
def temp_characters_dir(tmp_path):
    """Create a temporary directory for character data and patch the service."""
    d = tmp_path / "characters"
    d.mkdir()
    # Patch get_data_dir to return tmp_path, so _get_characters_dir returns tmp_path/characters
    with patch('back.services.character_data_service.get_data_dir', return_value=str(tmp_path)):
        yield str(d)


@pytest.fixture
def sample_character():
    """Create a sample Character object for testing."""
    character_id: UUID = uuid4()
    now: str = datetime.now().isoformat()
    
    character_dict = {
        "id": str(character_id),
        "name": "Test Character",
        "race": "humans",
        "culture": "gondorians",
        "stats": {
            "strength": 15,
            "constitution": 14,
            "agility": 13,
            "intelligence": 12,
            "wisdom": 16,
            "charisma": 15
        },
        "skills": {
            "combat": {
                "melee_weapons": 5,
                "archery": 3
            },
            "general": {
                "perception": 4
            }
        },
        "combat_stats": {
            "max_hit_points": 140,
            "current_hit_points": 140,
            "max_mana_points": 112,
            "current_mana_points": 112,
            "armor_class": 11,
            "attack_bonus": 2
        },
        "equipment": {
            "weapons": [],
            "armor": [],
            "accessories": [],
            "consumables": [],
            "gold": 100
        },
        "spells": {
            "known_spells": [],
            "spell_slots": {},
            "spell_bonus": 0
        },
        "level": 1,
        "status": "active",
        "experience_points": 0,
        "created_at": now,
        "updated_at": now,
        "description": "A brave warrior from Gondor",
        "physical_description": "Tall with dark hair"
    }
    
    return Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", **character_dict)


@pytest.mark.asyncio
async def test_save_character_object_success(temp_characters_dir, sample_character):
    """
    Test that a Character object is successfully saved to JSON with proper serialization.
    """
    character_id: str = str(sample_character.id)
    
    # Save the Character object
    result: Character = await CharacterDataService().save_character(sample_character, character_id)
    
    # Verify the file was created
    expected_file: str = os.path.join(temp_characters_dir, f"{character_id}.json")
    assert os.path.exists(expected_file), "Character file should be created"
    
    # Verify the content is valid JSON
    with open(expected_file, 'r', encoding='utf-8') as f:
        saved_data: dict = json.load(f)
    
    # Verify all fields are present and correctly serialized
    assert saved_data["id"] == character_id, "ID should be serialized as string"
    assert saved_data["name"] == "Test Character"
    assert saved_data["race"] == "humans"
    assert saved_data["status"] == "active", "Enum should be serialized as string"
    assert isinstance(saved_data["stats"], dict), "Stats should be a dict"
    assert isinstance(saved_data["skills"], dict), "Skills should be a dict"
    
    # Verify the returned Character matches the saved one
    assert result.id == sample_character.id
    assert result.name == sample_character.name


@pytest.mark.asyncio
async def test_save_and_load_character_roundtrip(temp_characters_dir, sample_character):
    """
    Test that a Character can be saved and loaded back with all data intact.
    """
    character_id: str = str(sample_character.id)
    
    # Save the Character
    await CharacterDataService().save_character(sample_character, character_id)
    
    # Load it back
    loaded_character: Character = await CharacterDataService().load_character(character_id)
    
    # Verify all critical fields match
    assert loaded_character.id == sample_character.id
    assert loaded_character.name == sample_character.name
    assert loaded_character.race == sample_character.race
    assert loaded_character.culture == sample_character.culture
    assert loaded_character.status == sample_character.status
    assert loaded_character.stats.strength == sample_character.stats.strength
    assert loaded_character.level == sample_character.level
    assert loaded_character.experience_points == sample_character.experience_points


@pytest.mark.asyncio
async def test_save_character_with_uuid_serialization(temp_characters_dir, sample_character):
    """
    Test that UUID fields are properly serialized to strings in JSON.
    """
    character_id: str = str(sample_character.id)
    
    # Save the Character
    await CharacterDataService().save_character(sample_character, character_id)
    
    # Read the raw JSON file
    expected_file: str = os.path.join(temp_characters_dir, f"{character_id}.json")
    with open(expected_file, 'r', encoding='utf-8') as f:
        saved_data: dict = json.load(f)
    
    # Verify UUID is stored as string, not as UUID object
    assert isinstance(saved_data["id"], str), "UUID should be serialized as string"
    assert saved_data["id"] == character_id


@pytest.mark.asyncio
async def test_save_character_with_enum_serialization(temp_characters_dir, sample_character):
    """
    Test that Enum fields (CharacterStatus) are properly serialized to strings.
    """
    character_id: str = str(sample_character.id)
    
    # Ensure the character has an ACTIVE status
    sample_character.status = CharacterStatus.ACTIVE
    
    # Save the Character
    await CharacterDataService().save_character(sample_character, character_id)
    
    # Read the raw JSON file
    expected_file: str = os.path.join(temp_characters_dir, f"{character_id}.json")
    with open(expected_file, 'r', encoding='utf-8') as f:
        saved_data: dict = json.load(f)
    
    # Verify status is stored as string
    assert isinstance(saved_data["status"], str), "Enum should be serialized as string"
    assert saved_data["status"] == "active"


@pytest.mark.asyncio
async def test_save_character_merge_behavior(temp_characters_dir, sample_character):
    """
    Test that saving a character merges with existing data without losing fields.
    """
    character_id: str = str(sample_character.id)
    
    # Save initial character
    await CharacterDataService().save_character(sample_character, character_id)
    
    # Modify the character
    sample_character.name = "Updated Name"
    sample_character.level = 2
    
    # Save again
    await CharacterDataService().save_character(sample_character, character_id)
    
    # Load and verify
    loaded_character: Character = await CharacterDataService().load_character(character_id)
    
    assert loaded_character.name == "Updated Name", "Name should be updated"
    assert loaded_character.level == 2, "Level should be updated"
    assert loaded_character.race == sample_character.race, "Other fields should remain"
    assert loaded_character.stats.strength == sample_character.stats.strength, "Stats should remain"


@pytest.mark.asyncio
async def test_save_character_updates_status_correctly(temp_characters_dir):
    """
    Test that saving a character with DRAFT status and then ACTIVE status persists correctly.
    """
    character_id: UUID = uuid4()
    now: str = datetime.now().isoformat()
    
    # Create a draft character
    draft_dict = {
        "id": str(character_id),
        "name": "Draft Character",
        "race": "humans",
        "culture": "gondorians",
        "stats": {
            "strength": 10,
            "constitution": 10,
            "agility": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        },
        "skills": {},
        "combat_stats": {
            "max_hit_points": 100,
            "current_hit_points": 100,
            "max_mana_points": 80,
            "current_mana_points": 80,
            "armor_class": 10,
            "attack_bonus": 0
        },
        "equipment": {"weapons": [], "armor": [], "accessories": [], "consumables": [], "gold": 0},
        "spells": {"known_spells": [], "spell_slots": {}, "spell_bonus": 0},
        "level": 1,
        "status": "draft",
        "experience_points": 0,
        "created_at": now,
        "updated_at": now,
        "description": None,
        "physical_description": None
    }
    
    draft_character: Character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", **draft_dict)
    
    # Save as draft
    await CharacterDataService().save_character(draft_character, str(character_id))
    
    # Verify status is draft
    loaded: Character = await CharacterDataService().load_character(str(character_id))
    assert loaded.status == CharacterStatus.DRAFT
    
    # Update to active
    draft_character.status = CharacterStatus.ACTIVE
    draft_character.description = "Now complete"
    draft_character.physical_description = "Fully described"
    
    # Save again
    await CharacterDataService().save_character(draft_character, str(character_id))
    
    # Verify status is now active
    loaded_active: Character = await CharacterDataService().load_character(str(character_id))
    assert loaded_active.status == CharacterStatus.ACTIVE
    assert loaded_active.description == "Now complete"
    assert loaded_active.physical_description == "Fully described"


@pytest.mark.asyncio
async def test_save_character_auto_detects_id(temp_characters_dir, sample_character):
    """
    Test that save_character uses the character's ID if the character_id argument is missing or empty.
    """
    # Case 1: character_id is None
    saved_char = await CharacterDataService().save_character(sample_character, None)
    assert saved_char.id == sample_character.id
    assert os.path.exists(os.path.join(temp_characters_dir, f"{sample_character.id}.json"))
    
    # Case 2: character_id is empty string
    # We need to modify the ID to verify it uses the new one or overwrites
    new_id = uuid4()
    sample_character.id = new_id
    saved_char_2 = await CharacterDataService().save_character(sample_character, "")
    assert saved_char_2.id == new_id
    assert os.path.exists(os.path.join(temp_characters_dir, f"{new_id}.json"))


@pytest.mark.asyncio
async def test_save_character_raises_error_if_no_id():
    """
    Test that saving raises ValueError if no ID can be determined.
    """
    # Create a dummy object without ID
    class DummyChar:
        def model_dump(self, mode='json'):
            return {"name": "No ID"}
            
    dummy = DummyChar()
    
    with pytest.raises(ValueError, match="No character_id provided"):
        await CharacterDataService().save_character(dummy, None)
