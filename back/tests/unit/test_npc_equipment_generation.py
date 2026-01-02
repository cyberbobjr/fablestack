from unittest.mock import MagicMock

import pytest

from back.models.domain.combat_state import CombatantType
from back.services.combat_service import CombatService


@pytest.fixture
def mock_combat_service():
    races_mock = MagicMock()
    # Setup mock races
    goblin = MagicMock()
    goblin.id = "goblin"
    goblin.name = "Goblin"
    goblin.default_equipment = ["weapon_scimitar", ["weapon_shortbow"], "armor_leather"]
    
    orc = MagicMock()
    orc.id = "orc"
    orc.name = "Orc"
    orc.default_equipment = ["weapon_greataxe", "armor_hide"]
    
    skeleton = MagicMock()
    skeleton.id = "skeleton"
    skeleton.name = "Skeleton"
    skeleton.default_equipment = ["weapon_shortsword"]
    
    races_mock.get_all_races.return_value = [goblin, orc, skeleton]
    
    char_data_mock = MagicMock()
    return CombatService(races_data_service=races_mock, character_data_service=char_data_mock)

@pytest.mark.asyncio
async def test_npc_equipment_generation(mock_combat_service):
    """
    Verify that NPCs get the correct equipment based on their race configuration.
    """
    combat_service = mock_combat_service
    
    # 1. Test Goblin (Should get Scimitar OR Shortbow and Leather Armor)
    goblin = combat_service._create_npc_with_equipment("Goblin Skirmisher", {"archetype": "Goblin"})
    assert any(w.item_id in ["weapon_scimitar", "weapon_shortbow"] for w in goblin.equipment.weapons)
    assert any(a.item_id == "armor_leather" for a in goblin.equipment.armor)
    
    # 2. Test Orc (Should get Greataxe OR Mace and Hide Armor)
    orc = combat_service._create_npc_with_equipment("Orc Warrior", {"archetype": "Orc"})
    assert any(w.item_id in ["weapon_greataxe", "weapon_mace"] for w in orc.equipment.weapons)
    assert any(a.item_id == "armor_hide" for a in orc.equipment.armor)
    
    # 3. Test Skeleton (Should get Shortsword)
    skeleton = combat_service._create_npc_with_equipment("Risen Skeleton", {"archetype": "Skeleton"})
    assert any(w.item_id == "weapon_shortsword" for w in skeleton.equipment.weapons)
    
    # 4. Test Unknown (Should get Natural Weapon)
    unknown = combat_service._create_npc_with_equipment("Unknown Beast", {"archetype": "Monster"})
    assert any(w.item_id == "weapon_natural" for w in unknown.equipment.weapons)
