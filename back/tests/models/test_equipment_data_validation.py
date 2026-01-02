"""
Integration tests for equipment data validation.

Purpose:
These tests validate that all equipment data from the YAML files can be correctly
loaded and converted into EquipmentItem Pydantic models without validation errors.
This ensures type consistency between YAML data and Python models, preventing
runtime errors when loading equipment during gameplay.
"""
import pytest
from back.models.domain.equipment_manager import EquipmentManager
from back.models.domain.items import EquipmentItem


@pytest.fixture
def equipment_manager() -> EquipmentManager:
    """
    Create an EquipmentManager instance with real YAML data.
    
    Purpose:
    Provides access to the actual equipment data from gamedata/equipment.yaml
    for validation testing. This ensures tests run against real data rather
    than mocks, catching type mismatches and validation errors.
    
    Returns:
        EquipmentManager: Manager instance loaded with real equipment data.
    """
    return EquipmentManager()


def test_all_weapons_load_correctly(equipment_manager: EquipmentManager) -> None:
    """
    Test that all weapons from equipment.yaml load without validation errors.
    
    Purpose:
    Validates that every weapon in the YAML file can be converted to an
    EquipmentItem model. This catches type mismatches (e.g., range as int vs str)
    and missing required fields before they cause runtime errors.
    
    Args:
        equipment_manager: Manager with loaded equipment data.
    """
    weapons = equipment_manager.get_weapons()
    assert len(weapons) > 0, "Should have at least one weapon in YAML"
    
    for weapon_name, weapon_data in weapons.items():
        # Attempt to create EquipmentItem - will raise ValidationError if types mismatch
        item = EquipmentItem(
            id=weapon_name.lower().replace(" ", "_"),
            item_id=weapon_name.lower().replace(" ", "_"),
            name=weapon_name,
            category=weapon_data.get('category', 'melee'),
            cost_gold=weapon_data.get('cost_gold', 0),
            cost_silver=weapon_data.get('cost_silver', 0),
            cost_copper=weapon_data.get('cost_copper', 0),
            weight=weapon_data.get('weight', 0.0),
            quantity=1,
            equipped=False,
            description=weapon_data.get('description'),
            damage=weapon_data.get('damage'),
            range=weapon_data.get('range'),
            protection=weapon_data.get('protection'),
            type=weapon_data.get('type')
        )
        assert item is not None
        assert item.name == weapon_name


def test_all_armor_load_correctly(equipment_manager: EquipmentManager) -> None:
    """
    Test that all armor from equipment.yaml load without validation errors.
    
    Purpose:
    Validates that every armor piece in the YAML file can be converted to an
    EquipmentItem model. This ensures the protection field is correctly typed
    as an integer and all required fields are present.
    
    Args:
        equipment_manager: Manager with loaded equipment data.
    """
    armor = equipment_manager.get_armor()
    assert len(armor) > 0, "Should have at least one armor in YAML"
    
    for armor_name, armor_data in armor.items():
        item = EquipmentItem(
            id=armor_name.lower().replace(" ", "_"),
            item_id=armor_name.lower().replace(" ", "_"),
            name=armor_name,
            category=armor_data.get('category', 'armor'),
            cost_gold=armor_data.get('cost_gold', 0),
            cost_silver=armor_data.get('cost_silver', 0),
            cost_copper=armor_data.get('cost_copper', 0),
            weight=armor_data.get('weight', 0.0),
            quantity=1,
            equipped=False,
            description=armor_data.get('description'),
            damage=armor_data.get('damage'),
            range=armor_data.get('range'),
            protection=armor_data.get('protection'),
            type=armor_data.get('type')
        )
        assert item is not None
        assert item.name == armor_name


def test_all_items_load_correctly(equipment_manager: EquipmentManager) -> None:
    """
    Test that all general items from equipment.yaml load without validation errors.
    
    Purpose:
    Validates that every general item (rope, torch, etc.) in the YAML file can
    be converted to an EquipmentItem model. These items typically don't have
    damage, range, or protection fields, testing the Optional typing.
    
    Args:
        equipment_manager: Manager with loaded equipment data.
    """
    items = equipment_manager.get_items()
    assert len(items) > 0, "Should have at least one item in YAML"
    
    for item_name, item_data in items.items():
        item = EquipmentItem(
            id=item_name.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            item_id=item_name.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            name=item_name,
            category=item_data.get('category', 'equipment'),
            cost_gold=item_data.get('cost_gold', 0),
            cost_silver=item_data.get('cost_silver', 0),
            cost_copper=item_data.get('cost_copper', 0),
            weight=item_data.get('weight', 0.0),
            quantity=1,
            equipped=False,
            description=item_data.get('description'),
            damage=item_data.get('damage'),
            range=item_data.get('range'),
            protection=item_data.get('protection'),
            type=item_data.get('type')
        )
        assert item is not None
        assert item.name == item_name


