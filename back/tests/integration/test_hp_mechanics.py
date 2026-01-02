"""
Integration tests for HP mechanics (damage and healing).
"""

import pytest

from back.services.character_data_service import CharacterDataService
from back.services.character_service import CharacterService
from back.tests.integration.helpers import load_character_from_file


@pytest.mark.asyncio
async def test_hp_mechanics(temp_data_dir, test_character):
    """Test damage and healing mechanics"""
    character_id, character_data = test_character
    
    # Initialize services
    data_service = CharacterDataService()
    char_service = CharacterService(character_id, data_service=data_service)
    await char_service.load()
    
    # Initial state
    char = char_service.get_character()
    max_hp = char.combat_stats.max_hit_points
    char.combat_stats.current_hit_points = max_hp
    await char_service.save_character()
    
    assert char.combat_stats.current_hit_points == max_hp
    assert char.hp == max_hp
    
    # 1. Test take_damage
    damage_amount = 10
    await char_service.take_damage(damage_amount)
    
    updated_char = char_service.get_character()
    expected_hp = max_hp - damage_amount
    
    assert updated_char.combat_stats.current_hit_points == expected_hp
    assert updated_char.hp == expected_hp
    
    # Verify persistence
    saved_data = load_character_from_file(temp_data_dir, character_id)
    assert saved_data["combat_stats"]["current_hit_points"] == expected_hp
    
    # 2. Test heal
    heal_amount = 5
    await char_service.heal(heal_amount)
    
    updated_char = char_service.get_character()
    expected_hp_after_heal = expected_hp + heal_amount
    
    assert updated_char.combat_stats.current_hit_points == expected_hp_after_heal
    assert updated_char.hp == expected_hp_after_heal
    
    # Verify persistence
    saved_data = load_character_from_file(temp_data_dir, character_id)
    assert saved_data["combat_stats"]["current_hit_points"] == expected_hp_after_heal
    
    # 3. Test overheal (should cap at max_hp)
    await char_service.heal(1000)
    
    updated_char = char_service.get_character()
    assert updated_char.combat_stats.current_hit_points == max_hp
    assert updated_char.hp == max_hp
    
    # 4. Test overkill (should cap at 0)
    await char_service.take_damage(1000)
    
    updated_char = char_service.get_character()
    assert updated_char.combat_stats.current_hit_points == 0
    assert updated_char.hp == 0
    assert not char_service.is_alive()
