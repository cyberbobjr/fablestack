from uuid import uuid4

from back.models.domain.character import (Character, CharacterStatus,
                                          CombatStats, Equipment, Skills,
                                          Spells, Stats)
from back.models.domain.combat_state import (Combatant, CombatantType,
                                             CombatState)
from back.models.domain.npc import NPC
from back.models.service.dtos import CombatSummary, ParticipantSummary
from back.services.combat_service import CombatService


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

def make_npc_obj(name="Goblin", hp=10, ac=12):
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

def make_participant(name, type, hp=10):
    if type == CombatantType.NPC:
        ref = make_npc_obj(name, hp)
        return Combatant(
            id=uuid4(),
            name=name,
            type=type,
            current_hit_points=hp,
            max_hit_points=hp,
            armor_class=10,
            initiative_roll=10,
            npc_ref=ref
        )
    else:
        ref = make_character(name, hp)
        return Combatant(
            id=uuid4(),
            name=name,
            type=type,
            current_hit_points=hp,
            max_hit_points=hp,
            armor_class=10,
            initiative_roll=10,
            character_ref=ref
        )

class TestCombatSummary:
    def test_get_combat_summary(self):
        """Test generating a combat summary DTO."""
        from unittest.mock import MagicMock
        races_mock = MagicMock()
        data_mock = MagicMock()
        combat_service = CombatService(races_mock, data_mock)
        
        attacker = make_participant("Attacker", CombatantType.NPC)
        target = make_participant("Target", CombatantType.PLAYER)
        
        state = CombatState(
            participants=[attacker, target], 
            turn_order=[attacker.id, target.id],
            current_turn_combatant_id=attacker.id,
            round_number=1,
            is_active=True,
            log=["Combat started"]
        )
        
        # We need mock EquipmentManager if CombatService init uses it?
        # CombatService init imports EquipmentManager.
        # But here we just use get_combat_summary which is a simple transformation.
        
        summary = combat_service.get_combat_summary(state)
        
        assert isinstance(summary, CombatSummary)
        assert summary.combat_id == str(state.id)
        assert summary.round == 1
        assert summary.status == "ongoing"
        assert len(summary.participants) == 2
        
        p_summary = summary.participants[0]
        assert isinstance(p_summary, ParticipantSummary)
        assert p_summary.name == "Attacker"
        assert p_summary.camp == "enemy" # NPC -> enemy
        
        p2_summary = summary.participants[1]
        assert p2_summary.name == "Target"
        assert p2_summary.camp == "player" # PLAYER -> player
        
        assert summary.current_turn == str(attacker.id)
        assert "Combat started" in summary.log
