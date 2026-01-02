from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.equipment_tools import inventory_decrease_quantity


@pytest.fixture
def mock_character():
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
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    
    # Mock specialized services
    service.character_service = MagicMock()
    service.character_service.get_character.return_value = mock_character
    service.equipment_service = MagicMock()
    service.equipment_service.decrease_item_quantity = AsyncMock(return_value=mock_character)
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

@pytest.mark.asyncio
async def test_inventory_decrease_quantity_success(mock_run_context, mock_character):
    # Setup mocks
    mock_run_context.deps.equipment_service.decrease_item_quantity.return_value = mock_character
    mock_run_context.deps.equipment_service.get_equipment_list.return_value = ["Arrows (19)"]
    
    # Execute
    result = await inventory_decrease_quantity(mock_run_context, "Arrows (20)", amount=1)
    
    # Assert
    assert result["message"] == "Decreased Arrows (20) by 1"
    assert result["inventory"] == ["Arrows (19)"]
    mock_run_context.deps.equipment_service.decrease_item_quantity.assert_called_once_with(
        mock_character, item_id="Arrows (20)", amount=1
    )

@pytest.mark.asyncio
async def test_inventory_decrease_quantity_service_unavailable(mock_run_context):
    mock_run_context.deps.equipment_service = None
    
    result = await inventory_decrease_quantity(mock_run_context, "Arrows", amount=1)
    
    assert "error" in result
    assert "service not available" in result["error"]

@pytest.mark.asyncio
async def test_inventory_decrease_quantity_exception(mock_run_context):
    mock_run_context.deps.equipment_service.decrease_item_quantity.side_effect = Exception("Decrease error")
    
    result = await inventory_decrease_quantity(mock_run_context, "Arrows", amount=1)
    
    assert "error" in result
    assert "Failed to decrease quantity: Decrease error" in result["error"]
