import os
from typing import Any, Dict, List, Optional

import yaml

from back.models.api.game import CultureData, RaceData

from ...config import get_data_dir


class RacesManager:
    """
    Manages races and cultures using the new simplified YAML system.

    Purpose:
        Provides centralized access to race and culture data for character creation.
        This manager loads and exposes racial characteristics, cultural bonuses, languages,
        and special traits from YAML configuration. It enables the character creation
        process to apply appropriate racial and cultural modifiers while maintaining
        data consistency and supporting easy updates to game content.

    Attributes:
        races_data (List[RaceData]): List of all available races with their cultures.
    """

    def __init__(self):
        self.races_data: Optional[List[RaceData]] = None

    def _ensure_loaded(self):
        """Ensures data is loaded"""
        if self.races_data is None:
            self._load_races_data()

    def _load_races_data(self):
        """Loads data from the YAML file"""
        data_path = os.path.join(get_data_dir(), "races_and_cultures.yaml")
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                self.races_data = [RaceData(**race) for race in yaml.safe_load(f)]
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Races data file not found: {data_path}. "
                f"Please ensure that file exists and contains valid YAML data with race definitions."
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in races file {data_path}: {str(e)}. "
                f"Please check the file format and syntax."
            )

    def get_all_races(self) -> List[RaceData]:
        """Returns the complete list of races"""
        self._ensure_loaded()
        return self.races_data

    def get_race_by_id(self, race_id: str) -> Optional[RaceData]:
        """Returns data for a race by its id"""
        self._ensure_loaded()
        for race in self.races_data:
            if race.id == race_id:
                return race
        return None

    def get_race_by_name(self, race_name: str) -> Optional[RaceData]:
        """Returns data for a race by its name"""
        self._ensure_loaded()
        for race in self.races_data:
            if race.name == race_name:
                return race
        return None

    def get_cultures_for_race(self, race_id: str) -> List[CultureData]:
        """Returns the available cultures for a race"""
        race = self.get_race_by_id(race_id)
        if race:
            return race.cultures or []
        return []

    def get_culture_by_id(self, race_id: str, culture_id: str) -> Optional[CultureData]:
        """Returns data for a specific culture"""
        cultures = self.get_cultures_for_race(race_id)
        for culture in cultures:
            if culture.id == culture_id:
                return culture
        return None

    def get_characteristic_bonuses(self, race_id: str, culture_id: Optional[str] = None) -> Dict[str, int]:
        """Returns all characteristic bonuses (race + culture)"""
        bonuses = {}

        # Racial bonuses
        race = self.get_race_by_id(race_id)
        if race:
            bonuses.update(race.characteristic_bonuses or {})

        # Cultural bonuses (if specified)
        if culture_id:
            culture = self.get_culture_by_id(race_id, culture_id)
            if culture:
                bonuses.update(culture.characteristic_bonuses or {})

        return bonuses

    def get_skill_bonuses(self, race_id: str, culture_id: str) -> Dict[str, int]:
        """Returns the skill bonuses of a culture"""
        culture = self.get_culture_by_id(race_id, culture_id)
        if culture:
            return culture.skill_bonuses or {}
        return {}

    def get_languages(self, race_id: str) -> Dict[str, List[str]]:
        """Returns the base and optional languages of a race"""
        race = self.get_race_by_id(race_id)
        if race:
            return {
                "base": race.base_languages or [],
                "optional": race.optional_languages or []
            }
        return {"base": [], "optional": []}

    def get_free_skill_points(self, race_id: str, culture_id: str) -> int:
        """Returns the number of free skill points"""
        culture = self.get_culture_by_id(race_id, culture_id)
        if culture:
            return culture.free_skill_points or 0
        return 0

    def get_special_traits(self, race_id: str, culture_id: str) -> Dict[str, Any]:
        """Returns the special traits of a culture"""
        culture = self.get_culture_by_id(race_id, culture_id)
        if culture:
            return culture.special_traits or {}
        return {}

    def get_culture_description(self, race_id: str, culture_id: str) -> str:
        """Returns the description/traits of a culture"""
        culture = self.get_culture_by_id(race_id, culture_id)
        if culture:
            return culture.traits or ""
        return ""

    def get_complete_character_bonuses(self, race_id: str, culture_id: str) -> Dict[str, Any]:
        """Returns all bonuses and traits for a character (race + culture)"""
        return {
            "characteristic_bonuses": self.get_characteristic_bonuses(race_id, culture_id),
            "skill_bonuses": self.get_skill_bonuses(race_id, culture_id),
            "languages": self.get_languages(race_id),
            "free_skill_points": self.get_free_skill_points(race_id, culture_id),
            "special_traits": self.get_special_traits(race_id, culture_id),
            "culture_description": self.get_culture_description(race_id, culture_id)
        }

    def get_all_races_data(self) -> List[RaceData]:
        """Returns the complete list of race data (not just names)"""
        self._ensure_loaded()
        return self.races_data

    def get_playable_races(self) -> List[RaceData]:
        """Returns only playable races"""
        self._ensure_loaded()
        return [race for race in self.races_data if race.is_playable]

    def get_combatant_races(self) -> List[RaceData]:
        """Returns only combatant races"""
        self._ensure_loaded()
        return [race for race in self.races_data if race.is_combatant]

    def get_playable_race_ids(self) -> List[str]:
        """Returns a list of IDs for playable races"""
        return [race.id for race in self.get_playable_races()]

    def get_combatant_race_ids(self) -> List[str]:
        """Returns a list of IDs for combatant races"""
        return [race.id for race in self.get_combatant_races()]

    def get_race_names(self) -> List[str]:
        """Returns only the names of the races"""
        self._ensure_loaded()
        return [race.name for race in self.races_data]

    def search_archetypes(self, query: str) -> List[Dict[str, str]]:
        """
        Searches for races/archetypes matching the query.
        
        Args:
            query (str): The search string (case-insensitive).
            
        Returns:
            List[Dict[str, str]]: List of matching archetypes with id, name, and description.
        """
        query = query.lower()
        results = []
        self._ensure_loaded()
        
        for race in self.races_data:
            if query in race.id.lower() or query in race.name.lower():
                results.append({
                    "id": race.id,
                    "name": race.name,
                    "description": race.description or ""
                })
                
        return results
