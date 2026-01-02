"""Combat round tests between player characters and NPCs."""
from __future__ import annotations

from typing import List

import pytest

from back.models.domain.character import (
    Character,
    CharacterStatus,
    CombatStats,
    Equipment,
    Skills,
    Spells,
    Stats,
)
from back.models.domain.combat_state import CombatState, Combatant, CombatantType
from back.models.domain.npc import NPC


def make_stats(value: int = 12) -> Stats:
    return Stats(
        strength=value,
        constitution=value,
        agility=value,
        intelligence=value,
        wisdom=value,
        charisma=value,
    )


def make_combat_stats(base_hp: int = 20, armor_class: int = 14) -> CombatStats:
    return CombatStats(
        max_hit_points=base_hp,
        current_hit_points=base_hp,
        max_mana_points=10,
        current_mana_points=10,
        armor_class=armor_class,
        attack_bonus=3,
    )


def make_character(name: str) -> Character:
    return Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        name=name,
        race="Human",
        culture="Gondor",
        stats=make_stats(14),
        skills=Skills(),
        equipment=Equipment(),
        combat_stats=make_combat_stats(28, armor_class=16),
        spells=Spells(),
        status=CharacterStatus.ACTIVE,
        description=f"{name} the Bold",
        physical_description="Tall and vigilant",
    )


def make_npc(name: str, level: int = 1) -> NPC:
    return NPC(
        name=name,
        description=f"{name} prowling the battlefield",
        stats=make_stats(11),
        skills=Skills(),
        equipment=Equipment(),
        combat_stats=make_combat_stats(18, armor_class=13),
        spells=Spells(),
        archetype="Goblin Warrior",
        level=level,
    )


def build_combatants(hero: Character, npc_count: int) -> List[Combatant]:
    participants: List[Combatant] = []
    hero_combatant = Combatant(
        name=hero.name,
        type=CombatantType.PLAYER,
        current_hit_points=hero.combat_stats.current_hit_points,
        max_hit_points=hero.combat_stats.max_hit_points,
        armor_class=hero.combat_stats.armor_class,
        initiative_roll=17,
        character_ref=hero,
    )
    participants.append(hero_combatant)

    for i in range(npc_count):
        npc = make_npc(f"Goblin #{i+1}", level=1)
        npc_combatant = Combatant(
            name=npc.name,
            type=CombatantType.NPC,
            current_hit_points=npc.combat_stats.current_hit_points,
            max_hit_points=npc.combat_stats.max_hit_points,
            armor_class=npc.combat_stats.armor_class,
            initiative_roll=12 - i,
            npc_ref=npc,
        )
        participants.append(npc_combatant)
    return participants


@pytest.mark.parametrize("npc_count", [1, 2])
def test_combat_round_player_vs_npcs(npc_count: int) -> None:
    hero = make_character("Arandur")
    participants = build_combatants(hero, npc_count)
    turn_order = [combatant.id for combatant in participants]
    combat_state = CombatState(
        participants=participants,
        turn_order=turn_order,
        current_turn_combatant_id=turn_order[0],
        round_number=1,
        is_active=True,
        log=[],
    )

    # Player acts first and focuses on the first NPC.
    target = participants[1]
    dealt = target.take_damage(10)
    combat_state.add_log_entry(f"{participants[0].name} strikes {target.name} for {dealt} damage")
    assert dealt == 10
    assert target.current_hit_points == target.max_hit_points - 10
    assert target.npc_ref is not None
    assert target.npc_ref.name == target.name

    # Each NPC retaliates
    for npc_combatant in participants[1:]:
        combat_state.current_turn_combatant_id = npc_combatant.id
        damage_to_player = participants[0].take_damage(4)
        combat_state.add_log_entry(
            f"{npc_combatant.name} retaliates for {damage_to_player} damage"
        )
        assert damage_to_player == 4
        assert npc_combatant.is_alive()

    assert participants[0].character_ref is not None
    assert participants[0].current_hit_points == hero.combat_stats.max_hit_points - (4 * npc_count)
    # Ensure combat log captured each action (player + each NPC)
    assert len(combat_state.log) == 1 + npc_count