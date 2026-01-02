"""
Integration test configuration and shared fixtures.
"""

from logging import basicConfig
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def mock_equipment_manager():
    """Mock EquipmentManager with minimal test data"""
    
    class FakeEquipmentManager:
        """Fake equipment manager that returns real dicts"""
        
        def get_equipment_by_id(self, item_id: str):
            """Return equipment data as a real dict"""
            return {
                "id": "test_sword",
                "name": "Test Sword",
                "cost": 50,
                "weight": 3,
                "damage": "1d8",
                "type": "melee",
                "category": "weapons",
                "description": "A test sword",
                "range": None,
                "defense": None
            }
        
        def get_item(self, item_id: str):
            """Return item data"""
            return {
                "id": "test_sword",
                "name": "Test Sword",
                "cost": 50,
                "damage": "1d8",
                "type": "weapon"
            }
        
        def list_by_category(self, category: str):
            """List items by category"""
            return [
                {"id": "test_sword", "name": "Test Sword", "cost": 50}
            ]
    
    return FakeEquipmentManager()


@pytest.fixture
def mock_race_manager():
    """Mock RaceManager with minimal test data"""
    mock = MagicMock()
    
    mock.get_race.return_value = {
        "name": "Human",
        "stat_bonuses": {"strength": 1, "constitution": 0, "agility": 0, "intelligence": 0, "wisdom": 0, "charisma": 0}
    }
    
    return mock


@pytest.fixture(scope="function", autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    """Create temporary data directory for tests with real file persistence"""
    # Create subdirectories for persistence
    (tmp_path / "characters").mkdir()
    (tmp_path / "sessions").mkdir()
    (tmp_path / "scenarios").mkdir()
    
    # Copy static data files from production
    base_dir = Path(__file__).parent.parent.parent # back/tests/integration -> back/tests -> back
    prod_data_dir = base_dir / "gamedata"
    
    import shutil
    for filename in ['equipment.yaml', 'skills.yaml', 'races_and_cultures.yaml', 'stats.yaml']:
        src = prod_data_dir / filename
        dst = tmp_path / filename
        if src.exists():
            shutil.copy2(src, dst)

    # Use monkeypatch to ensure patches persist for entire test
    # Patch the config instance method, not the wrapper function
    monkeypatch.setattr('back.config.config.get_data_dir', lambda: str(tmp_path))
    


    return tmp_path


@pytest.fixture
def test_character_data():
    """Create test character data with known stats"""
    from back.models.domain.character import (Character, CombatStats,
                                              Equipment, Skills, Stats)
    
    stats = Stats(
        strength=10,
        constitution=10,
        agility=10,
        intelligence=10,
        wisdom=10,
        charisma=10
    )
    
    skills = Skills()
    
    combat_stats = CombatStats(
        max_hit_points=50,
        current_hit_points=50,
        armor_class=10
    )
    
    equipment = Equipment(gold=100)
    
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        name="Test Hero",
        race="human",
        culture="gondor",
        stats=stats,
        skills=skills,
        combat_stats=combat_stats,
        equipment=equipment,
        level=1,
        experience_points=0
    )
    
    return character


@pytest.fixture
def test_character(temp_data_dir, test_character_data):
    """Create a test character and save to temp directory"""
    import json

    # Generate character ID
    character_id = str(uuid4())
    
    # Save character to temp directory manually (since we're in test context)
    char_file = temp_data_dir / "characters" / f"{character_id}.json"
    
    # Convert character to dict for saving
    char_dict = test_character_data.model_dump(mode='json')
    char_dict['id'] = character_id
    
    char_file.write_text(json.dumps(char_dict, indent=2))
    
    return character_id, test_character_data


@pytest.fixture
def test_scenario_success(temp_data_dir):
    """Create a test scenario file for success testing"""
    scenario_content = """# Test Success Scenario

You are testing the scenario end system.

**IMPORTANT INSTRUCTIONS:**
- When the player says "I complete the quest", you MUST call `end_scenario_tool` with outcome="success", xp_reward=100, gold_reward=50
- Be very concise in your responses
- Follow instructions exactly
"""
    scenario_path = temp_data_dir / "scenarios" / "test_scenario_success.md"
    scenario_path.write_text(scenario_content)
    return "test_scenario_success.md"


@pytest.fixture
def test_scenario_failure(temp_data_dir):
    """Create a test scenario file for failure testing"""
    scenario_content = """# Test Failure Scenario

You are testing the scenario end system.

**IMPORTANT INSTRUCTIONS:**
- When the player says "I acknowledge the failure", you MUST call `end_scenario_tool` with outcome="failure"
- Be very concise in your responses
- Follow instructions exactly
"""
    scenario_path = temp_data_dir / "scenarios" / "test_scenario_failure.md"
    scenario_path.write_text(scenario_content)
    return "test_scenario_failure.md"


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "llm: mark test as requiring real LLM calls (slow)"
    )


