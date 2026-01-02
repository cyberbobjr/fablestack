import os

import pytest
import yaml

from back.config import get_data_dir
from back.models.domain.equipment_manager import EquipmentManager


def test_create_item_persistence():
    """Test that create_item saves to YAML and updates cache"""
    manager = EquipmentManager()
    
    # 1. Create a new item
    item_data = {
        "name": "Sword of Testing",
        "cost_gold": 100,
        "weight": 2.5,
        "damage": "2d6",
        "description": "A test sword"
    }
    
    item_id = manager.create_item("weapon", item_data)
    
    # 2. Verify ID generation
    assert item_id == "weapon_sword-of-testing"
    
    # 3. Verify in-memory retrieval
    retrieved = manager.get_equipment_by_id(item_id)
    assert retrieved is not None
    assert retrieved["name"] == "Sword of Testing"
    assert retrieved["cost_gold"] == 100
    assert retrieved["damage"] == "2d6"
    
    # 4. Verify persistence to file
    data_path = os.path.join(get_data_dir(), 'equipment.yaml')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    assert "weapons" in data
    assert "Sword of Testing" in data["weapons"]
    saved_entry = data["weapons"]["Sword of Testing"]
    assert saved_entry["id"] == item_id
    assert saved_entry["cost_gold"] == 100
    assert saved_entry["damage"] == "2d6"

def test_create_item_complex_properties():
    """Test creating an item with all optional properties"""
    manager = EquipmentManager()
    
    item_data = {
        "name": "Magic Shield",
        "cost_gold": 50,
        "cost_silver": 5,
        "cost_copper": 10,
        "weight": 5.0,
        "protection": 3,
        "properties": "magical, sturdy",
        "quantity": 1,
        "description": "A shield"
    }
    
    item_id = manager.create_item("armor", item_data)
    
    # Verify persistence
    data_path = os.path.join(get_data_dir(), 'equipment.yaml')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    saved_entry = data["armor"]["Magic Shield"]
    assert saved_entry["protection"] == 3
    assert saved_entry["properties"] == "magical, sturdy"
    assert saved_entry["cost_silver"] == 5
