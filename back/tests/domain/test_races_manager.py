from unittest.mock import MagicMock, mock_open, patch

import pytest

from back.models.api.game import RaceData
from back.models.domain.races_manager import RacesManager


@pytest.fixture
def mock_yaml_data():
    return [
        {
            "id": "human",
            "name": "Human",
            "characteristic_bonuses": {"Willpower": 1},
            "base_languages": ["Westron"],
            "optional_languages": [],
            "is_playable": True,
            "is_combatant": True
        },
        {
            "id": "goblin",
            "name": "Goblin",
            "characteristic_bonuses": {"Agility": 1},
            "base_languages": ["Orkish"],
            "optional_languages": [],
            "is_playable": False,
            "is_combatant": True
        },
        {
            "id": "dummy",
            "name": "Dummy",
            "characteristic_bonuses": {},
            "base_languages": [],
            "optional_languages": [],
            "is_playable": True,
            "is_combatant": False
        }
    ]

@pytest.fixture
def manager(mock_yaml_data):
    with patch("builtins.open", mock_open(read_data="data")), \
         patch("yaml.safe_load", return_value=mock_yaml_data):
        manager = RacesManager()
        # Force load
        manager._load_races_data()
        return manager

class TestRacesManager:

    def test_get_all_races_data(self, manager):
        races = manager.get_all_races_data()
        assert len(races) == 3

    def test_get_playable_races(self, manager):
        races = manager.get_playable_races()
        assert len(races) == 2
        ids = [r.id for r in races]
        assert "human" in ids
        assert "dummy" in ids
        assert "goblin" not in ids

    def test_get_combatant_races(self, manager):
        races = manager.get_combatant_races()
        assert len(races) == 2
        ids = [r.id for r in races]
        assert "human" in ids
        assert "goblin" in ids
        assert "dummy" not in ids

    def test_get_playable_race_ids(self, manager):
        ids = manager.get_playable_race_ids()
        assert len(ids) == 2
        assert "human" in ids
        assert "dummy" in ids
        assert "goblin" not in ids

    def test_get_combatant_race_ids(self, manager):
        ids = manager.get_combatant_race_ids()
        assert len(ids) == 2
        assert "human" in ids
        assert "goblin" in ids
        assert "dummy" not in ids
