from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.equipment_tools import (create_armor, create_item,
                                        create_weapon, inventory_add_item)


@pytest.fixture
def mock_character():
    """Create a mock character"""
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
    service.equipment_service = MagicMock()
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
async def test_inventory_add_item_not_found(mock_run_context):
    """Test inventory_add_item when item does NOT exist"""
    # Setup
    mock_run_context.deps.equipment_service.equipment_exists.return_value = False
    
    # Execute
    result = await inventory_add_item(mock_run_context, "unknown_item", qty=1)
    
    # Assert
    assert "error" in result
    assert "not found in catalog" in result["error"]
    assert "create_weapon" in result["error"] # Check new error message
    mock_run_context.deps.equipment_service.add_item.assert_not_called()

@pytest.mark.asyncio
@patch('back.tools.equipment_tools.asyncio')
async def test_create_weapon_success(mock_asyncio, mock_run_context, mock_character):
    """Test create_weapon tool success"""
    # Setup
    mock_run_context.deps.equipment_service.create_item_definition.return_value = "weapon_sunblade"
    
    # Execute
    result = await create_weapon(
        mock_run_context, 
        name="Sunblade", 
        damage="1d10+2",
        range=0,
        description="A glowing sword",
        cost_gold=50
    )
    
    # Assert
    assert "item_id" in result
    assert result["item_id"] == "weapon_sunblade"
    assert "Use inventory_add_item" in result["message"]
    
    # Verify service call
    mock_run_context.deps.equipment_service.create_item_definition.assert_called_once()
    call_args = mock_run_context.deps.equipment_service.create_item_definition.call_args
    assert call_args[0][0] == "weapon"
    assert call_args[0][1]["name"] == "Sunblade"
    assert call_args[0][1]["damage"] == "1d10+2"
    assert call_args[1]["is_unique"] is False
    assert call_args[1]["can_buy"] is False

@pytest.mark.asyncio
@patch('back.tools.equipment_tools.asyncio')
async def test_create_armor_success(mock_asyncio, mock_run_context, mock_character):
    """Test create_armor tool success"""
    # Setup
    mock_run_context.deps.equipment_service.create_item_definition.return_value = "armor_dragon_scale"
    
    # Execute
    result = await create_armor(
        mock_run_context, 
        name="Dragon Scale", 
        protection=5,
        description="Tough armor",
        cost_gold=100
    )
    
    # Assert
    assert "item_id" in result
    assert result["item_id"] == "armor_dragon_scale"
    assert "Use inventory_add_item" in result["message"]
    
    # Verify service call
    mock_run_context.deps.equipment_service.create_item_definition.assert_called_once()
    call_args = mock_run_context.deps.equipment_service.create_item_definition.call_args
    assert call_args[0][0] == "armor"
    assert call_args[0][1]["protection"] == 5
    assert call_args[1]["is_unique"] is False
    assert call_args[1]["can_buy"] is False

@pytest.mark.asyncio
@patch('back.tools.equipment_tools.asyncio')
async def test_create_item_success(mock_asyncio, mock_run_context, mock_character):
    """Test specialized create_item tool success"""
    # Setup
    mock_run_context.deps.equipment_service.create_item_definition.return_value = "consumable_healing_potion"
    
    # Execute
    result = await create_item(
        mock_run_context, 
        name="Healing Potion", 
        category="consumable",
        description="Heals 2d4 HP",
        cost_gold=10
    )
    
    # Assert
    assert "item_id" in result
    assert result["item_id"] == "consumable_healing_potion"
    assert "Use inventory_add_item" in result["message"]
    
    # Verify service call
    mock_run_context.deps.equipment_service.create_item_definition.assert_called_once()
    call_args = mock_run_context.deps.equipment_service.create_item_definition.call_args
    assert call_args[0][0] == "consumable"
    assert call_args[1]["is_unique"] is False
    assert call_args[1]["can_buy"] is False

@pytest.mark.asyncio
async def test_create_item_invalid_category(mock_run_context):
    """Test create_item with invalid category (e.g. weapon)"""
    # Execute
    result = await create_item(mock_run_context, "Bad Sword", "weapon")
    
    # Assert
    assert "error" in result
    assert "Invalid category" in result["error"]
    assert "create_weapon" in result["error"]
