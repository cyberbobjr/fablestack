"""
New Strict Pydantic Character Model v2.0
Simplified English-only naming for character creation

This module provides a simplified character model with:
- 400 stat points instead of 550
- 40 skill development points instead of 84
- 6 main stat attributes
- 6 skill groups
- Strict Pydantic validation
"""
from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

from back.models.domain.items import EquipmentItem
from back.models.enums import CharacterSex, CharacterStatus


class Stats(BaseModel):
    """
    Simplified statistics system
    6 main attributes with max 60 total points
    
    Point allocation rules:
    - Each stat ranges from 3 to 20
    - Total points must not exceed 60
    - Recommended distribution: 10 per stat for balanced characters
    """
    DEFAULT_ALLOCATION: ClassVar[Dict[str, int]] = {
        "strength": 10,
        "constitution": 10,
        "agility": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
    }

    strength: int = Field(..., ge=3, le=20, description="Physical power and melee damage")
    constitution: int = Field(..., ge=3, le=20, description="Health points and endurance")
    agility: int = Field(..., ge=3, le=20, description="Speed, reflexes, and dodge")
    intelligence: int = Field(..., ge=3, le=20, description="Magical power and learning")
    wisdom: int = Field(..., ge=3, le=20, description="Perception and willpower")
    charisma: int = Field(..., ge=3, le=20, description="Social influence and leadership")
    
    @field_validator('*')
    @classmethod
    def validate_stat_range(cls, v: int) -> int:
        """Ensure each stat is within valid range"""
        if not (3 <= v <= 20):
            raise ValueError(f"Stat must be between 3 and 20, got {v}")
        return v
    
    # Removed validate_total_points to allow racial bonuses to exceed 60 points
    # Validation is now handled in the creation router before bonuses are applied
    
    def calculate_total_points(self) -> int:
        """Calculate total allocated points"""
        return sum([
            self.strength,
            self.constitution,
            self.agility,
            self.intelligence,
            self.wisdom,
            self.charisma
        ])

    def is_default_allocation(self) -> bool:
        """Return True if stats still match the creation defaults"""
        return all(
            getattr(self, stat_name) == value
            for stat_name, value in self.DEFAULT_ALLOCATION.items()
        )
    
    def get_modifier(self, stat_name: str) -> int:
        """
        Calculate modifier for a given stat
        Simplified bonus table: (stat - 10) // 2
        """
        stat_value = getattr(self, stat_name.lower())
        return (stat_value - 10) // 2
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "strength": 14,
                "constitution": 16,
                "agility": 12,
                "intelligence": 13,
                "wisdom": 15,
                "charisma": 10
            }
        }
    )


class Skills(BaseModel):
    """
    Simplified skills system aligned with skill_groups.yaml
    6 main groups with 40 total development points

    Skill rules:
    - Each skill rank costs 1 development point
    - Skills range from 0 (untrained) to 10 (master)
    - Total development points: 40
    """
    artistic: Dict[str, int] = Field(
        default_factory=dict,
        description="Artistic skills (storytelling, music, dance, etc.)"
    )
    magic_arts: Dict[str, int] = Field(
        default_factory=dict,
        description="Magic arts skills (alchemy, runes, divination, etc.)"
    )
    athletic: Dict[str, int] = Field(
        default_factory=dict,
        description="Athletic skills (acrobatics, climbing, etc.)"
    )
    combat: Dict[str, int] = Field(
        default_factory=dict,
        description="Combat skills (melee, ranged, defense)"
    )

    general: Dict[str, int] = Field(
        default_factory=dict,
        description="General skills (crafting, knowledge, perception, etc.)"
    )

    @field_validator('artistic', 'magic_arts', 'athletic', 'combat', 'general')
    @classmethod
    def validate_skill_ranks(cls, v: Dict[str, int]) -> Dict[str, int]:
        """Ensure all skill ranks are between 0 and 15"""
        for skill_name, rank in v.items():
            if not (0 <= rank <= 15):
                raise ValueError(f"Skill rank for {skill_name} must be between 0 and 15, got {rank}")
        return v

    # Removed validate_total_development_points to allow racial/sex bonuses to exceed 40 points
    # Validation is now handled in the creation router before bonuses are applied


    def get_total_development_points(self) -> int:
        """Calculate total development points used"""
        total = 0
        for skill_group in [self.artistic, self.magic_arts, self.athletic,
                           self.combat, self.general]:
            total += sum(skill_group.values())
        return total

    def get_skill_rank(self, skill_name: str) -> int:
        """Get rank for a specific skill across all groups"""
        for group in [self.artistic, self.magic_arts, self.athletic,
                     self.combat, self.general]:
            if skill_name in group:
                return group[skill_name]
        return 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "artistic": {"storytelling": 5, "music_singing": 3},
                "magic_arts": {"alchemy": 4, "runes": 2},
                "athletic": {"acrobatics": 3, "climbing": 4},
                "combat": {"weapon_handling": 5, "combat_style": 3},

                "general": {"crafting": 5, "perception": 4, "general_knowledge": 3}
            }
        }
    )


