
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.models.domain.items import EquipmentItem
from back.services.game_session_service import GameSessionService
from back.tools.equipment_tools import inventory_sell_item


@pytest.fixture
def mock_character():
    """Create a mock character with some items"""
    stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    skills = Skills()
    combat_stats = CombatStats(max_hit_points=50, current_hit_points=50)
    
    # Create an item to sell
    sword = EquipmentItem(
        id="sword-uuid-1",
        item_id="weapon_longsword",
        name="Longsword",
        category="weapon",
        quantity=1,
        weight=1.5,
        cost_gold=10, # Value 10G
        cost_silver=0,
        cost_copper=0, 
        equipped=False
    )
    
    equipment = Equipment(
        gold=0, silver=0, copper=0,
        weapons=[sword]
    )
    
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        name="Test Merchant",
        race="human",
        culture="merchant",
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
    service.equipment_service.remove_item = AsyncMock()
    
    # Mock catalog lookup
    mock_catalog_item = {
        "id": "weapon_longsword",
        "name": "Longsword",
        "cost_gold": 10,
        "cost_silver": 0,
        "cost_copper": 0
    }
    service.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_catalog_item
    
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
async def test_inventory_sell_item_success(mock_run_context, mock_character):
    """Test selling an item successfully"""
    # 1. Setup: Character has 0G, sells Longsword (value 10G) -> expects 5G
    
    # Execute
    result = await inventory_sell_item(mock_run_context, "weapon_longsword", qty=1)
    
    # Assert
    assert result["transaction"] == "success"
    assert "Sold 1 x Longsword" in result["message"]
    # Check refund match
    assert result["refund"]["gold"] == 5
    assert result["refund"]["silver"] == 0
    
    # Verify service calls
    mock_run_context.deps.equipment_service.remove_item.assert_called_once()
    mock_run_context.deps.character_service.add_currency.assert_called_once_with(5, 0, 0)


@pytest.mark.asyncio
async def test_inventory_sell_item_not_found(mock_run_context):
    """Test selling an item that doesn't exist"""
    # Execute
    result = await inventory_sell_item(mock_run_context, "non_existent_item", qty=1)
    
    # Assert
    assert "error" in result
    assert "not found in inventory" in result["error"]
    
    # Verify NO service calls
    mock_run_context.deps.equipment_service.remove_item.assert_not_called()
    mock_run_context.deps.character_service.add_currency.assert_not_called()


@pytest.mark.asyncio
async def test_inventory_sell_item_quantity_error(mock_run_context, mock_character):
    """Test selling more items than possessed"""
    # Character has 1 sword, try to sell 2
    
    # Execute
    result = await inventory_sell_item(mock_run_context, "weapon_longsword", qty=2)
    
    # Assert
    assert "error" in result
    assert "Not enough items" in result["error"] 
    # Or "not found" depending on implementation details, checking logic
    
    # Verify NO service calls
    mock_run_context.deps.equipment_service.remove_item.assert_not_called()
    mock_run_context.deps.character_service.add_currency.assert_not_called()


@pytest.mark.asyncio
async def test_inventory_sell_item_value_calculation(mock_run_context, mock_character):
    """Test value calculation handles complex currency (e.g. silver)"""
    # Setup: item worth 1G 5S (150 copper) -> 50% = 75 copper -> 0G 7S 5C
    
    # Modify catalog mock
    mock_context = mock_run_context
    mock_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = {
        "cost_gold": 1,
        "cost_silver": 5,
        "cost_copper": 0
    }
    
    # Execute
    result = await inventory_sell_item(mock_context, "weapon_longsword", qty=1)
    
    # Assert
    assert result["transaction"] == "success"
    assert result["refund"]["gold"] == 0
    assert result["refund"]["silver"] == 7
    assert result["refund"]["copper"] == 5
    
    mock_context.deps.character_service.add_currency.assert_called_once_with(0, 7, 5)
