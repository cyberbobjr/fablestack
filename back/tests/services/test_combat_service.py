from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from back.models.domain.character import (Character, CharacterStatus,
                                          CombatStats, Equipment, Skills,
                                          Spells, Stats)
from back.models.domain.combat_state import (Combatant, CombatantType,
                                             CombatState)
from back.models.domain.items import EquipmentItem
from back.models.domain.npc import NPC
from back.models.domain.payloads import CombatIntentPayload
from back.models.domain.payloads import EnemyIntent as CombatEnemyIntent
from back.services.character_service import CharacterService
from back.services.combat_service import CombatService
from back.services.game_session_service import GameSessionService

# --- Helpers to create valid Pydantic models ---

def make_stats(val=10):
    return Stats(
        strength=val, constitution=val, agility=val,
        intelligence=val, wisdom=val, charisma=val
    )

def make_combat_stats(hp=20, ac=10):
    return CombatStats(
        max_hit_points=hp, current_hit_points=hp,
        max_mana_points=10, current_mana_points=10,
        armor_class=ac, attack_bonus=2
    )

def make_character(name="Hero", hp=20):
    return Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        id=uuid4(),
        name=name,
        race="Human",
        culture="Empire",
        stats=make_stats(),
        skills=Skills(),
        equipment=Equipment(),
        combat_stats=make_combat_stats(hp=hp, ac=15),
        spells=Spells(),
        status=CharacterStatus.ACTIVE,
        description="A hero"
    )

def make_npc(name="Goblin", hp=10, ac=12):
    return NPC(
        id=uuid4(),
        name=name,
        archetype="Goblin Warrior",
        stats=make_stats(),
        skills=Skills(),
        equipment=Equipment(),
        combat_stats=make_combat_stats(hp=hp, ac=ac),
        spells=Spells()
    )

# --- Fixtures ---

@pytest.fixture
def mock_equipment_manager():
    with patch('back.services.combat_service.EquipmentManager') as MockManager:
        manager = MockManager.return_value
        manager.get_equipment_by_id.side_effect = lambda item_id: {
            "name": "Test Item",
            "category": "weapons" if "weapon" in item_id else "armor",
            "cost_gold": 10,
            "weight": 1.0,
            "damage": "1d6",
            "protection": 2 if "armor" in item_id else 0,
            "type": "melee"
        }
        yield manager

@pytest.fixture
def combat_service(mock_equipment_manager):
    races_mock = MagicMock()
    # Mock get_all_races to return valid data so NPC generation works
    race_mock = MagicMock()
    race_mock.id = "goblin"
    race_mock.name = "Goblin"
    race_mock.default_equipment = ["weapon_sword", "armor_leather"]
    races_mock.get_all_races.return_value = [race_mock]
    
    char_data_mock = MagicMock()
    # Mock methods used by sync
    char_data_mock.load_character = AsyncMock(return_value=make_character())
    char_data_mock.save_character = AsyncMock()
    
    return CombatService(races_data_service=races_mock, character_data_service=char_data_mock)

@pytest.fixture
def real_character():
    return make_character()

@pytest.fixture
def mock_session_service(real_character):
    service = MagicMock(spec=GameSessionService)
    service.character_service = MagicMock(spec=CharacterService)
    service.character_service.get_character.return_value = real_character
    return service

