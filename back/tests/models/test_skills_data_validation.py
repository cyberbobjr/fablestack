"""
Integration tests for skills data validation.

Purpose:
These tests validate that all skill data from skills.yaml can be correctly
loaded and parsed without errors. This ensures data consistency and prevents
runtime errors when loading skill information during character creation and
gameplay.
"""
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def skills_data() -> dict:
    """
    Load skills data from YAML file.
    
    Purpose:
    Provides access to the actual skills data from gamedata/skills.yaml
    for validation testing. This ensures tests run against real data.
    
    Returns:
        dict: Parsed skills data from YAML.
    """
    skills_path = Path(__file__).parent.parent.parent / "gamedata" / "skills.yaml"
    with open(skills_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_all_skill_groups_load(skills_data: dict) -> None:
    """
    Test that all skill groups from skills.yaml load correctly.
    
    Purpose:
    Validates that the skill_groups section exists and contains all expected
    skill groups with proper structure. This ensures the YAML structure is
    correct and all skill groups are accessible.
    
    Args:
        skills_data: Parsed skills YAML data.
    """
    assert 'skill_groups' in skills_data, "skills.yaml should have skill_groups section"
    
    skill_groups = skills_data['skill_groups']
    expected_groups = [
        "artistic", "magic_arts", "athletic", 
        "combat", "general"
    ]
    
    for group_name in expected_groups:
        assert group_name in skill_groups, f"Skill group '{group_name}' should exist"
        assert 'name' in skill_groups[group_name], f"Group '{group_name}' should have a name"
        assert 'skills' in skill_groups[group_name], f"Group '{group_name}' should have skills"
        assert len(skill_groups[group_name]['skills']) > 0, f"Group '{group_name}' should have at least one skill"


def test_skills_have_required_fields(skills_data: dict) -> None:
    """
    Test that all skills have required fields.
    
    Purpose:
    Validates that every skill has the minimum required fields: id, name, and
    description. This ensures skills can be properly displayed and used in
    the game.
    
    Args:
        skills_data: Parsed skills YAML data.
    """
    skill_groups = skills_data['skill_groups']
    
    for group_name, group_data in skill_groups.items():
        for skill_id, skill_data in group_data['skills'].items():
            assert 'id' in skill_data, f"Skill '{skill_id}' in '{group_name}' should have an id"
            assert 'name' in skill_data, f"Skill '{skill_id}' in '{group_name}' should have a name"
            assert 'description' in skill_data, f"Skill '{skill_id}' in '{group_name}' should have a description"
            
            # Validate id matches key
            assert skill_data['id'] == skill_id, f"Skill id '{skill_data['id']}' should match key '{skill_id}'"


def test_skills_with_stat_bonuses(skills_data: dict) -> None:
    """
    Test that skills with stat_bonuses have correct structure.
    
    Purpose:
    Validates that skills with stat bonuses (e.g., storytelling, weapon_handling)
    have the correct structure with min_value and bonus_points. This ensures
    stat bonuses can be correctly applied during character creation.
    
    Args:
        skills_data: Parsed skills YAML data.
    """
    skill_groups = skills_data['skill_groups']
    skills_with_bonuses = []
    
    for group_name, group_data in skill_groups.items():
        for skill_id, skill_data in group_data['skills'].items():
            if 'stat_bonuses' in skill_data:
                skills_with_bonuses.append((group_name, skill_id, skill_data))
    
    assert len(skills_with_bonuses) > 0, "Should have at least one skill with stat bonuses"
    
    for group_name, skill_id, skill_data in skills_with_bonuses:
        stat_bonuses = skill_data['stat_bonuses']
        
        # Each stat bonus should have a stat name as key
        for stat_name, bonus_data in stat_bonuses.items():
            assert 'min_value' in bonus_data, f"Skill '{skill_id}' stat bonus for '{stat_name}' should have min_value"
            assert 'bonus_points' in bonus_data, f"Skill '{skill_id}' stat bonus for '{stat_name}' should have bonus_points"
            
            # Validate types
            assert isinstance(bonus_data['min_value'], int), f"min_value should be int for '{skill_id}'"
            assert isinstance(bonus_data['bonus_points'], int), f"bonus_points should be int for '{skill_id}'"
            
            # Validate reasonable ranges
            assert 3 <= bonus_data['min_value'] <= 20, f"min_value should be between 3-20 for '{skill_id}'"
            assert bonus_data['bonus_points'] > 0, f"bonus_points should be positive for '{skill_id}'"


def test_racial_affinities_load(skills_data: dict) -> None:
    """
    Test that all racial affinities load correctly.
    
    Purpose:
    Validates that the racial_affinities section exists and contains proper
    structure for all races. This ensures racial skill bonuses can be correctly
    applied during character creation.
    
    Args:
        skills_data: Parsed skills YAML data.
    """
    assert 'racial_affinities' in skills_data, "skills.yaml should have racial_affinities section"
    
    racial_affinities = skills_data['racial_affinities']
    expected_races = [
        'Noldor', 'Longbeards', 'Rohirrim', 'Northmen', 'Brandybucks',
        'Gondorians', 'Harfoots', 'Silvan', 'Firebeards', 'Sindar',
        'Stoors', 'Dúnedain'
    ]
    
    for race_name in expected_races:
        assert race_name in racial_affinities, f"Race '{race_name}' should have affinities"
        affinities = racial_affinities[race_name]
        
        assert isinstance(affinities, list), f"Affinities for '{race_name}' should be a list"
        assert len(affinities) > 0, f"Race '{race_name}' should have at least one affinity"
        
        for affinity in affinities:
            assert 'skill' in affinity, f"Affinity for '{race_name}' should have skill"
            assert 'base_points' in affinity, f"Affinity for '{race_name}' should have base_points"
            assert isinstance(affinity['base_points'], int), f"base_points should be int for '{race_name}'"
            assert affinity['base_points'] > 0, f"base_points should be positive for '{race_name}'"


def test_skill_ids_are_valid(skills_data: dict) -> None:
    """
    Test that all skill IDs use valid format (lowercase with underscores).
    
    Purpose:
    Validates that skill IDs follow a consistent naming convention, making
    them easier to reference in code and preventing case-sensitivity issues.
    
    Args:
        skills_data: Parsed skills YAML data.
    """
    skill_groups = skills_data['skill_groups']
    
    for group_name, group_data in skill_groups.items():
        for skill_id in group_data['skills'].keys():
            # Should be lowercase with underscores
            assert skill_id.islower() or '_' in skill_id, f"Skill ID '{skill_id}' should be lowercase with underscores"
            assert ' ' not in skill_id, f"Skill ID '{skill_id}' should not contain spaces"