class Equipment(BaseModel):
    """Simplified equipment system"""
    weapons: List[EquipmentItem] = Field(
        default_factory=list,
        description="Equipped weapons with stats"
    )
    armor: List[EquipmentItem] = Field(
        default_factory=list,
        description="Equipped armor pieces"
    )
    accessories: List[EquipmentItem] = Field(
        default_factory=list,
        description="Accessories and magical items"
    )
    consumables: List[EquipmentItem] = Field(
        default_factory=list,
        description="Consumable items (potions, scrolls)"
    )
    gold: int = Field(default=0, ge=0, description="Gold pieces")
    silver: int = Field(default=0, ge=0, description="Silver pieces")
    copper: int = Field(default=0, ge=0, description="Copper pieces")
    
    def get_total_weight(self) -> float:
        """Calculate total equipment weight"""
        total_weight = 0.0
        for item_list in [self.weapons, self.armor, self.accessories, self.consumables]:
            for item in item_list:
                total_weight += item.weight
        return total_weight

    def get_total_in_copper(self) -> int:
        """Calculate total wealth in copper pieces"""
        return (self.gold * 100) + (self.silver * 10) + self.copper

    def can_afford(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """Check if character can afford a cost (with automatic conversion)"""
        cost_in_copper = (gold * 100) + (silver * 10) + copper
        return self.get_total_in_copper() >= cost_in_copper

    def add_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> None:
        """Add currency to inventory"""
        self.gold += max(0, gold)
        self.silver += max(0, silver)
        self.copper += max(0, copper)

    def deduct_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """
        Deduct currency with automatic conversion.
        Returns True if successful, False if insufficient funds.
        Strategy: Convert everything to copper, deduct, then reconvert to G/S/C.
        """
        cost_in_copper = (gold * 100) + (silver * 10) + copper
        current_total = self.get_total_in_copper()
        
        if current_total < cost_in_copper:
            return False
            
        remaining = current_total - cost_in_copper
        
        # Convert back to G/S/C (greedy approach: max gold, then silver, then copper)
        self.gold = remaining // 100
        remaining %= 100
        self.silver = remaining // 10
        self.copper = remaining % 10
        
        return True
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "weapons": [
                    {"name": "longsword", "damage": "1d8", "weight": 5}
                ],
                "armor": [
                    {"name": "leather_armor", "defense": 2, "weight": 10}
                ],
                "accessories": [
                    {"name": "ring_of_power", "bonus": "+1 charisma"}
                ],
                "consumables": [
                    {"name": "health_potion", "quantity": 3, "effect": "heal 2d8"}
                ],
                "gold": 100,
                "silver": 5,
                "copper": 10
            }
        }
    )


