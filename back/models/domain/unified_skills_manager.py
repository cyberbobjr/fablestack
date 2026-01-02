"""
Unified Skills Manager for loading and managing all skill-related data.

This manager loads the unified skills.yaml file containing:
- Skill groups and their skills with descriptions and IDs
- Racial affinities with base points
- Stat-based skill bonuses
"""

import os
from typing import Any, Dict, List, Optional

import yaml

from ...config import get_data_dir


class UnifiedSkillsManager:
    """
    Manager for unified skills data from skills.yaml.

    Purpose:
        Provides centralized access to skill groups, racial affinities, and stat-based bonuses.
        This manager loads the unified skills configuration and exposes methods for querying
        skill information, calculating bonuses, and retrieving racial skill affinities. It
        enables the character creation and skill allocation systems to work with consistent
        skill data while supporting flexible skill group organization and stat-skill relationships.

    Attributes:
        _data (Dict): Complete skills data loaded from YAML including skill groups and racial affinities.
    """

    def __init__(self):
        self._data: Dict = {}
        self._load_skills_data()

    def _load_skills_data(self):
        """Load skills data from the unified YAML file"""
        data_path = os.path.join(get_data_dir(), "skills.yaml")
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                self._data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Skills data file not found: {data_path}. "
                "Please ensure that file exists and contains valid YAML data."
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in skills file {data_path}: {str(e)}. "
                "Please check the file format and syntax."
            )

    @property
    def skill_groups(self) -> Dict[str, Dict]:
        """Get all skill groups with their skills."""
        return self._data.get("skill_groups", {})

    @property
    def racial_affinities(self) -> Dict[str, List[Dict[str, int]]]:
        """Get racial affinities mapping."""
        return self._data.get("racial_affinities", {})

    def get_skill_group(self, group_name: str) -> Optional[Dict]:
        """
        Get a specific skill group by name.

        Args:
            group_name: Name of the skill group

        Returns:
            Skill group data or None if not found
        """
        return self.skill_groups.get(group_name)

    def get_skill_info(self, group_name: str, skill_id: str) -> Optional[Dict]:
        """
        Get information about a specific skill.

        Args:
            group_name: Name of the skill group
            skill_id: ID of the skill

        Returns:
            Skill information or None if not found
        """
        group = self.get_skill_group(group_name)
        if group and "skills" in group:
            return group["skills"].get(skill_id)
        return None

    def get_race_affinities(self, race_name: str) -> List[Dict[str, int]]:
        """
        Get skill affinities for a specific race.

        Args:
            race_name: Name of the race

        Returns:
            List of skill affinities with base points
        """
        return self.racial_affinities.get(race_name, [])

    def get_stat_bonuses_for_skill(self, group_name: str, skill_id: str) -> List[Dict]:
        """
        Get stat bonuses for a specific skill.

        Args:
            group_name: Name of the skill group
            skill_id: ID of the skill

        Returns:
            List of stat bonuses for the skill
        """
        skill_info = self.get_skill_info(group_name, skill_id)
        if skill_info and "stat_bonuses" in skill_info:
            return [skill_info["stat_bonuses"]]
        return []

    def get_all_skills(self) -> Dict[str, Dict[str, Dict]]:
        """
        Get all skills organized by group.

        Returns:
            Dictionary with group names as keys and skill dictionaries as values
        """
        all_skills = {}
        for group_name, group_data in self.skill_groups.items():
            if "skills" in group_data:
                all_skills[group_name] = group_data["skills"]
        return all_skills

    def get_all_skill_ids(self) -> List[str]:
        """
        Get a list of all unique skill IDs across all groups.

        Returns:
            List of skill IDs sorted alphabetically
        """
        skill_ids = set()
        for group_data in self.skill_groups.values():
            if "skills" in group_data:
                skill_ids.update(group_data["skills"].keys())
        return sorted(list(skill_ids))

    def get_skills_by_group(self, group_name: str) -> Dict[str, Dict]:
        """
        Get all skills for a specific group.

        Args:
            group_name: Name of the skill group

        Returns:
            Dictionary of skills in the group
        """
        group = self.get_skill_group(group_name)
        return group.get("skills", {}) if group else {}

    def get_skill_by_name(self, skill_name: str) -> Optional[Dict]:
        """
        Find a skill by its display name across all groups.

        Args:
            skill_name: Display name of the skill

        Returns:
            Skill information with group context or None if not found
        """
        for group_name, group_data in self.skill_groups.items():
            if "skills" in group_data:
                for skill_id, skill_info in group_data["skills"].items():
                    if skill_info.get("name") == skill_name:
                        return {
                            "group": group_name,
                            "id": skill_id,
                            **skill_info
                        }
        return None

    def get_all_races(self) -> List[str]:
        """
        Get list of all races that have skill affinities.

        Returns:
            List of race names
        """
        return list(self.racial_affinities.keys())

    def get_stat_based_skill_bonuses(self, stat_name: str, stat_value: int) -> List[Dict]:
        """
        Get all skills that receive bonuses from a specific stat at a given value.

        Args:
            stat_name: Name of the stat (e.g., 'charisma', 'strength')
            stat_value: Value of the stat

        Returns:
            List of skill bonuses that apply
        """
        bonuses = []
        for group_name, group_data in self.skill_groups.items():
            if "skills" in group_data:
                for skill_id, skill_info in group_data["skills"].items():
                    if "stat_bonuses" in skill_info:
                        stat_bonus = skill_info["stat_bonuses"]
                        if (stat_bonus.get("stat_name") == stat_name and
                            stat_value >= stat_bonus.get("min_value", 0)):
                            bonuses.append({
                                "group": group_name,
                                "skill": skill_id,
                                "bonus_points": stat_bonus.get("bonus_points", 0)
                            })
        return bonuses

    def get_skill_data(self, skill_id: str) -> Optional[Dict]:
        """
        Get skill data by ID, including its category (group).

        Args:
            skill_id: The ID of the skill to find.

        Returns:
            Dict containing skill data and 'category' (group key), or None if not found.
        """
        for group_name, group_data in self.skill_groups.items():
            if "skills" in group_data and skill_id in group_data["skills"]:
                skill_info = group_data["skills"][skill_id]
                # Return a copy to avoid mutating original, adding category
                result = skill_info.copy()
                result['category'] = group_name
                return result
        return None

    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all skills data including skill groups and racial affinities.

        Returns:
            Complete skills data dictionary
        """
        return self._data