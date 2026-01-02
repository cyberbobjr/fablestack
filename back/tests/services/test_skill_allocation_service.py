import pytest
from unittest.mock import MagicMock, patch
from back.services.skill_allocation_service import SkillAllocationService
from back.models.domain.character import Stats

@pytest.fixture
def mock_skills_manager():
    manager = MagicMock()
    manager.get_all_skills.return_value = {
        "combat": {"sword": {}, "archery": {}},
        "general": {"perception": {}, "athletics": {}}
    }
    manager.get_race_affinities.return_value = [{"sword": 2}]
    manager.get_stat_based_skill_bonuses.return_value = []
    manager.get_skill_by_name.return_value = {"group": "combat", "id": "sword"}
    return manager

@pytest.fixture
def service(mock_skills_manager):
    with patch('back.services.skill_allocation_service.UnifiedSkillsManager', return_value=mock_skills_manager):
        return SkillAllocationService()

@pytest.fixture
def sample_stats():
    return Stats(strength=12, constitution=10, agility=14, intelligence=10, wisdom=10, charisma=10)

class TestSkillAllocationService:

    def test_allocate_random_skills_initializes_all_skills(self, service, sample_stats, mock_skills_manager):
        """Test that all skills are initialized to 0."""
        result = service.allocate_random_skills_for_character("human", "empire", sample_stats)
        
        assert "combat" in result
        assert "general" in result
        assert "sword" in result["combat"]
        assert "perception" in result["general"]

    def test_allocate_race_affinities(self, service, sample_stats, mock_skills_manager):
        """Test that race affinities are applied."""
        result = service.allocate_random_skills_for_character("human", "empire", sample_stats)
        
        # Sword should have at least 2 points from race affinity
        assert result["combat"]["sword"] >= 2

    def test_calculate_total_points(self, service):
        """Test total points calculation."""
        allocated = {
            "combat": {"sword": 5, "archery": 3},
            "general": {"perception": 2}
        }
        
        total = service._calculate_total_points(allocated)
        
        assert total == 10

    def test_allocate_stat_bonuses(self, service):
        """Test stat bonus allocation."""
        allocated = {"combat": {"sword": 0}}
        bonuses = [("combat", "sword", 3)]
        
        result = service._allocate_stat_bonuses(allocated, bonuses)
        
        assert result["combat"]["sword"] == 3

    def test_distribute_remaining_points(self, service):
        """Test random distribution of remaining points."""
        allocated = {
            "combat": {"sword": 0, "archery": 0},
            "general": {"perception": 0}
        }
        
        result = service._distribute_remaining_points(allocated, 10)
        
        total = service._calculate_total_points(result)
        assert total == 10