class CombatStats(BaseModel):
    """
    Simplified combat statistics
    
    Calculation:
    - hit_points = constitution * 10 + level * 5
    - mana_points = intelligence * 5 + wisdom * 3
    - armor_class = 10 + agility_modifier + armor_bonus
    """
    max_hit_points: int = Field(..., ge=1, description="Maximum health")
    current_hit_points: int = Field(..., ge=0, description="Current health")
    max_mana_points: int = Field(default=0, ge=0, description="Maximum magical energy")
    current_mana_points: int = Field(default=0, ge=0, description="Current magical energy")
    armor_class: int = Field(default=10, ge=1, le=30, description="Defense rating")
    attack_bonus: int = Field(default=0, description="Base attack modifier")
    
    @model_validator(mode='after')
    def validate_current_stats(self) -> 'CombatStats':
        """Ensure current HP/MP don't exceed maximum"""
        if self.current_hit_points > self.max_hit_points:
            raise ValueError("Current HP cannot exceed maximum HP")
        if self.current_mana_points > self.max_mana_points:
            raise ValueError("Current MP cannot exceed maximum MP")
        return self
    
    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.current_hit_points > 0
    
    def heal(self, amount: int) -> int:
        """Heal character and return actual amount healed"""
        old_hp = self.current_hit_points
        self.current_hit_points = min(
            self.current_hit_points + amount,
            self.max_hit_points
        )
        return self.current_hit_points - old_hp
    
    def take_damage(self, amount: int) -> int:
        """Apply damage and return actual damage taken"""
        old_hp = self.current_hit_points
        self.current_hit_points = max(0, self.current_hit_points - amount)
        return old_hp - self.current_hit_points
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_hit_points": 50,
                "current_hit_points": 50,
                "max_mana_points": 30,
                "current_mana_points": 30,
                "armor_class": 15,
                "attack_bonus": 3
            }
        }
    )


class Spells(BaseModel):
    """
    Simplified magic system
    3 main spheres: Universal, Healer, Elemental
    """
    known_spells: List[str] = Field(
        default_factory=list,
        description="List of known spell names"
    )
    spell_slots: Dict[int, int] = Field(
        default_factory=dict,
        description="Available spell slots by level (1-9)"
    )
    spell_bonus: int = Field(default=0, description="Magic attack modifier")
    
    def can_cast_spell(self, spell_level: int) -> bool:
        """Check if character has available spell slot for given level"""
        return self.spell_slots.get(spell_level, 0) > 0
    
    def use_spell_slot(self, spell_level: int) -> bool:
        """Use a spell slot and return success status"""
        if self.can_cast_spell(spell_level):
            self.spell_slots[spell_level] -= 1
            return True
        return False
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "known_spells": ["fireball", "heal", "lightning_bolt", "shield"],
                "spell_slots": {"1": 4, "2": 3, "3": 2},
                "spell_bonus": 4
            }
        }
    )


