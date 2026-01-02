from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.models.domain.equipment_manager import EquipmentManager
from back.models.domain.items import EquipmentItem

client = TestClient(app)

@pytest.fixture
def mock_equipment_manager_override():
    injector = app.state.injector
    # Retrieve the real singleton instance
    real_manager = injector.get(EquipmentManager)
    
    # Create a mock for the method we want to override
    mock_get_all = MagicMock()
    
    # Save original method
    original_get_all = real_manager.get_all_equipment
    
    # Apply patch
    real_manager.get_all_equipment = mock_get_all
    
    # We yield the real manager (which now has a mocked method)
    # But strictly speaking we should yield the mock logic controller (mock_get_all) or the manager.
    # The test expects a mock interface. 
    # Let's yield a MagicMock that wraps the real_manager but allows configuring get_all_equipment easily?
    # Or just yield the real_manager, and the test configures real_manager.get_all_equipment.return_value... 
    # BUT real_manager.get_all_equipment IS now a MagicMock.
    
    yield real_manager
    
    # Restore original method
    real_manager.get_all_equipment = original_get_all

def test_get_equipment_success(mock_equipment_manager_override):
    """
    Test that the equipment endpoint returns the correct structure and handles data conversion.
    """
    mock_equipment_manager = mock_equipment_manager_override
    
    # Mock equipment data as it would come from the YAML file
    mock_data = {
        "weapons": [
            {
                "id": "weapon_longsword",
                "name": "Longsword",
                "category": "weapon",
                "cost": 15.0,
                "weight": 3.0,
                "quantity": 1,
                "equipped": False,
                "description": "A well-balanced one-handed sword",
                "damage": "1d8",
                "range": None
            }
        ],
        "armor": [
            {
                "id": "armor_chain_mail",
                "name": "Chain Mail",
                "category": "armor",
                "cost": 75.0,
                "weight": 55.0,
                "quantity": 1,
                "equipped": False,
                "description": "Flexible metal armor",
                "protection": 16
            }
        ],
        "accessories": [],
        "consumables": [],
        "items": [
            {
                "id": "item_rope",
                "name": "Rope",
                "type": "equipment",
                "weight": 2.0,
                "cost": 0.1
            }
        ]
    }
    
    mock_equipment_manager.get_all_equipment.return_value = mock_data

    response = client.get("/api/creation/equipment")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "weapons" in data
    assert "armor" in data
    assert "accessories" in data
    assert "consumables" in data
    assert "general" in data
    
    # Verify weapon conversion
    weapon = data["weapons"][0]
    assert weapon["item_id"] == "weapon_longsword"
    assert weapon["cost_gold"] == 15
    assert weapon["cost_silver"] == 0
    
    # Verify armor conversion
    armor = data["armor"][0]
    assert armor["item_id"] == "armor_chain_mail"
    assert armor["cost_gold"] == 75
    
    # Verify general item conversion
    rope = data["general"][0]
    assert rope["item_id"] == "item_rope"
    assert rope["type"] == "equipment"

def test_get_equipment_cost_conversion(mock_equipment_manager_override):
    """
    Test cost conversion logic (gold/silver/copper).
    """
    mock_equipment_manager = mock_equipment_manager_override
    
    # Mock equipment data as it would come from the YAML file
    mock_data = {
        "weapons": [
            {
                "id": "weapon_dagger",
                "name": "Dagger",
                "category": "weapon",
                "cost": 2.5, # 2 Gold, 5 Silver
                "weight": 1.0,
                "quantity": 1,
                "equipped": False
            }
        ],
        "armor": [],
        "accessories": [],
        "consumables": []
    }
    
    mock_equipment_manager.get_all_equipment.return_value = mock_data

    response = client.get("/api/creation/equipment")
    
    assert response.status_code == 200
    data = response.json()
    
    weapon = data["weapons"][0]
    assert weapon["cost_gold"] == 2
    assert weapon["cost_silver"] == 5
    assert weapon["cost_copper"] == 0