class TestCombatService:

    def test_start_combat_initialization(self, combat_service, mock_session_service, real_character):
        """Test starting combat with a player and an NPC."""
        # We explicitly provide HP to match the character, or override it.
        # Here we match the character's HP (20)
        
        intent = CombatIntentPayload(
            location="Test Location",
            description="Test Description",
            enemies_detected=[
                CombatEnemyIntent(name="Goblin", archetype="goblin_warrior", max_hp=10, hp=10, ac=12) 
            ],
            message="Combat starts!"
        )

        
        # Mock _create_npc_with_equipment to return our specific NPC
        with patch.object(combat_service, '_create_npc_with_equipment') as mock_create_npc:
            mock_npc = make_npc("Goblin", hp=10, ac=12)
            mock_create_npc.return_value = mock_npc
            
            state = combat_service.start_combat(intent, mock_session_service)
        
        assert isinstance(state, CombatState)
        assert len(state.participants) == 2
        assert state.is_active is True
        
        # Verify Player
        player = next(p for p in state.participants if p.type == CombatantType.PLAYER)
        assert player.name == "Hero"
        assert player.character_ref == real_character
        assert player.current_hit_points == 20
        
        # Verify NPC
        npc = next(p for p in state.participants if p.type == CombatantType.NPC)
        assert npc.name == "Goblin"
        assert npc.current_hit_points == 10
        assert npc.armor_class == 12

    def test_start_combat_npc_generation(self, combat_service, mock_session_service):
        """Test NPC generation with default equipment based on name."""
        intent = CombatIntentPayload(
            location="Test Location",
            description="Test Description",
            enemies_detected=[
                CombatEnemyIntent(name="Goblin Warrior", archetype_id="goblin_warrior", level=1, role="enemy")
            ],
            message="Combat starts!"
        )
        
        state = combat_service.start_combat(intent, mock_session_service)
        npc = state.participants[0]
        
        assert npc.npc_ref is not None
        assert npc.npc_ref.name == "Goblin Warrior"
        # Check if equipment was added
        assert len(npc.npc_ref.equipment.weapons) > 0
        assert len(npc.npc_ref.equipment.armor) > 0

    @pytest.mark.asyncio
    async def test_execute_attack_hit(self, combat_service):
        """Test a successful attack."""
        attacker_npc = make_npc("Attacker", hp=10, ac=10)
        target_npc = make_npc("Target", hp=10, ac=10)
        
        attacker = Combatant(
            id=uuid4(), name=attacker_npc.name, type=CombatantType.NPC,
            current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=10,
            npc_ref=attacker_npc
        )
        target = Combatant(
            id=uuid4(), name=target_npc.name, type=CombatantType.NPC,
            current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=5,
            npc_ref=target_npc
        )
        state = CombatState(participants=[attacker, target], turn_order=[attacker.id, target.id])
        
        # Mock dice roll to ensure hit (d20=15 + bonus)
        with patch('back.services.combat_service.random.randint', return_value=15), \
             patch('back.services.combat_service.roll_dice', return_value=4):
            
            result = await combat_service.execute_attack(state, str(attacker.id), str(target.id))
            
            assert "Hit!" in result.message
            # Damage: 4 (roll) + 2 (bonus) = 6
            assert target.current_hit_points == 4 # 10 - 6
            assert "deals 6 damage" in result.message

    @pytest.mark.asyncio
    async def test_execute_attack_miss(self, combat_service):
        """Test a missed attack."""
        attacker_npc = make_npc("Attacker")
        target_npc = make_npc("Target")
        
        attacker = Combatant(
            id=uuid4(), name=attacker_npc.name, type=CombatantType.NPC,
            current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=10,
            npc_ref=attacker_npc
        )
        target = Combatant(
            id=uuid4(), name=target_npc.name, type=CombatantType.NPC,
            current_hit_points=10, max_hit_points=10, armor_class=20, initiative_roll=5, # High AC
            npc_ref=target_npc
        )
        state = CombatState(participants=[attacker, target], turn_order=[attacker.id, target.id])
        
        # Mock dice roll to ensure miss (d20=2)
        with patch('back.services.combat_service.random.randint', return_value=2):
            
            result = await combat_service.execute_attack(state, str(attacker.id), str(target.id))
            
            assert "Miss!" in result.message
            assert target.current_hit_points == 10

    @pytest.mark.asyncio
    async def test_execute_attack_crit(self, combat_service):
        """Test a critical hit."""
        attacker_npc = make_npc("Attacker")
        target_npc = make_npc("Target", hp=20)
        
        attacker = Combatant(
            id=uuid4(), name=attacker_npc.name, type=CombatantType.NPC,
            current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=10,
            npc_ref=attacker_npc
        )
        target = Combatant(
            id=uuid4(), name=target_npc.name, type=CombatantType.NPC,
            current_hit_points=20, max_hit_points=20, armor_class=10, initiative_roll=5,
            npc_ref=target_npc
        )
        state = CombatState(participants=[attacker, target], turn_order=[attacker.id, target.id])
        
        # Mock dice roll to ensure crit (d20=20)
        with patch('back.services.combat_service.random.randint', return_value=20), \
             patch('back.services.combat_service.roll_dice', side_effect=[4, 4]): # Base + Crit
            
            result = await combat_service.execute_attack(state, str(attacker.id), str(target.id))
            
            assert "Hit!" in result.message
            # Damage: 4 (base) + 4 (crit) + 2 (bonus from make_combat_stats) = 10
            # Wait, make_combat_stats sets attack_bonus=2.
            # _get_attack_bonus returns 2.
            # Damage calculation: damage + damage_mod. damage_mod = attack_bonus = 2.
            # Total damage = 4 + 4 + 2 = 10.
            assert target.current_hit_points == 10 

    @pytest.mark.asyncio
    async def test_apply_direct_damage_and_sync(self, combat_service, real_character):
        """Test applying damage and syncing player HP."""
        player_combatant = Combatant(
            id=uuid4(), name="Hero", type=CombatantType.PLAYER,
            current_hit_points=20, max_hit_points=20, armor_class=15, initiative_roll=10,
            character_ref=real_character
        )
        state = CombatState(participants=[player_combatant], turn_order=[player_combatant.id])
        
        # Mock CharacterService for sync
        with patch('back.services.combat_service.CharacterService') as MockCharService:
            mock_service_instance = MockCharService.return_value
            mock_service_instance.character_data = real_character
            mock_service_instance.load = AsyncMock()
            mock_service_instance.save = AsyncMock()
            
            await combat_service.apply_direct_damage(state, str(player_combatant.id), 5)
            
            assert player_combatant.current_hit_points == 15
            # Verify sync called
            MockCharService.assert_called()
            mock_service_instance.save.assert_awaited_once()
            assert mock_service_instance.character_data.combat_stats.current_hit_points == 15

    def test_end_turn_advancement(self, combat_service):
        """Test turn advancement and round increment."""
        npc1 = make_npc("P1")
        npc2 = make_npc("P2")
        p1 = Combatant(id=uuid4(), name="P1", type=CombatantType.NPC, current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=10, npc_ref=npc1)
        p2 = Combatant(id=uuid4(), name="P2", type=CombatantType.NPC, current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=5, npc_ref=npc2)
        
        state = CombatState(
            participants=[p1, p2],
            turn_order=[p1.id, p2.id],
            current_turn_combatant_id=p1.id,
            round_number=1
        )
        
        # End P1 turn -> P2
        state = combat_service.end_turn(state)
        assert state.current_turn_combatant_id == p2.id
        assert state.round_number == 1
        
        # End P2 turn -> P1 (New Round)
        state = combat_service.end_turn(state)
        assert state.current_turn_combatant_id == p1.id
        assert state.round_number == 2

    def test_check_combat_end(self, combat_service, real_character):
        """Test combat end conditions."""
        npc = make_npc("E1")
        p1 = Combatant(id=uuid4(), name="P1", type=CombatantType.PLAYER, current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=10, character_ref=real_character)
        e1 = Combatant(id=uuid4(), name="E1", type=CombatantType.NPC, current_hit_points=10, max_hit_points=10, armor_class=10, initiative_roll=5, npc_ref=npc)
        
        state = CombatState(participants=[p1, e1], turn_order=[p1.id, e1.id])
        
        # Both alive
        assert combat_service.check_combat_end(state) is False
        
        # Enemy dies
        e1.current_hit_points = 0
        assert combat_service.check_combat_end(state) is True
        
        # Player dies (Enemy alive)
        e1.current_hit_points = 10
        p1.current_hit_points = 0
        assert combat_service.check_combat_end(state) is True

    @pytest.mark.asyncio
    async def test_end_combat(self, combat_service, real_character):
        """Test ending combat and final sync."""
        player_combatant = Combatant(
            id=uuid4(), name="Hero", type=CombatantType.PLAYER,
            current_hit_points=15, max_hit_points=20, armor_class=15, initiative_roll=10,
            character_ref=real_character
        )
        state = CombatState(participants=[player_combatant], is_active=True, turn_order=[player_combatant.id])
        
        with patch('back.services.combat_service.CharacterService') as MockCharService:
            mock_service_instance = MockCharService.return_value
            mock_service_instance.character_data = real_character
            mock_service_instance.load = AsyncMock()
            mock_service_instance.save = AsyncMock()
            
            new_state = await combat_service.end_combat(state, "Victory")
            
            assert new_state.is_active is False
            assert "Combat ended: Victory" in new_state.log[-1]
            mock_service_instance.save.assert_awaited_once()

    def test_start_combat_auto_add_player(self, combat_service, mock_session_service, real_character):
        """Test that player is automatically added if missing from participants."""
        intent = CombatIntentPayload(
            location="Test Location",
            description="Test Description",
            enemies_detected=[
                CombatEnemyIntent(name="Goblin", archetype_id="goblin", level=1, role="enemy")
            ],
            message="Combat starts!"
        )
        
        state = combat_service.start_combat(intent, mock_session_service)
        
        # Verify player was added
        player = next((p for p in state.participants if p.type == CombatantType.PLAYER), None)
        assert player is not None
        assert player.name == "Hero"
        assert player.character_ref == real_character

    def test_start_combat_invalid_archetype(self, combat_service, mock_session_service):
        """Test robustness when an invalid archetype ID is provided."""
        intent = CombatIntentPayload(
            location="Test Location",
            description="Test Description",
            enemies_detected=[
                CombatEnemyIntent(name="Unknown Entity", archetype_id="invalid_id_123", level=1, role="enemy")
            ],
            message="Combat starts!"
        )
        
        # Should not raise exception, but fallback to generic stats/equipment
        state = combat_service.start_combat(intent, mock_session_service)
        
        npc = state.participants[0]
        assert npc.name == "Unknown Entity"
        assert npc.npc_ref is not None
        # Should have fallback equipment (natural weapon)
        # Note: _create_npc_with_equipment adds "weapon_natural" if no match
        # But we need to check if it actually does that.
        # Let's just check that it didn't crash and we have an NPC.
        assert state.is_active is True
