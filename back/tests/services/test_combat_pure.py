from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from back.models.domain.character import Character, CombatStats, Skills, Stats
from back.models.domain.combat_state import (AttackResult, Combatant,
                                             CombatantType, CombatState)
from back.models.domain.items import EquipmentItem
from back.models.domain.npc import NPC
from back.services.combat_service import CombatService


@pytest.fixture
def combat_service():
    races_mock = MagicMock()
    races_mock.get_all_races.return_value = []
    
    char_data_mock = MagicMock()
    # Async mocks for I/O methods
    char_data_mock.load_character = AsyncMock() 
    char_data_mock.save_character = AsyncMock()
    
    return CombatService(races_data_service=races_mock, character_data_service=char_data_mock)

@pytest.fixture
def mock_combatant_player():
    char = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        id=uuid4(),
        name="Hero",
        race="Human",
        culture="Empire",
        skills=Skills(),
        stats=Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10),
        combat_stats=CombatStats(current_hit_points=20, max_hit_points=20, armor_class=10)
    )
    return Combatant(
        id=uuid4(),
        name="Hero",
        type=CombatantType.PLAYER,
        current_hit_points=20,
        max_hit_points=20,
        armor_class=10,
        initiative_roll=15,
        character_ref=char
    )

@pytest.fixture
def mock_combatant_npc():
    npc = NPC(
        id=uuid4(),
        name="Goblin",
        archetype="Goblin Warrior",
        stats=Stats(strength=8, constitution=8, agility=12, intelligence=8, wisdom=8, charisma=6),
        combat_stats=CombatStats(current_hit_points=10, max_hit_points=10, armor_class=8)
    )
    return Combatant(
        id=uuid4(),
        name="Goblin",
        type=CombatantType.NPC,
        current_hit_points=10,
        max_hit_points=10,
        armor_class=8,
        initiative_roll=5,
        npc_ref=npc
    )

@pytest.mark.asyncio
@patch('back.services.combat_service.roll_dice')
@patch('back.services.combat_service.random.randint')
async def test_execute_attack_hit(mock_randint, mock_roll, combat_service, mock_combatant_player, mock_combatant_npc):
    # Mock dice rolls:
    # random.randint used for d20 attack roll
    mock_randint.return_value = 15
    # roll_dice used for damage
    mock_roll.return_value = 4
    
    # Setup mock weapon (Sword) - Real Object
    sw_id = uuid4()
    sword = EquipmentItem(
        id=str(sw_id),
        item_id="longsword",
        name="Longsword", 
        damage="1d8", 
        type="melee", 
        quantity=1,
        category="weapon",
        weight=1.0,
        equipped=True
    )
    mock_combatant_player.character_ref.equipment.weapons = [sword]
    
    # Create CombatState
    state = CombatState(
        participants=[mock_combatant_player, mock_combatant_npc],
        is_active=True,
        log=[]
    )
    
    result = await combat_service.execute_attack(state, str(mock_combatant_player.id), str(mock_combatant_npc.id))
    
    assert result.is_hit is True
    assert result.is_crit is False
    assert result.damage == 4
    assert "hero deals 4 damage to goblin using longsword" in result.message.lower()
    assert "Hit!" in result.message
    
    # Check HP reduction
    # Note: execute_attack might return result but caller applies damage?
    # No, combat_service.apply_damage should be called or implied.
    # Let's check combat_service code. 
    # If execute_attack is pure calculation, it shouldn't mutate?
    # Wait, implementation earlier (Step 406 snippet) showed it is deterministic helper.
    # I need to verify if execute_attack MUTATES state or just RETURNS result.
    # Usually helpers return result, and mutation happens in specific combat tools?
    # PURE PYTHON SERVICE LAYER should probably mutate provided objects if designed that way.
    # Let's verify result first.

@pytest.mark.asyncio
@patch('back.services.combat_service.roll_dice')
@patch('back.services.combat_service.random.randint')
async def test_execute_attack_miss(mock_randint, mock_roll, combat_service, mock_combatant_player, mock_combatant_npc):
    # Mock dice rolls:
    # 1. Attack Roll: 1d20 -> 2 (Miss AC 8 usually)
    mock_randint.return_value = 2
    mock_roll.return_value = 0 # Not used on miss but safe
    
    # Create CombatState
    state = CombatState(
        participants=[mock_combatant_player, mock_combatant_npc],
        is_active=True,
        log=[]
    )
    
    result = await combat_service.execute_attack(state, str(mock_combatant_player.id), str(mock_combatant_npc.id))
    
    assert result.is_hit is False
    assert result.damage == 0
    assert "Miss" in result.message

@pytest.mark.asyncio
@patch('back.services.combat_service.roll_dice')
@patch('back.services.combat_service.random.randint')
async def test_execute_attack_critical(mock_randint, mock_roll, combat_service, mock_combatant_player, mock_combatant_npc):
    # Mock dice rolls:
    # 1. Attack Roll: 20 (Critical)
    mock_randint.return_value = 20
    
    # 2. Damage Roll: 1d6 -> 4
    # 3. Crit Damage Roll: 1d6 -> 3
    mock_roll.side_effect = [4, 3]
    
    # Create CombatState
    state = CombatState(
        participants=[mock_combatant_player, mock_combatant_npc],
        is_active=True,
        log=[]
    )
    
    result = await combat_service.execute_attack(state, str(mock_combatant_player.id), str(mock_combatant_npc.id))
    
    assert result.is_hit is True
    assert result.is_crit is True
    assert result.damage == 7 # 4 + 3
    assert "Critical Hit!" in result.message
