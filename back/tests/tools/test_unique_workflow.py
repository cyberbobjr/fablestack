import os
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.config import get_data_dir
from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.equipment_tools import create_weapon, inventory_add_item


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
    """Create a mock GameSessionService with real EquipmentService but mocked data service"""
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    
    # Mock specialized services
    service.character_service = MagicMock()
    service.character_service.get_character.return_value = mock_character
    service.character_service.add_currency = AsyncMock()
    
    # Use REAL EquipmentService with mocked data service
    from back.models.domain.equipment_manager import EquipmentManager
    from back.services.character_data_service import CharacterDataService
    from back.services.equipment_service import EquipmentService
    
    mock_data_service = MagicMock(spec=CharacterDataService)
    # Important: The Code uses `await data_service.save_character(...)`
    # So save_character MUST be an AsyncMock
    mock_data_service.save_character = AsyncMock(return_value=mock_character)
    
    mock_equipment_manager = EquipmentManager()
    # Ensure no file IO happens implicitly
    mock_equipment_manager._load_equipment_data = MagicMock(return_value={'weapons': {}, 'armor': {}, 'items': {}})
    mock_equipment_manager._save_unique_equipment_data = MagicMock()
    mock_equipment_manager._save_standard_equipment_entry = MagicMock()
    # We pass the mock_data_service here
    equipment_service = EquipmentService(mock_data_service, mock_equipment_manager)
    
    # Mock EquipmentManager to avoid reading real files during unit tests
    # BUT we want to test persistence logic, so we might want to use a temporary directory
    # For this test, we will mock the save methods to verify they are called correctly
    equipment_service.equipment_manager._save_unique_equipment_data = MagicMock()
    equipment_service.equipment_manager._save_standard_equipment_entry = MagicMock()
    
    # Mock load to return empty or specific data
    equipment_service.equipment_manager._load_equipment_data = MagicMock(return_value={
        'weapons': {}, 'armor': {}, 'items': {}
    })
    # Reset lazy load
    equipment_service.equipment_manager._equipment_data = None
    
    # Configure async methods
    # equipment_service.add_item = AsyncMock(return_value=mock_character) # REMOVED to allow testing partial integration
    
    service.equipment_service = equipment_service
    service.data_service = mock_data_service
    service.races_service = MagicMock()
    
    # Add translation_agent mock
    from back.agents.translation_agent import TranslationAgent
    service.translation_agent = MagicMock(spec=TranslationAgent)
    
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
async def test_create_unique_weapon_workflow(mock_run_context):
    """Test creating a unique weapon and adding it to inventory"""
    # 1. Create Unique Weapon
    result = await create_weapon(
        mock_run_context,
        name="Unique Blade",
        damage="1d8",
        is_unique=True
    )
    
    assert "message" in result
    assert "ID:" in result["message"]
    item_id = result["item_id"]
    
    # Verify it called save_unique
    mock_run_context.deps.equipment_service.equipment_manager._save_unique_equipment_data.assert_called_once()
    mock_run_context.deps.equipment_service.equipment_manager._save_standard_equipment_entry.assert_not_called()
    
    # Verify inventory is NOT modified yet (we need to check the character mock)
    # The tool does not modify inventory, so no need to check character save yet
    
    # 2. Add to Inventory
    # We need to ensure the manager "has" the item in memory for add_item to work
    # Since we mocked load, we need to manually inject it into the manager's cache
    manager = mock_run_context.deps.equipment_service.equipment_manager
    # The create_item call should have updated the in-memory cache
    assert "Unique Blade" in manager.equipment_data['weapons']
    
    add_result = await inventory_add_item(mock_run_context, item_id, qty=1)
    
    assert "message" in add_result
    assert f"Added 1 x {item_id}" in add_result["message"]
    
    # Verify character was saved (meaning item was added)
    mock_run_context.deps.equipment_service.data_service.save_character.assert_called()

@pytest.mark.asyncio
async def test_create_standard_weapon_workflow(mock_run_context):
    """Test creating a standard weapon (default behavior)"""
    # 1. Create Standard Weapon
    result = await create_weapon(
        mock_run_context,
        name="Standard Sword",
        damage="1d6",
        is_unique=False
    )
    
    item_id = result["item_id"]
    
    # Verify it called save_standard
    mock_run_context.deps.equipment_service.equipment_manager._save_standard_equipment_entry.assert_called_once()
    mock_run_context.deps.equipment_service.equipment_manager._save_unique_equipment_data.assert_not_called()
