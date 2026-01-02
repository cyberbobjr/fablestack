from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.character_tools import character_add_currency
from back.tools.equipment_tools import inventory_buy_item


@pytest.fixture
def mock_character():
    """Create a mock character with currency"""
    stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    skills = Skills()
    combat_stats = CombatStats(max_hit_points=50, current_hit_points=50)
    equipment = Equipment(gold=10, silver=5, copper=50) # Total: 1000 + 50 + 50 = 1100 copper
    
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
    service.character_service.add_currency = AsyncMock(return_value=mock_character)
    service.character_service.remove_currency = AsyncMock(return_value=mock_character)
    
    service.equipment_service = MagicMock()
    service.equipment_service.add_item = AsyncMock()
    
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
async def test_inventory_buy_item_success_gold_only(mock_run_context, mock_character):
    """Test buying an item costing only gold"""
    # Setup mocks
    mock_item = {"id": "sword", "cost_gold": 2, "cost_silver": 0, "cost_copper": 0}
    mock_run_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_item
    mock_run_context.deps.equipment_service.add_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["sword"]
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "sword", qty=1)
    
    # Assert
    assert "Purchased 1 x sword" in result["message"]
    assert result["transaction"]["cost"]["gold"] == 2
    # Initial: 10G 5S 50C = 1100C. Cost: 2G = 200C. Remaining: 900C.
    # Greedy redistribution: 9G 0S 0C.
    assert mock_character.gold == 9
    assert mock_character.silver == 0
    assert mock_character.copper == 0
    mock_run_context.deps.equipment_service.add_item.assert_called_once()

@pytest.mark.asyncio
async def test_inventory_buy_item_success_mixed_currency(mock_run_context, mock_character):
    """Test buying an item with mixed currency cost"""
    # Setup mocks
    mock_item = {"id": "dagger", "cost_gold": 0, "cost_silver": 5, "cost_copper": 10}
    mock_run_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_item
    mock_run_context.deps.equipment_service.add_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["dagger"]
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "dagger", qty=1)
    
    # Assert
    assert "Purchased 1 x dagger" in result["message"]
    # Initial: 10G 5S 50C = 1100C. Cost: 0G 5S 10C = 60C. Remaining: 1040C.
    # Greedy redistribution: 10G 4S 0C.
    assert mock_character.gold == 10
    assert mock_character.silver == 4
    assert mock_character.copper == 0

@pytest.mark.asyncio
async def test_inventory_buy_item_insufficient_funds(mock_run_context, mock_character):
    """Test buying an item with insufficient funds"""
    # Setup mocks
    mock_item = {"id": "expensive_armor", "cost_gold": 100, "cost_silver": 0, "cost_copper": 0}
    mock_run_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_item
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "expensive_armor", qty=1)
    
    # Assert
    assert "error" in result
    assert "Insufficient funds" in result["error"]
    mock_run_context.deps.equipment_service.add_item.assert_not_called()

@pytest.mark.asyncio
async def test_inventory_buy_item_with_conversion(mock_run_context, mock_character):
    """Test buying an item requiring currency conversion"""
    # Initial: 10G 5S 50C. Total Copper: 1100.
    # Cost: 0G 6S 0C (60C).
    # Player has 5S, needs 1S more. Should break 1G into 10S.
    # Result should be: 9G 9S 50C.
    
    # Setup mocks
    mock_item = {"id": "item", "cost_gold": 0, "cost_silver": 6, "cost_copper": 0}
    mock_run_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_item
    mock_run_context.deps.equipment_service.add_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["item"]
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "item", qty=1)
    
    # Assert
    assert "Purchased" in result["message"]
    # Check total value in copper to be safe
    expected_copper = 1100 - 60
    actual_copper = mock_character.equipment.get_total_in_copper()
    assert actual_copper == expected_copper
    
    # Check specific distribution (greedy algorithm)
    # 1040 copper -> 10G 4S 0C
    assert mock_character.gold == 10
    assert mock_character.silver == 4
    assert mock_character.copper == 0

@pytest.mark.asyncio
async def test_character_add_currency(mock_run_context, mock_character):
    """Test adding currency to character"""
    # Setup mock side effect to update character
    def side_effect(gold, silver, copper):
        mock_character.equipment.add_currency(gold, silver, copper)
        return mock_character
        
    mock_run_context.deps.character_service.add_currency.side_effect = side_effect

    # Execute
    result = await character_add_currency(mock_run_context, gold=5, silver=2, copper=10)
    
    # Assert
    assert "Added 5G 2S 10C" in result["message"]
    # Initial: 10G 5S 50C. Added: 5G 2S 10C. Result: 15G 7S 60C.
    assert mock_character.gold == 15
    assert mock_character.silver == 7
    assert mock_character.copper == 60
    mock_run_context.deps.character_service.save_character.assert_not_called() # Service calls save, but we mocked add_currency which calls save. Wait, if we mock add_currency, the REAL add_currency is not called, so save_character inside it is not called.
    # But our side effect only updates equipment. It doesn't call save.
    # So we shouldn't assert save_character is called unless we call it in side_effect.
    # But the tool doesn't call save_character directly. It relies on service.
    # So we should NOT assert save_character called here because we mocked the service method that does it.

@pytest.mark.asyncio
async def test_inventory_buy_ranged_weapon(mock_run_context, mock_character):
    """Test buying a ranged weapon with range field (regression test for Longbow bug)"""
    # Setup mocks - simulate Longbow data with range as integer
    mock_item = {
        "id": "longbow",
        "name": "Longbow",
        "category": "ranged",
        "cost_gold": 1,
        "cost_silver": 5,
        "cost_copper": 0,
        "weight": 1.0,
        "damage": "1d8+2",
        "range": 150,  # Integer value, not string - this was causing the bug
        "type": "weapon"
    }
    mock_run_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_item
    mock_run_context.deps.equipment_service.add_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["Longbow"]
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "longbow", qty=1)
    
    # Assert
    assert "Purchased 1 x longbow" in result["message"]
    assert result["transaction"]["cost"]["gold"] == 1
    assert result["transaction"]["cost"]["silver"] == 5
    # Initial: 10G 5S 50C = 1100C. Cost: 1G 5S = 150C. Remaining: 950C.
    # Greedy redistribution: 9G 5S 0C.
    assert mock_character.gold == 9
    assert mock_character.silver == 5
    assert mock_character.copper == 0
    mock_run_context.deps.equipment_service.add_item.assert_called_once()

@pytest.mark.asyncio
async def test_inventory_buy_armor_with_protection(mock_run_context, mock_character):
    """Test buying armor with protection field"""
    # Setup mocks - simulate Leather Armor data with protection field
    mock_item = {
        "id": "leather_armor",
        "name": "Leather Armor",
        "category": "armor",
        "cost_gold": 1,
        "cost_silver": 0,
        "cost_copper": 0,
        "weight": 5.0,
        "protection": 3,  # Integer protection value
        "type": "armor"
    }
    mock_run_context.deps.equipment_service.equipment_manager.get_equipment_by_id.return_value = mock_item
    mock_run_context.deps.equipment_service.add_item.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["Leather Armor"]
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "leather_armor", qty=1)
    
    # Assert
    assert "Purchased 1 x leather_armor" in result["message"]
    assert result["transaction"]["cost"]["gold"] == 1
    # Initial: 10G 5S 50C = 1100C. Cost: 1G = 100C. Remaining: 1000C.
    # Greedy redistribution: 10G 0S 0C.
    assert mock_character.gold == 10
    assert mock_character.silver == 0
    assert mock_character.copper == 0
    mock_run_context.deps.equipment_service.add_item.assert_called_once()