def test_longbow_has_range(equipment_manager: EquipmentManager) -> None:
    """
    Test that Longbow has a range field as an integer.
    
    Purpose:
    Specific regression test for the bug that caused this fix. The Longbow
    has a range value of 150 (int) in the YAML, which previously caused a
    ValidationError because EquipmentItem expected a string. This test ensures
    the fix works correctly.
    
    Args:
        equipment_manager: Manager with loaded equipment data.
    """
    longbow = equipment_manager.get_equipment_by_id("longbow")
    assert longbow is not None, "Longbow should exist in equipment.yaml"
    
    item = EquipmentItem(
        id="longbow",
        item_id="longbow",
        name=longbow['name'],
        category=longbow.get('category', 'ranged'),
        cost_gold=longbow.get('cost_gold', 0),
        cost_silver=longbow.get('cost_silver', 0),
        cost_copper=longbow.get('cost_copper', 0),
        weight=longbow.get('weight', 0.0),
        quantity=1,
        equipped=False,
        description=longbow.get('description'),
        damage=longbow.get('damage'),
        range=longbow.get('range'),
        protection=longbow.get('protection'),
        type=longbow.get('type')
    )
    
    assert item.range is not None, "Longbow should have a range"
    assert isinstance(item.range, int), "Range should be an integer"
    assert item.range == 150, "Longbow range should be 150"


def test_armor_has_protection(equipment_manager: EquipmentManager) -> None:
    """
    Test that armor items have protection field as an integer.
    
    Purpose:
    Validates that armor pieces correctly have the protection field set as
    an integer value. This ensures the service correctly reads 'protection'
    from YAML (not the old 'defense' field).
    
    Args:
        equipment_manager: Manager with loaded equipment data.
    """
    # Use the exact name from YAML
    leather_armor = equipment_manager.get_equipment_by_id("Leather Armor")
    assert leather_armor is not None, "Leather Armor should exist in equipment.yaml"
    
    item = EquipmentItem(
        id="leather_armor",
        item_id="leather_armor",
        name=leather_armor['name'],
        category=leather_armor.get('category', 'armor'),
        cost_gold=leather_armor.get('cost_gold', 0),
        cost_silver=leather_armor.get('cost_silver', 0),
        cost_copper=leather_armor.get('cost_copper', 0),
        weight=leather_armor.get('weight', 0.0),
        quantity=1,
        equipped=False,
        description=leather_armor.get('description'),
        damage=leather_armor.get('damage'),
        range=leather_armor.get('range'),
        protection=leather_armor.get('protection'),
        type=leather_armor.get('type')
    )
    
    assert item.protection is not None, "Leather Armor should have protection"
    assert isinstance(item.protection, int), "Protection should be an integer"
    assert item.protection == 3, "Leather Armor protection should be 3"


def test_weapons_have_damage(equipment_manager: EquipmentManager) -> None:
    """
    Test that all weapons have a damage field as a string.
    
    Purpose:
    Validates that all weapons have the damage field set as a string containing
    the dice formula (e.g., "1d8+2"). This ensures weapons are properly configured
    for combat calculations.
    
    Args:
        equipment_manager: Manager with loaded equipment data.
    """
    weapons = equipment_manager.get_weapons()
    
    for weapon_name, weapon_data in weapons.items():
        item = EquipmentItem(
            id=weapon_name.lower().replace(" ", "_"),
            item_id=weapon_name.lower().replace(" ", "_"),
            name=weapon_name,
            category=weapon_data.get('category', 'melee'),
            cost_gold=weapon_data.get('cost_gold', 0),
            cost_silver=weapon_data.get('cost_silver', 0),
            cost_copper=weapon_data.get('cost_copper', 0),
            weight=weapon_data.get('weight', 0.0),
            quantity=1,
            equipped=False,
            description=weapon_data.get('description'),
            damage=weapon_data.get('damage'),
            range=weapon_data.get('range'),
            protection=weapon_data.get('protection'),
            type=weapon_data.get('type')
        )
        
        assert item.damage is not None, f"{weapon_name} should have damage"
        assert isinstance(item.damage, str), f"{weapon_name} damage should be a string"
        assert 'd' in item.damage, f"{weapon_name} damage should be a dice formula"
