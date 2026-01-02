from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.character_tools import character_remove_currency
from back.tools.equipment_tools import inventory_increase_quantity


@pytest.fixture
def mock_character():
    stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    skills = Skills()
    combat_stats = CombatStats(max_hit_points=50, current_hit_points=50)
    equipment = Equipment(gold=100, silver=5, copper=3)
    
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
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    
    # Mock specialized services
    service.character_service = MagicMock()
    service.character_service.get_character.return_value = mock_character
    service.character_service.remove_currency = AsyncMock(return_value=mock_character)
    service.equipment_service = MagicMock()
    service.equipment_service.increase_item_quantity = AsyncMock(return_value=mock_character)
    service.equipment_service.get_equipment_list = MagicMock(return_value=[])
    service.data_service = MagicMock()
    service.races_service = MagicMock()
    service.translation_agent = MagicMock()
    
    return service

@pytest.fixture
def mock_run_context(mock_session_service):
    mock_model = MagicMock()
    usage = RunUsage(requests=1)
    return RunContext(
        deps=mock_session_service, 
        retry=0, 
        tool_name="test_tool", 
        model=mock_model, 
        usage=usage
    )

# Tests for character_remove_currency

@pytest.mark.asyncio
async def test_character_remove_currency_success(mock_run_context, mock_character):
    mock_character.equipment.gold = 50
    mock_character.equipment.silver = 3
    mock_character.equipment.copper = 7
    
    result = await character_remove_currency(mock_run_context, gold=10, silver=2, copper=5)
    
    assert "message" in result
    assert "Removed 10G 2S 5C" in result["message"]
    assert "currency" in result
    mock_run_context.deps.character_service.remove_currency.assert_called_once_with(10, 2, 5)

@pytest.mark.asyncio
async def test_character_remove_currency_insufficient_funds(mock_run_context):
    mock_run_context.deps.character_service.remove_currency.side_effect = ValueError("Insufficient funds")
    
    result = await character_remove_currency(mock_run_context, gold=1000)
    
    assert "error" in result
    assert "Insufficient funds" in result["error"]

@pytest.mark.asyncio
async def test_character_remove_currency_service_unavailable(mock_run_context):
    mock_run_context.deps.character_service = None
    
    result = await character_remove_currency(mock_run_context, gold=10)
    
    assert "error" in result
    assert "service not available" in result["error"]

# Tests for inventory_increase_quantity

@pytest.mark.asyncio
async def test_inventory_increase_quantity_success(mock_run_context, mock_character):
    result = await inventory_increase_quantity(mock_run_context, "item_arrows", amount=5)
    
    assert "message" in result
    assert "Increased item_arrows by 5" in result["message"]
    assert "inventory" in result
    mock_run_context.deps.equipment_service.increase_item_quantity.assert_called_once_with(
        mock_character, item_id="item_arrows", amount=5
    )

@pytest.mark.asyncio
async def test_inventory_increase_quantity_service_unavailable(mock_run_context):
    mock_run_context.deps.equipment_service = None
    
    result = await inventory_increase_quantity(mock_run_context, "Arrows", amount=1)
    
    assert "error" in result
    assert "service not available" in result["error"]

@pytest.mark.asyncio
async def test_inventory_increase_quantity_exception(mock_run_context):
    mock_run_context.deps.equipment_service.increase_item_quantity.side_effect = Exception("Increase error")
    
    result = await inventory_increase_quantity(mock_run_context, "Arrows", amount=1)
    
    assert "error" in result
    assert "Failed to increase quantity: Increase error" in result["error"]
