from uuid import uuid4

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Spells, Stats)
from back.models.domain.items import EquipmentItem
from back.models.enums import CharacterStatus


def _build_sample_character() -> Character:
    # Inline type annotations for all local variables (project standard)
    stats: Stats = Stats(
        strength=14,
        constitution=13,
        agility=12,
        intelligence=11,
        wisdom=10,
        charisma=9
    )
    combat_stats: CombatStats = Character.calculate_combat_stats(stats, level=2)
    skills: Skills = Skills(combat={"weapon_handling": 5, "combat_style": 3}, general={"perception": 4})
    equipment: Equipment = Equipment(
        weapons=[EquipmentItem(id="w1", item_id="weapon_longsword", name="longsword", category="weapon", cost_gold=15, cost_silver=0, cost_copper=0, weight=2, quantity=1, equipped=True, damage="1d8")],
        armor=[EquipmentItem(id="a1", item_id="armor_leather", name="leather_armor", category="armor", cost_gold=10, cost_silver=0, cost_copper=0, weight=5, quantity=1, equipped=True, protection=2)],
        gold=25
    )
    spells: Spells = Spells(known_spells=["light"], spell_slots={1: 2}, spell_bonus=1)
    character: Character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        id=uuid4(),
        name="Testor",
        race="Human",
        culture="Ranger",
        level=2,
        stats=stats,
        skills=skills,
        equipment=equipment,
        combat_stats=combat_stats,
        spells=spells,
        status=CharacterStatus.ACTIVE,
        experience_points=1200,
        description="A wandering ranger",
        physical_description="Lean, weathered, grey-eyed"
    )
    return character


def test_narrative_prompt_block_contains_sections():
    character: Character = _build_sample_character()
    block: str = character.build_narrative_prompt_block()
    assert "Name: Testor" in block
    assert "Stats:" in block
    assert "Combat Stats:" in block
    assert "Equipment:" in block
    assert "Background:" in block
    assert "Physical Description:" in block
    # Verify skill IDs are used
    assert "weapon_handling" in block
    assert "combat_style" in block
    assert "perception" in block


def test_combat_prompt_block_contains_core_sections():
    character: Character = _build_sample_character()
    block: str = character.build_combat_prompt_block()
    assert "Combat Stats:" in block
    assert "Combat Skills:" in block
    assert "Equipped Weapons:" in block
    assert "Equipped Armor:" in block
    assert "Initiative Bonus:" in block
    # Verify skill IDs are used
    assert "weapon_handling" in block
    assert "combat_style" in block


def test_narrative_prompt_json_structure():
    character: Character = _build_sample_character()
    data: dict = character.build_narrative_prompt_json()
    assert data["name"] == "Testor"
    assert "stats" in data and isinstance(data["stats"], dict)
    assert "combat" in data and "hp" in data["combat"]
    assert "equipment" in data and "weapons" in data["equipment"]
    assert data["status"] == character.status.value


def test_combat_prompt_json_structure():
    character: Character = _build_sample_character()
    data: dict = character.build_combat_prompt_json()
    assert data["name"] == "Testor"
    assert "combat_stats" in data and "armor_class" in data["combat_stats"]
    assert "combat_skills" in data
    assert "equipped" in data and "weapons" in data["equipped"]
