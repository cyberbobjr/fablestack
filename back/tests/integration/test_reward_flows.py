"""
Integration tests for reward flows (XP and gold).
"""

import pytest

from back.services.character_data_service import CharacterDataService
from back.services.character_service import CharacterService
from back.services.game_session_service import GameSessionService
from back.tests.integration.helpers import load_character_from_file


@pytest.mark.asyncio
async def test_add_xp(temp_data_dir, test_character):
    """Test adding XP to character with real persistence"""
    character_id, character_data = test_character
    
    # Initialize services
    data_service = CharacterDataService()
    char_service = CharacterService(character_id, data_service=data_service)
    await char_service.load()
    
    # Initial state
    assert char_service.get_character().experience_points == 0
    
    # Add XP
    await char_service.apply_xp(100)
    
    # Verify in-memory state
    updated_character = char_service.get_character()
    assert updated_character.experience_points == 100
    
    # Verify persistence
    saved_data = load_character_from_file(temp_data_dir, character_id)
    assert saved_data["experience_points"] == 100


@pytest.mark.asyncio
async def test_add_currency_flow(temp_data_dir, test_character):
    character_id, character_data = test_character
    
    # 1. Initialize Service using create factory
    from unittest.mock import MagicMock

    from back.agents.translation_agent import TranslationAgent
    from back.services.character_data_service import CharacterDataService
    from back.services.equipment_service import EquipmentService
    from back.services.races_data_service import RacesDataService
    from back.services.settings_service import SettingsService

    data_service = CharacterDataService()
    mock_settings = MagicMock(spec=SettingsService)
    mock_races = MagicMock(spec=RacesDataService)
    mock_translation = MagicMock(spec=TranslationAgent)
    mock_equipment = MagicMock(spec=EquipmentService)

    session_service = await GameSessionService.create(
        "test_session_reward", 
        str(character_id), 
        "test_scenario.yaml",
        character_data_service=data_service,
        equipment_service=mock_equipment,
        settings_service=mock_settings,
        races_service=mock_races,
        translation_agent=mock_translation
    )
    char_service = session_service.character_service
    
    # 2. Add Gold
    initial_gold = char_service.character_data.gold
    await char_service.add_currency(gold=50)
    
    # Verify in-memory state
    updated_character = char_service.get_character()
    assert updated_character.equipment.gold == initial_gold + 50
    
    # Verify persistence
    saved_data = load_character_from_file(temp_data_dir, character_id)
    assert saved_data["equipment"]["gold"] == initial_gold + 50


@pytest.mark.asyncio
async def test_add_xp_with_level_up(temp_data_dir, test_character):
    """Test adding enough XP to trigger level up"""
    character_id, character_data = test_character
    
    # Initialize services
    data_service = CharacterDataService()
    char_service = CharacterService(character_id, data_service=data_service)
    await char_service.load()
    
    # Add enough XP for level 2 (threshold is level * 1000, so 1 * 1000 = 1000 XP)
    await char_service.apply_xp(1000)
    
    # Verify level up
    updated_character = char_service.get_character()
    assert updated_character.experience_points == 1000
    assert updated_character.level == 2
    
    # Verify persistence
    saved_data = load_character_from_file(temp_data_dir, character_id)
    assert saved_data["level"] == 2