class Character(BaseModel):
    """
    Simplified character model with strict Pydantic validation
    
    All fields in English for backend consistency.
    Simplified from original system:
    - 400 stat points 
    - 40 skill development points
    - 6 stat attributes
    - 6 skill groups
    """
    
    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique character identifier")
    user_id: UUID = Field(..., description="ID of the user who owns this character")
    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    race: str = Field(..., min_length=1, max_length=50, description="Character race")
    sex: CharacterSex = Field(..., description="Character biological sex")
    culture: str = Field(..., min_length=1, max_length=50, description="Character culture")
    level: int = Field(default=1, ge=1, le=20, description="Character level")
    
    # Core stats (simplified: 400 points)
    stats: Stats = Field(..., description="Character base statistics")
    
    # Skills (simplified: 40 development points)
    skills: Skills = Field(..., description="Character trained skills")
    
    # Game mechanics
    status: CharacterStatus = Field(default=CharacterStatus.DRAFT, description="Character lifecycle status")
    experience_points: int = Field(default=0, ge=0, description="Total experience points")
    
    # Equipment and inventory
    equipment: Equipment = Field(
        default_factory=Equipment,
        description="Character equipment and inventory"
    )
    
    # Combat and magic
    combat_stats: CombatStats = Field(..., description="Combat-related statistics")
    spells: Spells = Field(
        default_factory=Spells,
        description="Known spells and magic abilities"
    )

    # Descriptions
    physical_description: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Physical appearance description (height, build, features)"
    )
    physical_description_localized: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Localized physical appearance description"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    description: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Character background and description"
    )
    description_localized: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Localized character background and description"
    )
    portrait_url: Optional[str] = Field(
        default=None,
        description="URL of the character's generated portrait"
    )
    
    def update_timestamp(self) -> None:
        """Update the last modified timestamp"""
        self.updated_at = datetime.now(timezone.utc)
    
    def level_up(self) -> None:
        """
        Level up character
        - Increase level by 1
        - Update combat stats based on new level
        """
        if self.level < 20:
            self.level += 1
            # Recalculate HP and MP based on new level
            hp_increase = 5
            self.combat_stats.max_hit_points += hp_increase
            self.combat_stats.current_hit_points += hp_increase
            self.update_timestamp()
    
    def add_experience(self, amount: int) -> bool:
        """
        Add experience points and check for level up
        Returns True if character leveled up
        """
        self.experience_points += amount
        # Simple level up threshold: 1000 XP per level
        required_xp = self.level * 1000
        if self.experience_points >= required_xp:
            self.level_up()
            return True
        return False

    def is_complete(self) -> bool:
        """Determine if the character contains every mandatory section"""
        has_identity = bool(self.name and self.race and self.culture)
        stats_ready = not self.stats.is_default_allocation()
        full_skills = self.skills.get_total_development_points() >= 40
        has_background = bool(self.description)
        has_physical_description = bool(self.physical_description)
        return all([has_identity, stats_ready, full_skills, has_background, has_physical_description])

    def sync_status_from_completion(self) -> CharacterStatus:
        """Force the lifecycle status to match the completion state"""
        self.status = CharacterStatus.ACTIVE if self.is_complete() else CharacterStatus.DRAFT
        return self.status
    
    def calculate_initiative(self) -> int:
        """Calculate combat initiative bonus"""
        agility_mod = self.stats.get_modifier('agility')
        wisdom_mod = self.stats.get_modifier('wisdom')
        return agility_mod + (wisdom_mod // 2)
    
    def get_skill_check_bonus(self, skill_name: str, stat_name: str) -> int:
        """
        Calculate total bonus for a skill check
        Total = skill rank + stat modifier
        """
        skill_rank = self.skills.get_skill_rank(skill_name)
        stat_modifier = self.stats.get_modifier(stat_name)
        return skill_rank + stat_modifier

    @staticmethod
    def calculate_combat_stats(stats: Stats, level: int = 1) -> CombatStats:
        """
        Calculate combat stats based on core attributes and level.
        """
        strength_modifier = stats.get_modifier('strength')
        agility_modifier = stats.get_modifier('agility')
        
        max_hp = stats.constitution * 10 + level * 5
        max_mp = stats.intelligence * 5 + stats.wisdom * 3
        ac = 10 + agility_modifier
        attack_bonus = strength_modifier

        return CombatStats(
            max_hit_points=max_hp,
            current_hit_points=max_hp,
            max_mana_points=max_mp,
            current_mana_points=max_mp,
            armor_class=ac,
            attack_bonus=attack_bonus
        )

    # --- Compatibility properties for legacy services ---
    @property
    def xp(self) -> int:
        """Compat: maps legacy xp to experience_points"""
        return self.experience_points

    @xp.setter
    def xp(self, value: int) -> None:
        self.experience_points = max(0, int(value))

    @property
    def gold(self) -> int:
        """Compat: expose gold at character root (maps to equipment.gold)"""
        return self.equipment.gold

    @gold.setter
    def gold(self, value: int) -> None:
        self.equipment.gold = max(0, int(value))

    @property
    def silver(self) -> int:
        """Compat: expose silver at character root (maps to equipment.silver)"""
        return self.equipment.silver

    @silver.setter
    def silver(self, value: int) -> None:
        self.equipment.silver = max(0, int(value))

    @property
    def copper(self) -> int:
        """Compat: expose copper at character root (maps to equipment.copper)"""
        return self.equipment.copper

    @copper.setter
    def copper(self, value: int) -> None:
        self.equipment.copper = max(0, int(value))

    @property
    def hp(self) -> int:
        """Compat: expose current HP at character root (maps to combat_stats.current_hit_points)"""
        return self.combat_stats.current_hit_points

    @hp.setter
    def hp(self, value: int) -> None:
        value_int = max(0, int(value))
        self.combat_stats.current_hit_points = min(value_int, self.combat_stats.max_hit_points)

    def build_narrative_prompt_block(self) -> str:
        """
        ### build_narrative_prompt_block
        **Description:** Produce a rich multi-section textual representation of the character for narrative prompts.
        **Parameters:**
        - (none)
        **Returns:** A formatted string containing identity, stats, skills, combat stats, equipment and descriptions.
        """
        from typing import Any, Dict, List

        # Stats formatting
        stats_dict: Dict[str, int] = self.stats.model_dump()
        stats_lines: List[str] = [f"  - {stat.upper()}: {value}" for stat, value in stats_dict.items()]
        stats_block: str = "\n".join(stats_lines)

        # Skills formatting (all groups)
        skills_dict: Dict[str, Dict[str, int]] = self.skills.model_dump()
        skill_group_blocks: List[str] = []
        for group_name, group_skills in skills_dict.items():
            group_name_fmt: str = group_name.replace('_', ' ').title()
            if group_skills:
                # Use skill ID directly instead of formatted name
                group_skill_lines: List[str] = [f"    - {skill}: {rank}" for skill, rank in group_skills.items()]
                group_block: str = f"\n  {group_name_fmt}:\n" + "\n".join(group_skill_lines)
            else:
                group_block: str = f"\n  {group_name_fmt}:\n    - None"
            skill_group_blocks.append(group_block)
        skills_block: str = "".join(skill_group_blocks)

        # Equipment formatting
        equipment_dict: Dict[str, Any] = self.equipment.model_dump()
        weapons_names: List[str] = [w.get("name", "unknown") for w in equipment_dict.get("weapons", [])]
        armor_names: List[str] = [a.get("name", "unknown") for a in equipment_dict.get("armor", [])]
        accessories_names: List[str] = [acc.get("name", "unknown") for acc in equipment_dict.get("accessories", [])]
        consumables_names: List[str] = [c.get("name", "unknown") for c in equipment_dict.get("consumables", [])]
        weapons_str: str = ", ".join(weapons_names) if weapons_names else "None"
        armor_str: str = ", ".join(armor_names) if armor_names else "None"
        accessories_str: str = ", ".join(accessories_names) if accessories_names else "None"
        consumables_str: str = ", ".join(consumables_names) if consumables_names else "None"

        # Combat stats formatting
        combat_dict: Dict[str, int] = self.combat_stats.model_dump()
        hp_line: str = f"  - HP: {combat_dict.get('current_hit_points')}/{combat_dict.get('max_hit_points')}"
        mp_line: str = f"  - MP: {combat_dict.get('current_mana_points')}/{combat_dict.get('max_mana_points')}"
        ac_line: str = f"  - Armor Class: {combat_dict.get('armor_class')}"
        atk_line: str = f"  - Attack Bonus: {combat_dict.get('attack_bonus')}"
        combat_block: str = "\n".join([hp_line, mp_line, ac_line, atk_line])

        physical_str: str = self.physical_description if self.physical_description else 'Not defined'
        background_str: str = self.description if self.description else 'Not defined'

        narrative_block: str = (
            f"Name: {self.name}\n"
            f"Sex: {self.sex.value}\n"
            f"Race: {self.race}\n"
            f"Culture: {self.culture}\n"
            f"Level: {self.level}\n\n"
            f"Stats:\n{stats_block}\n\n"
            f"Skills:{skills_block}\n\n"
            f"Combat Stats:\n{combat_block}\n\n"
            f"Experience: {self.experience_points} XP\n"
            f"Currency: {equipment_dict.get('gold', 0)}G {equipment_dict.get('silver', 0)}S {equipment_dict.get('copper', 0)}C\n\n"
            f"Equipment:\n  - Weapons: {weapons_str}\n  - Armor: {armor_str}\n  - Accessories: {accessories_str}\n  - Consumables: {consumables_str}\n\n"
            f"Physical Description: {physical_str}\n"
            f"Background: {background_str}\n"
        )
        return narrative_block

    def build_combat_prompt_block(self) -> str:
        """
        ### build_combat_prompt_block
        **Description:** Produce a focused combat-oriented representation of the character for combat prompts.
        **Parameters:**
        - (none)
        **Returns:** A formatted string emphasizing combat stats, combat skills and equipped items.
        """
        from typing import Any, Dict, List

        # Core stat modifiers for quick reference
        stats_dict: Dict[str, int] = self.stats.model_dump()
        stat_lines: List[str] = [
            f"  - {stat.upper()}: {value} (modifier: {self.stats.get_modifier(stat)})" for stat, value in stats_dict.items()
        ]
        stats_block: str = "\n".join(stat_lines)

        # Combat skills only
        skills_dict: Dict[str, Dict[str, int]] = self.skills.model_dump()
        combat_skills_dict: Dict[str, int] = skills_dict.get('combat', {})
        combat_skill_lines: List[str] = [
            f"    - {skill}: {rank}" for skill, rank in combat_skills_dict.items()
        ] if combat_skills_dict else ["    - None"]
        combat_skills_block: str = "\n".join(combat_skill_lines)

        # Equipment (weapons + armor)
        equipment_dict: Dict[str, Any] = self.equipment.model_dump()
        weapons_list: List[Dict[str, Any]] = equipment_dict.get("weapons", [])
        armor_list: List[Dict[str, Any]] = equipment_dict.get("armor", [])
        weapons_lines: List[str] = [
            f"    - {w.get('name', 'unknown')}: {w.get('damage', 'N/A')} damage" for w in weapons_list
        ] if weapons_list else ["    - None"]
        armor_lines: List[str] = [
            f"    - {a.get('name', 'unknown')}: {a.get('defense', 'N/A')} defense" for a in armor_list
        ] if armor_list else ["    - None"]
        weapons_block: str = "\n".join(weapons_lines)
        armor_block: str = "\n".join(armor_lines)

        # Combat stats
        combat_dict: Dict[str, int] = self.combat_stats.model_dump()
        hp_line: str = f"  - HP: {combat_dict.get('current_hit_points')}/{combat_dict.get('max_hit_points')}"
        mp_line: str = f"  - MP: {combat_dict.get('current_mana_points')}/{combat_dict.get('max_mana_points')}"
        ac_line: str = f"  - Armor Class: {combat_dict.get('armor_class')}"
        atk_line: str = f"  - Attack Bonus: {combat_dict.get('attack_bonus')}"
        init_line: str = f"  - Initiative Bonus: {self.calculate_initiative()}"
        combat_core_block: str = "\n".join([hp_line, mp_line, ac_line, atk_line, init_line])

        combat_prompt_block: str = (
            f"Name: {self.name}\n"
            f"Race: {self.race} | Culture: {self.culture} | Level: {self.level}\n\n"
            f"Combat Stats:\n{stats_block}\n\n"
            f"Combat Skills:\n{combat_skills_block}\n\n"
            f"Health & Defense:\n{combat_core_block}\n\n"
            f"Equipped Weapons:\n{weapons_block}\n\n"
            f"Equipped Armor:\n{armor_block}\n"
        )
        return combat_prompt_block

    def build_narrative_prompt_json(self) -> dict:
        """
        ### build_narrative_prompt_json
        **Description:** Provide a structured JSON-friendly representation of the character for narrative contexts.
        **Returns:** Dict with identity, stats, skills, combat, equipment and descriptions.
        """
        from typing import Any, Dict
        stats_dict: Dict[str, int] = self.stats.model_dump()
        skills_dict: Dict[str, Dict[str, int]] = self.skills.model_dump()
        equipment_dict: Dict[str, Any] = self.equipment.model_dump()
        combat_dict: Dict[str, int] = self.combat_stats.model_dump()
        return {
            "id": str(self.id),
            "name": self.name,
            "race": self.race,
            "culture": self.culture,
            "level": self.level,
            "stats": stats_dict,
            "skills": skills_dict,
            "combat": {
                "hp": combat_dict.get("current_hit_points"),
                "max_hp": combat_dict.get("max_hit_points"),
                "mp": combat_dict.get("current_mana_points"),
                "max_mp": combat_dict.get("max_mana_points"),
                "armor_class": combat_dict.get("armor_class"),
                "attack_bonus": combat_dict.get("attack_bonus"),
                "initiative_bonus": self.calculate_initiative()
            },
            "experience_points": self.experience_points,
            "gold": equipment_dict.get("gold", 0),
            "silver": equipment_dict.get("silver", 0),
            "copper": equipment_dict.get("copper", 0),
            "equipment": equipment_dict,
            "background": self.description,
            "background_localized": self.description_localized,
            "physical_description": self.physical_description,
            "physical_description_localized": self.physical_description_localized,
            "status": self.status.value
        }

    def build_combat_prompt_json(self) -> dict:
        """
        ### build_combat_prompt_json
        **Description:** Provide a compact structured JSON representation for combat resolution.
        **Returns:** Dict focused on combat relevant data (stats, combat stats, combat skills, equipped weapons/armor).
        """
        from typing import Any, Dict, List
        stats_dict: Dict[str, int] = self.stats.model_dump()
        skills_dict: Dict[str, Dict[str, int]] = self.skills.model_dump()
        combat_skills: Dict[str, int] = skills_dict.get("combat", {})
        equipment_dict: Dict[str, Any] = self.equipment.model_dump()
        weapons: List[Dict[str, Any]] = equipment_dict.get("weapons", [])
        armor: List[Dict[str, Any]] = equipment_dict.get("armor", [])
        combat_dict: Dict[str, int] = self.combat_stats.model_dump()
        return {
            "id": str(self.id),
            "name": self.name,
            "sex": self.sex.value,
            "race": self.race,

            "culture": self.culture,
            "level": self.level,
            "stats": stats_dict,
            "combat_stats": {
                "hp": combat_dict.get("current_hit_points"),
                "max_hp": combat_dict.get("max_hit_points"),
                "mp": combat_dict.get("current_mana_points"),
                "max_mp": combat_dict.get("max_mana_points"),
                "armor_class": combat_dict.get("armor_class"),
                "attack_bonus": combat_dict.get("attack_bonus"),
                "initiative_bonus": self.calculate_initiative()
            },
            "combat_skills": combat_skills,
            "equipped": {
                "weapons": weapons,
                "armor": armor
            }
        }
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Aragorn",
                "sex": "male",
                "race": "Human",
                "culture": "Dúnedain",
                "level": 5,
                "stats": {
                    "strength": 16,
                    "constitution": 14,
                    "agility": 15,
                    "intelligence": 12,
                    "wisdom": 14,
                    "charisma": 16
                },
                "skills": {
                    "combat": {"sword_combat": 7, "archery": 5},
                    "general": {"athletics": 6, "perception": 5, "survival": 8},
                    "stealth": {"stealth": 4},
                    "social": {"persuasion": 5, "leadership": 6},
                    "magic": {},
                    "crafting": {"herbalism": 3}
                },
                "combat_stats": {
                    "max_hit_points": 60,
                    "current_hit_points": 60,
                    "max_mana_points": 15,
                    "current_mana_points": 15,
                    "armor_class": 17,
                    "attack_bonus": 5
                },
                "status": "active",
                "experience_points": 4500,
                "description": "A ranger of the North, heir to Isildur.",
                "physical_description": "Tall, weathered, dark-haired, with keen grey eyes."
            }
        }
    )


# Export main classes
__all__ = [
    'Character',
    'CharacterStatus',
    'Stats',
    'Skills',
    'Equipment',
    'CombatStats',
    'Spells'
]
Character.model_rebuild()