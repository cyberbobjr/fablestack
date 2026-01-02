# Unitary Business Logic (SRP)

import random
from typing import Dict, Optional

from injector import inject

from back.models.api.skills import SkillCheckResult
from back.models.domain.character import Character
from back.models.domain.stats_manager import StatsManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager
from back.models.enums import CharacterStatus
from back.services.character_data_service import CharacterDataService
from back.utils.logger import get_logger, log_debug, log_info, log_warning
from back.utils.model_converter import ModelConverter

logger = get_logger(__name__)

class CharacterService:
    """
    ### CharacterService
    **Description:** Service responsible for character-related business logic.
    It acts as an abstraction layer above `CharacterDataService` for operations
    that modify the character's state (XP, Gold, HP, Rest).
    
    **Usage:**
    This service is used by `GameSessionService` to expose business methods to Tools
    and agents. It is not meant to be instantiated directly by controllers, but rather
    via `GameSessionService` which manages the session context.
    """

    @inject
    def __init__(self, character_id: str, data_service: CharacterDataService):
        """
        ### __init__
        **Description:** Initializes the character service.
        **Note:** Does NOT load data automatically. You must call `load()` before using other methods.
        
        **Parameters:**
        - `character_id` (str): ID of the character to manage.
        - `data_service` (CharacterDataService): Injected persistence service.
        """
        self.character_id = character_id
        # We rely on the injector to provide the singleton data service
        self.data_service = data_service
        self.character_data: Optional[Character] = None

    async def load(self) -> Character:
        """
        ### load
        **Description:** Asynchronously loads the character data from persistence.
        **Returns:** The loaded Character object.
        """
        self.character_data = await self.data_service.load_character(self.character_id)
        return self.character_data

    async def save(self) -> None:
        """
        ### save
        **Description:** Persists the current character state.
        
        **Returns:** None.
        """
        if self.character_data:
            await self.data_service.save_character(self.character_data, self.character_id)

    async def save_character(self) -> None:
        """Alias for save() to maintain backward compatibility with tests."""
        await self.save()

    async def save_character_data(self) -> None:
        """Alias for save() to maintain backward compatibility with tests."""
        await self.save()

    def _ensure_loaded(self) -> Character:
        """
        ### _ensure_loaded
        **Description:** Helper to ensure character data is loaded.
        **Returns:** Character object.
        **Raises:** RuntimeError if data is not loaded.
        """
        if not self.character_data:
            raise RuntimeError(f"Character data for {self.character_id} not loaded. Call load() first.")
        return self.character_data

    def get_character(self) -> Character:
        """
        ### get_character
        **Description:** Returns the character data object.
        
        **Returns:** 
        - `Character`: The character object.
        """
        return self._ensure_loaded()

    def get_character_json(self) -> str:
        """
        ### get_character_json
        **Description:** Returns character data as a JSON string.
        Useful for display or debugging.
        
        **Returns:** 
        - `str`: JSON representation of the character.
        """
        return ModelConverter.to_json(self.character_data)
    
    # --- Business Logic Methods ---

    async def apply_xp(self, xp: int) -> Character:
        """
        ### apply_xp
        **Description:** Adds experience points (XP) to the character and checks if they should level up.
        
        **Parameters:**
        - `xp` (int): The amount of XP to add. Must be positive.
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        if xp < 0:
            log_warning("Attempt to add negative XP", action="apply_xp", character_id=self.character_id, xp=xp)
            return self.character_data

        self.character_data.xp += xp
        
        # Check for level up (simplified logic: 1000 XP per level for example)
        # TODO: Implement a real XP table if necessary
        xp_threshold = self.character_data.level * 1000
        if self.character_data.xp >= xp_threshold:
            self.level_up()

        await self.data_service.save_character(self.character_data, self.character_id)
        
        log_info("XP added to character",
                   extra={"action": "apply_xp",
                          "character_id": str(self.character_data.id),
                          "xp_added": xp,
                          "xp_total": self.character_data.xp,
                          "level": self.character_data.level})
        
        return self.character_data
    
    def level_up(self) -> None:
        """
        ### level_up
        **Description:** Handles the character's level up.
        Increases level, recalculates max HP, and heals the character.
        
        **Returns:** None.
        """
        self.character_data.level += 1
        
        # Recalculate max HP (Constitution * 10 + Level * 5)
        new_max_hp = self.calculate_max_hp()
        self.character_data.combat_stats.max_hit_points = new_max_hp
        
        # Fully heal upon leveling up
        self.character_data.combat_stats.current_hit_points = new_max_hp
        
        log_info("Level up!", 
                 extra={"action": "level_up", 
                        "character_id": str(self.character_data.id), 
                        "new_level": self.character_data.level,
                        "new_max_hp": new_max_hp})

    async def add_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> Character:
        """
        ### add_currency
        **Description:** Adds currency (gold, silver, copper) to the character's inventory.
        Delegates to `equipment.add_currency`.
        
        **Parameters:**
        - `gold` (int): Amount of gold to add.
        - `silver` (int): Amount of silver to add.
        - `copper` (int): Amount of copper to add.
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        self.character_data.equipment.add_currency(gold, silver, copper)
        await self.data_service.save_character(self.character_data, self.character_id)
        
        log_info("Currency added to character",
                   extra={"action": "add_currency",
                          "character_id": str(self.character_data.id),
                          "gold_added": gold,
                          "silver_added": silver,
                          "copper_added": copper,
                          "total_gold": self.character_data.equipment.gold,
                          "total_silver": self.character_data.equipment.silver,
                          "total_copper": self.character_data.equipment.copper})
        
        return self.character_data
    
    async def remove_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> Character:
        """
        ### remove_currency
        **Description:** Removes currency from the character with automatic conversion.
        If the character doesn't have enough of a specific denomination, it will automatically
        convert from higher denominations (1 gold = 10 silver = 100 copper).
        
        **Parameters:**
        - `gold` (int): Amount of gold to remove. Must be non-negative.
        - `silver` (int): Amount of silver to remove. Must be non-negative.
        - `copper` (int): Amount of copper to remove. Must be non-negative.
        
        **Returns:** 
        - `Character`: The updated character object.
        
        **Raises:**
        - `ValueError`: If the character doesn't have enough total currency.
        """
        if gold < 0 or silver < 0 or copper < 0:
            raise ValueError("Currency amounts must be non-negative")
        
        # Convert everything to copper for calculation
        total_to_remove_copper = (gold * 100) + (silver * 10) + copper
        current_total_copper = (self.character_data.equipment.gold * 100) + \
                               (self.character_data.equipment.silver * 10) + \
                               self.character_data.equipment.copper
        
        if current_total_copper < total_to_remove_copper:
            raise ValueError(
                f"Insufficient funds. Need {total_to_remove_copper}C total, "
                f"but only have {current_total_copper}C"
            )
        
        # Calculate new total
        remaining_copper = current_total_copper - total_to_remove_copper
        
        # Convert back to gold/silver/copper
        new_gold = remaining_copper // 100
        remaining_copper %= 100
        new_silver = remaining_copper // 10
        new_copper = remaining_copper % 10
        
        # Update character
        self.character_data.equipment.gold = new_gold
        self.character_data.equipment.silver = new_silver
        self.character_data.equipment.copper = new_copper
        
        await self.data_service.save_character(self.character_data, self.character_id)
        
        log_info("Currency removed from character",
                   extra={"action": "remove_currency",
                          "character_id": str(self.character_data.id),
                          "gold_removed": gold,
                          "silver_removed": silver,
                          "copper_removed": copper,
                          "total_gold": self.character_data.equipment.gold,
                          "total_silver": self.character_data.equipment.silver,
                          "total_copper": self.character_data.equipment.copper})
        
        return self.character_data
    
    async def take_damage(self, amount: int, source: str = "combat") -> Character:
        """
        ### take_damage
        **Description:** Applies damage to the character by reducing their current hit points.
        Delegates logic to `combat_stats.take_damage`.
        
        **Parameters:**
        - `amount` (int): Damage points to apply.
        - `source` (str): The source of damage (e.g., "combat", "trap", "fall").
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        # Delegate to combat stats to ensure consistency
        self.character_data.combat_stats.take_damage(int(amount))
        await self.data_service.save_character(self.character_data, self.character_id)
        
        log_warning("Damage applied to character",
                       extra={"action": "take_damage",
                              "character_id": str(self.character_data.id),
                              "amount": amount,
                              "hp_remaining": self.character_data.hp,
                              "source": source})
        
        return self.character_data
    
    async def heal(self, amount: int, source: str = "heal") -> Character:
        """
        ### heal
        **Description:** Restores hit points to the character.
        Cannot exceed maximum HP.
        
        **Parameters:**
        - `amount` (int): Hit points to restore.
        - `source` (str): The source of healing (e.g., "potion", "spell", "rest").
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        max_hp = self.character_data.combat_stats.max_hit_points
        current_hp = self.character_data.hp
        
        new_hp = min(max_hp, current_hp + int(amount))
        self.character_data.hp = new_hp
        
        await self.data_service.save_character(self.character_data, self.character_id)
        
        log_info("Healing applied to character",
                   extra={"action": "heal",
                          "character_id": str(self.character_data.id),
                          "amount": amount,
                          "hp_remaining": self.character_data.hp,
                          "source": source})
        
        return self.character_data

    def calculate_max_hp(self) -> int:
        """
        ### calculate_max_hp
        **Description:** Calculates the character's theoretical max HP based on their stats.
        Formula: Constitution * 10 + Level * 5.
        
        **Returns:** 
        - `int`: Calculated max HP.
        """
        constitution = self.character_data.stats.constitution
        level = self.character_data.level
        return constitution * 10 + level * 5
    
    def is_alive(self) -> bool:
        """
        ### is_alive
        **Description:** Checks if the character is still alive (HP > 0).
        
        **Returns:** 
        - `bool`: True if alive, False if dead.
        """
        return self.character_data.combat_stats.is_alive()
    
    async def short_rest(self) -> Character:
        """
        ### short_rest
        **Description:** Performs a short rest.
        House rule: Restores 25% of maximum HP.
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        max_hp = self.character_data.combat_stats.max_hit_points
        heal_amount = int(max_hp * 0.25)
        
        log_info("Short rest performed", action="short_rest", character_id=self.character_id, heal_amount=heal_amount)
        return await self.heal(heal_amount, source="short_rest")

    async def long_rest(self) -> Character:
        """
        ### long_rest
        **Description:** Performs a long rest.
        Restores all HP and (potentially) other resources (Mana, etc.).
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        max_hp = self.character_data.combat_stats.max_hit_points
        missing_hp = max_hp - self.character_data.hp
        
        # Restore Mana if applicable (logic to be extended as needed)
        if hasattr(self.character_data.combat_stats, 'max_mana_points'):
             self.character_data.combat_stats.current_mana_points = self.character_data.combat_stats.max_mana_points

        log_info("Long rest performed", action="long_rest", character_id=self.character_id, heal_amount=missing_hp)
        return await self.heal(missing_hp, source="long_rest")

    def perform_skill_check(
        self,
        skill_name: str,
        difficulty_name: str = "normal",
        difficulty_modifier: int = 0,
        fallback_stat_name: Optional[str] = None
    ) -> SkillCheckResult:
        """
        ### perform_skill_check
        **Description:** Performs a skill check for the character using the unified skill system.
        
        **Parameters:**
        - `skill_name` (str): Name of the skill or stat to test.
        - `difficulty_name` (str): Difficulty ("favorable", "normal", "unfavorable").
        - `difficulty_modifier` (int): Additional modifier.
        - `fallback_stat_name` (Optional[str]): Stat to use if skill not found.
        
        **Returns:**
        - `SkillCheckResult`: Detailed result of the check.
        """
        skills_manager = UnifiedSkillsManager()
        stats_manager = StatsManager()
        
        # Determine the skill value (logic moved from tool)
        skill_value: int = 0
        source_used: str = ""
        skill_name_lower: str = skill_name.lower().replace(" ", "_")
        
        stat_mapping: Dict[str, str] = {name.lower(): name.lower() for name in stats_manager.get_all_stats_names()}
        
        # 1. Direct Stat Check
        if skill_name_lower in stat_mapping:
            stat_key = stat_mapping[skill_name_lower]
            stat_value = getattr(self.character_data.stats, stat_key)
            skill_value = stat_value * 3
            source_used = f"Base stat {stat_key.title()}"
        else:
            # 2. Skill Check (Trained or Untrained)
            skill_found = False
            skill_groups = self.character_data.skills.model_dump()
            
            # Check known skills
            for group_name, group_skills in skill_groups.items():
                if skill_name_lower in group_skills:
                    skill_rank = group_skills[skill_name_lower]
                    
                    skill_info = skills_manager.get_skill_by_name(skill_name)
                    
                    base_stat_name = "wisdom"
                    if skill_info and "base_stat" in skill_info:
                        base_stat_name = skill_info["base_stat"]
                    
                    base_stat_value = getattr(self.character_data.stats, base_stat_name, 10)
                    skill_value = (base_stat_value * 3) + (skill_rank * 10)
                    source_used = f"Skill {skill_name} (rank {skill_rank}) based on {base_stat_name.title()}"
                    skill_found = True
                    break
            
            # Untrained / Fallback
            if not skill_found:
                skill_info = skills_manager.get_skill_by_name(skill_name)
                
                if skill_info and "base_stat" in skill_info:
                    base_stat_name = skill_info["base_stat"]
                    # Untrained penalty could be applied here if desired, currently raw stat
                    base_stat_value = getattr(self.character_data.stats, base_stat_name, 10)
                    skill_value = base_stat_value * 3
                    source_used = f"Untrained skill {skill_name} (using {base_stat_name.title()} base: {base_stat_value})"
                else:
                    target_stat = "wisdom"
                    if fallback_stat_name and fallback_stat_name.lower() in stat_mapping:
                        target_stat = fallback_stat_name.lower()
                    
                    default_stat_value = getattr(self.character_data.stats, target_stat, 10)
                    skill_value = default_stat_value * 3
                    source_used = f"Unknown skill '{skill_name}' (using fallback {target_stat.title()}: {default_stat_value})"

        # 3. Calculate Target
        difficulty_modifiers = {"favorable": -20, "normal": 0, "unfavorable": 20}
        base_difficulty = difficulty_modifiers.get(difficulty_name.lower(), 0)
        total_difficulty = base_difficulty + difficulty_modifier
        target = skill_value - total_difficulty
        
        # 4. Roll
        roll = random.randint(1, 100)
        success = roll <= target
        margin = abs(roll - target)
        
        degree = "Simple Success"
        if success:
            if margin >= 50: degree = "Critical Success"
            elif margin >= 30: degree = "Excellent Success"
            elif margin >= 10: degree = "Good Success"
        else:
            degree = "Simple Failure"
            if margin >= 50: degree = "Critical Failure"
            elif margin >= 30: degree = "Severe Failure"
            elif margin >= 10: degree = "Moderate Failure"
            
        result_message = (
            f"Skill check for {skill_name}: {source_used} = {skill_value}, "
            f"Roll 1d100 = {roll}, Target = {target} ({skill_value} - {total_difficulty}), "
            f"Result: **{degree}**"
        )
        
        log_info(
            "Skill check performed", 
            action="perform_skill_check", 
            character_id=self.character_id,
            skill=skill_name,
            roll=roll, 
            target=target, 
            success=success
        )
        
        return SkillCheckResult(
            message=result_message,
            skill_name=skill_name,
            roll=roll,
            target=target,
            success=success,
            degree=degree,
            source_used=source_used
        )


