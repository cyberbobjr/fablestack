"""
Integration tests for stats data validation.

Purpose:
These tests validate that all stats data from stats.yaml can be correctly
loaded and parsed without errors. This ensures data consistency and prevents
runtime errors when loading stat information during character creation and
gameplay.
"""
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def stats_data() -> dict:
    """
    Load stats data from YAML file.
    
    Purpose:
    Provides access to the actual stats data from gamedata/stats.yaml
    for validation testing. This ensures tests run against real data.
    
    Returns:
        dict: Parsed stats data from YAML.
    """
    stats_path = Path(__file__).parent.parent.parent / "gamedata" / "stats.yaml"
    with open(stats_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_all_stats_load(stats_data: dict) -> None:
    """
    Test that all 6 stats from stats.yaml load correctly.
    
    Purpose:
    Validates that the stats section exists and contains all 6 expected stats
    (Strength, Constitution, Agility, Intelligence, Wisdom, Charisma). This
    ensures the YAML structure is correct and all stats are accessible.
    
    Args:
        stats_data: Parsed stats YAML data.
    """
    assert 'stats' in stats_data, "stats.yaml should have stats section"
    
    stats = stats_data['stats']
    expected_stats = ['Strength', 'Constitution', 'Agility', 'Intelligence', 'Wisdom', 'Charisma']
    
    assert len(stats) == 6, "Should have exactly 6 stats"
    
    for stat_name in expected_stats:
        assert stat_name in stats, f"Stat '{stat_name}' should exist"


def test_stats_have_required_fields(stats_data: dict) -> None:
    """
    Test that each stat has all required fields.
    
    Purpose:
    Validates that every stat has the required fields: short_name, category,
    description, and examples. This ensures stats can be properly displayed
    and used in the game.
    
    Args:
        stats_data: Parsed stats YAML data.
    """
    stats = stats_data['stats']
    required_fields = ['short_name', 'category', 'description', 'examples']
    
    for stat_name, stat_data in stats.items():
        for field in required_fields:
            assert field in stat_data, f"Stat '{stat_name}' should have field '{field}'"
        
        # Validate short_name is 3 characters
        assert len(stat_data['short_name']) == 3, f"Stat '{stat_name}' short_name should be 3 characters"
        assert stat_data['short_name'].isupper(), f"Stat '{stat_name}' short_name should be uppercase"
        
        # Validate category is one of the expected values
        valid_categories = ['physical', 'mental', 'social']
        assert stat_data['category'] in valid_categories, f"Stat '{stat_name}' category should be one of {valid_categories}"
        
        # Validate description is not empty
        assert len(stat_data['description']) > 0, f"Stat '{stat_name}' description should not be empty"
        
        # Validate examples is a list with at least one item
        assert isinstance(stat_data['examples'], list), f"Stat '{stat_name}' examples should be a list"
        assert len(stat_data['examples']) > 0, f"Stat '{stat_name}' should have at least one example"


def test_value_range_defined(stats_data: dict) -> None:
    """
    Test that value_range is properly defined.
    
    Purpose:
    Validates that the value_range section exists with min and max values.
    This ensures stat values can be properly validated during character
    creation and gameplay.
    
    Args:
        stats_data: Parsed stats YAML data.
    """
    assert 'value_range' in stats_data, "stats.yaml should have value_range section"
    
    value_range = stats_data['value_range']
    
    assert 'min' in value_range, "value_range should have min"
    assert 'max' in value_range, "value_range should have max"
    
    assert isinstance(value_range['min'], int), "value_range min should be an integer"
    assert isinstance(value_range['max'], int), "value_range max should be an integer"
    
    assert value_range['min'] == 3, "Minimum stat value should be 3"
    assert value_range['max'] == 20, "Maximum stat value should be 20"
    assert value_range['min'] < value_range['max'], "Min should be less than max"


def test_bonus_formula_defined(stats_data: dict) -> None:
    """
    Test that bonus_formula is properly defined.
    
    Purpose:
    Validates that the bonus_formula exists and contains the expected formula
    for calculating stat bonuses. This ensures stat bonuses can be correctly
    calculated during gameplay.
    
    Args:
        stats_data: Parsed stats YAML data.
    """
    assert 'bonus_formula' in stats_data, "stats.yaml should have bonus_formula"
    
    bonus_formula = stats_data['bonus_formula']
    
    assert isinstance(bonus_formula, str), "bonus_formula should be a string"
    assert len(bonus_formula) > 0, "bonus_formula should not be empty"
    assert '(value - 10) // 2' == bonus_formula, "bonus_formula should be '(value - 10) // 2'"


def test_stat_categories_distribution(stats_data: dict) -> None:
    """
    Test that stats are properly distributed across categories.
    
    Purpose:
    Validates that stats are distributed across physical, mental, and social
    categories as expected. This ensures a balanced character creation system.
    
    Args:
        stats_data: Parsed stats YAML data.
    """
    stats = stats_data['stats']
    
    categories = {'physical': 0, 'mental': 0, 'social': 0}
    
    for stat_name, stat_data in stats.items():
        category = stat_data['category']
        categories[category] += 1
    
    # Expected distribution: 3 physical, 2 mental, 1 social
    assert categories['physical'] == 3, "Should have 3 physical stats"
    assert categories['mental'] == 2, "Should have 2 mental stats"
    assert categories['social'] == 1, "Should have 1 social stat"
