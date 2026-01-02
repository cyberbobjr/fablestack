"""
Skill Allocation Service for Character Creation V2.

This service handles the allocation of skills for random character generation,
taking into account race affinities and character stats.
"""

import random
from typing import Dict, List, Tuple

from back.models.domain.character import Stats
from back.models.domain.unified_skills_manager import UnifiedSkillsManager


class SkillAllocationService:
    """
    ### SkillAllocationService
    **Description:** Service for allocating skills based on race affinities and character stats.

    This service implements the logic for:
    - Race-based skill affinities (from skills.yaml)
    - Stat-based skill bonuses (from skills.yaml)
    - Random distribution of remaining skill points
    """

    def __init__(self):
        """
        ### __init__
        **Description:** Initializes the SkillAllocationService.
        """
        self.skills_manager = UnifiedSkillsManager()

    def allocate_random_skills_for_character(
        self,
        race_name: str,
        culture_name: str,
        stats: Stats,
        free_skill_points: int = 0
    ) -> Dict[str, Dict[str, int]]:
        """
        ### allocate_random_skills_for_character
        **Description:** Allocate skills randomly for a character based on race, culture, and stats.

        **Parameters:**
        - `race_name` (str): The character's race
        - `culture_name` (str): The character's culture
        - `stats` (Stats): The character's stats
        - `free_skill_points` (int): Additional skill points from culture

        **Returns:**
        - `Dict[str, Dict[str, int]]`: Dictionary of skill groups with allocated skills (all skills initialized to 0, then allocated)
        """
        # Initialize all skills from YAML data with 0 points
        allocated_skills: Dict[str, Dict[str, int]] = {}
        all_skills = self.skills_manager.get_all_skills()
        
        for group_name, skills_dict in all_skills.items():
            allocated_skills[group_name] = {}
            for skill_id in skills_dict.keys():
                allocated_skills[group_name][skill_id] = 0

        # Step 1: Allocate race-based affinities
        race_affinities: List[Dict[str, int]] = self.skills_manager.get_race_affinities(race_name)
        allocated_skills = self._allocate_race_affinities(allocated_skills, race_affinities)

        # Step 2: Allocate stat-based bonuses
        stat_bonuses: List[Tuple[str, str, int]] = self._get_stat_based_bonuses(stats)
        allocated_skills = self._allocate_stat_bonuses(allocated_skills, stat_bonuses)

        # Step 3: Distribute remaining points randomly
        # Base 40 + free points
        total_allowed_points = 40 + free_skill_points
        remaining_points = total_allowed_points - self._calculate_total_points(allocated_skills)
        if remaining_points > 0:
            allocated_skills = self._distribute_remaining_points(allocated_skills, remaining_points)

        return allocated_skills

    def _allocate_race_affinities(
        self,
        allocated_skills: Dict[str, Dict[str, int]],
        affinities: List[Dict[str, int]]
    ) -> Dict[str, Dict[str, int]]:
        """
        ### _allocate_race_affinities
        **Description:** Allocate base points for race affinities.
        
        **Parameters:**
        - `allocated_skills` (Dict[str, Dict[str, int]]): Current skills state
        - `affinities` (List[Dict[str, int]]): List of affinities to apply
        
        **Returns:**
        - `Dict[str, Dict[str, int]]`: Updated skills dictionary
        """
        for affinity in affinities:
            # Each affinity dict contains skill mappings with base points
            for skill_name, base_points in affinity.items():
                # Find which group this skill belongs to
                skill_info = self.skills_manager.get_skill_by_name(skill_name)
                if skill_info:
                    group_name = skill_info["group"]
                    skill_id = skill_info["id"]

                    if group_name in allocated_skills:
                        allocated_skills[group_name][skill_id] = (
                            allocated_skills[group_name].get(skill_id, 0) + base_points
                        )

        return allocated_skills

    def _get_stat_based_bonuses(self, stats: Stats) -> List[Tuple[str, str, int]]:
        """
        ### _get_stat_based_bonuses
        **Description:** Get skill bonuses based on character stats.
        
        **Parameters:**
        - `stats` (Stats): Character stats
        
        **Returns:**
        - `List[Tuple[str, str, int]]`: List of bonuses (group, skill, points)
        """
        bonuses: List[Tuple[str, str, int]] = []

        # Get all stat-based bonuses from the YAML data
        stat_based_bonuses = self.skills_manager.get_stat_based_skill_bonuses("charisma", stats.charisma)
        stat_based_bonuses.extend(self.skills_manager.get_stat_based_skill_bonuses("intelligence", stats.intelligence))
        stat_based_bonuses.extend(self.skills_manager.get_stat_based_skill_bonuses("wisdom", stats.wisdom))
        stat_based_bonuses.extend(self.skills_manager.get_stat_based_skill_bonuses("agility", stats.agility))
        stat_based_bonuses.extend(self.skills_manager.get_stat_based_skill_bonuses("strength", stats.strength))

        # Convert to the expected format
        for bonus in stat_based_bonuses:
            bonuses.append((bonus["group"], bonus["skill"], bonus["bonus_points"]))

        return bonuses

    def _allocate_stat_bonuses(
        self,
        allocated_skills: Dict[str, Dict[str, int]],
        bonuses: List[Tuple[str, str, int]]
    ) -> Dict[str, Dict[str, int]]:
        """
        ### _allocate_stat_bonuses
        **Description:** Apply stat-based bonuses to skills.
        
        **Parameters:**
        - `allocated_skills` (Dict[str, Dict[str, int]]): Current skills state
        - `bonuses` (List[Tuple[str, str, int]]): List of bonuses to apply
        
        **Returns:**
        - `Dict[str, Dict[str, int]]`: Updated skills dictionary
        """
        for group, skill, points in bonuses:
            if group in allocated_skills:
                allocated_skills[group][skill] = allocated_skills[group].get(skill, 0) + points

        return allocated_skills

    def _distribute_remaining_points(
        self,
        allocated_skills: Dict[str, Dict[str, int]],
        remaining_points: int
    ) -> Dict[str, Dict[str, int]]:
        """
        ### _distribute_remaining_points
        **Description:** Distribute remaining skill points randomly across all available skills.
        
        **Parameters:**
        - `allocated_skills` (Dict[str, Dict[str, int]]): Current skills state
        - `remaining_points` (int): Points left to distribute
        
        **Returns:**
        - `Dict[str, Dict[str, int]]`: Updated skills dictionary
        """
        # Get all available skills from the unified manager
        all_skills: List[Tuple[str, str]] = []
        all_skill_data = self.skills_manager.get_all_skills()

        for group_name, skills_dict in all_skill_data.items():
            for skill_id in skills_dict.keys():
                all_skills.append((group_name, skill_id))

        # Distribute points randomly
        for _ in range(remaining_points):
            if all_skills:
                group, skill = random.choice(all_skills)
                allocated_skills[group][skill] = allocated_skills[group].get(skill, 0) + 1

        return allocated_skills

    def _calculate_total_points(self, allocated_skills: Dict[str, Dict[str, int]]) -> int:
        """
        ### _calculate_total_points
        **Description:** Calculate total allocated skill points.
        
        **Parameters:**
        - `allocated_skills` (Dict[str, Dict[str, int]]): Skills dictionary
        
        **Returns:**
        - `int`: Total points allocated
        """
        total = 0
        for group_skills in allocated_skills.values():
            total += sum(group_skills.values())
        return total