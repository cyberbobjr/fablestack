"""Service wrapper for race and culture data lookups."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from back.models.api.game import CultureData, RaceData
from back.models.domain.races_manager import RacesManager


class RacesDataService:
    """Expose read-only helpers around `races_and_cultures.yaml`."""

    def __init__(self, manager: Optional[RacesManager] = None) -> None:
        self._manager = manager or RacesManager()

    def get_all_races(self) -> List[RaceData]:
        """Return every race definition."""
        return self._manager.get_all_races()

    def get_race_by_id(self, race_id: str) -> Optional[RaceData]:
        """Return a single race when it exists."""
        return self._manager.get_race_by_id(race_id)

    def get_cultures_for_race(self, race_id: str) -> List[CultureData]:
        """Return the cultures tied to a race."""
        return self._manager.get_cultures_for_race(race_id)

    def get_complete_character_bonuses(self, race_id: str, culture_id: str) -> Dict[str, Any]:
        """Return combined stat, skill, and language bonuses."""
        return self._manager.get_complete_character_bonuses(race_id, culture_id)

    def get_playable_races(self) -> List[RaceData]:
        """Returns only playable races"""
        return self._manager.get_playable_races()

    def get_combatant_races(self) -> List[RaceData]:
        """Returns only combatant races"""
        return self._manager.get_combatant_races()

    def get_playable_race_ids(self) -> List[str]:
        """Returns a list of IDs for playable races"""
        return self._manager.get_playable_race_ids()

    def get_combatant_race_ids(self) -> List[str]:
        """Returns a list of IDs for combatant races"""
        return self._manager.get_combatant_race_ids()

    def get_random_race_and_culture(self, only_playable: bool = True) -> Tuple[RaceData, CultureData]:
        """
        Pick a random race and one of its cultures.
        
        Args:
            only_playable: If True, only select from playable races.
        """
        if only_playable:
            races = self.get_playable_races()
        else:
            races = self.get_all_races()
            
        if not races:
            raise ValueError("No races available to choose from.")
        race = random.choice(races)
        cultures = race.cultures or []
        if not cultures:
            # If a race has no cultures (like Goblin might), we might need to handle it.
            # But for now, let's assume all races have at least one culture or this method isn't used for them.
            # Or we can return None for culture? The return type says Tuple[RaceData, CultureData].
            # Let's keep the exception but make the message clear.
            raise ValueError(f"Race '{race.name}' has no cultures defined.")
        return race, random.choice(cultures)

    def search_archetypes(self, query: str) -> List[Dict[str, str]]:
        """Search for races/archetypes matching the query."""
        return self._manager.search_archetypes(query)
