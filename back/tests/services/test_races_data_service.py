from unittest.mock import MagicMock, patch

import pytest

from back.models.api.game import CultureData, RaceData
from back.services.races_data_service import RacesDataService


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    # Return mock objects instead of real Pydantic models
    race1 = MagicMock()
    race1.id = "human"
    race1.name = "Human"
    culture1 = MagicMock()
    culture1.id = "empire"
    culture1.name = "Empire"
    race1.cultures = [culture1]
    
    race2 = MagicMock()
    race2.id = "elf"
    race2.name = "Elf"
    culture2 = MagicMock()
    culture2.id = "forest"
    culture2.name = "Forest"
    race2.cultures = [culture2]
    
    manager.get_all_races.return_value = [race1, race2]
    manager.get_playable_races.return_value = [race1, race2]
    manager.get_combatant_races.return_value = [race1, race2]
    manager.get_playable_race_ids.return_value = ["human", "elf"]
    manager.get_combatant_race_ids.return_value = ["human", "elf"]
    
    manager.get_race_by_id.return_value = race1
    manager.get_cultures_for_race.return_value = [culture1]
    manager.get_complete_character_bonuses.return_value = {"strength": 2}
    return manager

@pytest.fixture
def service(mock_manager):
    return RacesDataService(manager=mock_manager)

class TestRacesDataService:

    def test_get_all_races(self, service, mock_manager):
        """Test retrieving all races."""
        races = service.get_all_races()
        
        assert len(races) == 2
        assert races[0].name == "Human"
        mock_manager.get_all_races.assert_called_once()

    def test_get_playable_races(self, service, mock_manager):
        """Test retrieving playable races."""
        races = service.get_playable_races()
        assert len(races) == 2
        mock_manager.get_playable_races.assert_called_once()

    def test_get_combatant_races(self, service, mock_manager):
        """Test retrieving combatant races."""
        races = service.get_combatant_races()
        assert len(races) == 2
        mock_manager.get_combatant_races.assert_called_once()

    def test_get_playable_race_ids(self, service, mock_manager):
        """Test retrieving playable race IDs."""
        ids = service.get_playable_race_ids()
        assert ids == ["human", "elf"]
        mock_manager.get_playable_race_ids.assert_called_once()

    def test_get_combatant_race_ids(self, service, mock_manager):
        """Test retrieving combatant race IDs."""
        ids = service.get_combatant_race_ids()
        assert ids == ["human", "elf"]
        mock_manager.get_combatant_race_ids.assert_called_once()

    def test_get_race_by_id(self, service, mock_manager):
        """Test retrieving a race by ID."""
        race = service.get_race_by_id("human")
        
        assert race is not None
        assert race.name == "Human"
        mock_manager.get_race_by_id.assert_called_once_with("human")

    def test_get_cultures_for_race(self, service, mock_manager):
        """Test retrieving cultures for a race."""
        cultures = service.get_cultures_for_race("human")
        
        assert len(cultures) == 1
        assert cultures[0].name == "Empire"
        mock_manager.get_cultures_for_race.assert_called_once_with("human")

    def test_get_complete_character_bonuses(self, service, mock_manager):
        """Test retrieving character bonuses."""
        bonuses = service.get_complete_character_bonuses("human", "empire")
        
        assert bonuses == {"strength": 2}
        mock_manager.get_complete_character_bonuses.assert_called_once_with("human", "empire")

    def test_get_random_race_and_culture(self, service, mock_manager):
        """Test random race and culture selection."""
        race, culture = service.get_random_race_and_culture()
        
        assert race is not None
        assert culture is not None
        assert culture in race.cultures
        mock_manager.get_playable_races.assert_called_once()

    def test_get_random_race_and_culture_all(self, service, mock_manager):
        """Test random race and culture selection from all races."""
        race, culture = service.get_random_race_and_culture(only_playable=False)
        
        assert race is not None
        assert culture is not None
        mock_manager.get_all_races.assert_called_once()

    def test_get_random_race_and_culture_no_races(self, mock_manager):
        """Test random selection with no races available."""
        mock_manager.get_playable_races.return_value = []
        service = RacesDataService(manager=mock_manager)
        
        with pytest.raises(ValueError, match="No races available"):
            service.get_random_race_and_culture()

    def test_get_random_race_and_culture_no_cultures(self, mock_manager):
        """Test random selection with race having no cultures."""
        race_no_culture = MagicMock()
        race_no_culture.name = "Orc"
        race_no_culture.cultures = []
        mock_manager.get_playable_races.return_value = [race_no_culture]
        service = RacesDataService(manager=mock_manager)
        
        with pytest.raises(ValueError, match="has no cultures"):
            service.get_random_race_and_culture()
