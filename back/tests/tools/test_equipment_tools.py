from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.equipment_tools import (inventory_add_item,
                                        inventory_remove_item,
                                        list_available_equipment)


@pytest.fixture
def mock_character():
    """Create a mock character with gold"""
    stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    skills = Skills()
    combat_stats = CombatStats(max_hit_points=50, current_hit_points=50)
    equipment = Equipment(gold=100)
    
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        name="Test Hero",
        race="human",
        culture="gondor",
        stats=stats,
        skills=skills,
        combat_stats=combat_stats,
        equipment=equipment
    )
    return character


@pytest.fixture
def mock_session_service(mock_character):
    """Create a mock GameSessionService"""
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    
    # Mock specialized services
    service.character_service = MagicMock()
    service.character_service.get_character.return_value = mock_character
    service.character_service.add_currency = AsyncMock()
    
    service.equipment_service = MagicMock()
    service.equipment_service.equipment_exists.return_value = True # Default to existing for add tests
    service.equipment_service.add_item = AsyncMock()
    service.equipment_service.remove_item = AsyncMock()
    
    service.data_service = MagicMock()
    service.races_service = MagicMock()
    service.translation_agent = MagicMock()
    
    return service


@pytest.fixture
def mock_run_context(mock_session_service):
    """Create a mock RunContext"""
    mock_model = MagicMock()
    usage = RunUsage(requests=1)
    return RunContext(
        deps=mock_session_service, 
        retry=0, 
        tool_name="test_tool", 
        model=mock_model, 
        usage=usage
    )


@pytest.mark.asyncio
async def test_inventory_add_item_free(mock_run_context, mock_character):
    """Test adding a free item to inventory"""
    # Setup mocks
    mock_run_context.deps.equipment_service.add_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["weapon_sword"]
    
    # Execute
    result = await inventory_add_item(mock_run_context, "weapon_sword", qty=1)
    
    # Assert
    assert result["message"] == "Added 1 x weapon_sword"
    assert result["inventory"] == ["weapon_sword"]
    mock_run_context.deps.equipment_service.add_item.assert_called_once()


@pytest.mark.asyncio
async def test_inventory_add_item_service_unavailable(mock_run_context):
    """Test error handling when equipment service is unavailable"""
    mock_run_context.deps.equipment_service = None
    
    # Execute
    result = await inventory_add_item(mock_run_context, "sword", qty=1)
    
    # Assert
    assert "error" in result
    assert "service not available" in result["error"]


@pytest.mark.asyncio
async def test_inventory_add_item_exception_handling(mock_run_context):
    """Test that exceptions are caught and returned as errors"""
    # Setup mock to raise an exception
    # Need to simulate equipment_exists check passing, then add failing
    mock_run_context.deps.equipment_service.equipment_exists.side_effect = Exception("Unexpected error")
    
    # Execute
    result = await inventory_add_item(mock_run_context, "sword", qty=1)
    
    # Assert
    assert "error" in result
    assert "Unexpected error" in result["error"]


@pytest.mark.asyncio
async def test_inventory_remove_item(mock_run_context, mock_character):
    """Test removing an item from inventory"""
    # Setup mocks
    mock_run_context.deps.equipment_service.remove_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = []
    
    # Mock get_equipment_details to return an item matching "potion"
    mock_item = MagicMock()
    mock_item.name = "Potion"
    mock_item.id = "potion"
    # item_id property for check
    mock_item.item_id = "potion" 
    mock_run_context.deps.equipment_service.get_equipment_details.return_value = [mock_item]
    
    # Execute
    result = await inventory_remove_item(mock_run_context, "potion", qty=1)
    
    # Assert
    assert result["message"] == "Removed 1 x potion"
    assert result["inventory"] == []
    mock_run_context.deps.equipment_service.remove_item.assert_called_once_with(
        mock_character, item_id="potion", quantity=1
    )


@pytest.mark.asyncio
async def test_inventory_remove_item_service_unavailable(mock_run_context):
    """Test error handling when equipment service is unavailable"""
    mock_run_context.deps.equipment_service = None
    
    # Execute
    result = await inventory_remove_item(mock_run_context, "potion", qty=1)
    
    # Assert
    assert "error" in result
    assert "service not available" in result["error"]


@pytest.mark.asyncio
async def test_inventory_remove_item_exception_handling(mock_run_context):
    """Test that exceptions are caught and returned as errors"""
    # Setup mock to raise an exception
    mock_run_context.deps.character_service.get_character.side_effect = Exception("Remove error")
    
    # Execute
    result = await inventory_remove_item(mock_run_context, "potion", qty=1)
    
    # Assert
    assert "error" in result
    assert "Failed to remove item: Remove error" in result["error"]


@pytest.mark.asyncio
async def test_list_available_equipment_all(mock_run_context):
    """Test listing all available equipment"""
    # Setup mocks
    mock_equipment_manager = MagicMock()
    mock_equipment_manager.get_all_equipment.return_value = {
        "weapons": [
            {"id": "longsword", "name": "Longsword", "cost_gold": 15, "cost_silver": 0, "cost_copper": 0, "weight": 3, "damage": "1d8", "description": "A versatile blade", "can_buy": True}
        ],
        "armor": [
            {"id": "leather_armor", "name": "Leather Armor", "cost_gold": 10, "cost_silver": 0, "cost_copper": 0, "weight": 5, "protection": 2, "description": "Light protection", "can_buy": True}
        ],
        "accessories": [],
        "consumables": []
    }
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    
    # Execute
    result = await list_available_equipment(mock_run_context, category="all")
    
    # Assert
    assert "items" in result
    assert "weapons" in result["items"]
    assert "armor" in result["items"]
    assert len(result["items"]["weapons"]) == 1
    assert result["items"]["weapons"][0]["item_id"] == "longsword"
    assert result["items"]["weapons"][0]["cost"]["gold"] == 15
    assert "summary" in result


@pytest.mark.asyncio
async def test_list_available_equipment_by_category(mock_run_context):
    """Test listing equipment filtered by category"""
    # Setup mocks
    mock_equipment_manager = MagicMock()
    mock_equipment_manager.get_all_equipment.return_value = {
        "weapons": [
            {"id": "sword", "name": "Sword", "cost_gold": 10, "cost_silver": 0, "cost_copper": 0, "weight": 2, "damage": "1d6", "description": "Basic sword", "can_buy": True}
        ],
        "armor": [],
        "accessories": [],
        "consumables": []
    }
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    
    # Execute
    result = await list_available_equipment(mock_run_context, category="weapons")
    
    # Assert
    assert "items" in result
    assert "weapons" in result["items"]
    assert "armor" not in result["items"]
    assert result["category_filter"] == "weapons"


@pytest.mark.asyncio
async def test_list_available_equipment_invalid_category(mock_run_context):
    """Test error handling for invalid category"""
    # Setup mocks
    mock_equipment_manager = MagicMock()
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    
    # Execute
    result = await list_available_equipment(mock_run_context, category="invalid")
    
    # Assert
    assert "error" in result
    assert "Invalid category" in result["error"]


@pytest.mark.asyncio
async def test_list_available_equipment_exception_handling(mock_run_context):
    """Test that exceptions are caught and returned as errors"""
    # Setup mock to raise an exception
    mock_run_context.deps.equipment_service.equipment_manager = MagicMock()
    mock_run_context.deps.equipment_service.equipment_manager.get_all_equipment.side_effect = Exception("List error")
    
    # Execute
    result = await list_available_equipment(mock_run_context, category="all")
    
    # Assert
    assert "error" in result
    assert "Failed to list equipment: List error" in result["error"]
