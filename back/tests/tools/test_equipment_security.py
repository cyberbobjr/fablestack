from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import ModelMessage, RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.services.game_session_service import GameSessionService
from back.tools.equipment_tools import (create_armor, create_item,
                                        create_weapon, inventory_add_item,
                                        inventory_buy_item,
                                        list_available_equipment)

# --- Fixtures ---

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

# --- Tests ---

@pytest.mark.asyncio
async def test_can_buy_filtering(mock_run_context):
    """
    Test Case 1: `canBuy` Filtering
    Verify that list_available_equipment only shows items with can_buy=True.
    """
    # Setup mock data
    mock_equipment_manager = MagicMock()
    mock_equipment_manager.get_all_equipment.return_value = {
        "weapons": [
            {"id": "sword_standard", "name": "Standard Sword", "can_buy": True},
            {"id": "sword_unique", "name": "Quest Sword", "can_buy": False}
        ]
    }
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    
    # Execute
    result = await list_available_equipment(mock_run_context, category="weapons")
    
    # Assert
    items = result.get("items", {}).get("weapons", [])
    assert len(items) == 1
    assert items[0]["item_id"] == "sword_standard"
    # Ensure "Quest Sword" is NOT present
    assert not any(i["item_id"] == "sword_unique" for i in items)


@pytest.mark.asyncio
async def test_secure_item_creation(mock_run_context):
    """
    Test Case 2: Secure Item Creation
    Verify that newly created items default to can_buy=False.
    """
    service = mock_run_context.deps.equipment_service
    # Mock the return value of create_item_definition
    service.create_item_definition.return_value = "weapon_new_custom"

    # Execute
    await create_weapon(
        mock_run_context, 
        name="Custom Sword", 
        damage="1d8", 
        description="A custom blade"
    )
    
    # Assert create_item_definition was called with can_buy=False
    # Note: We need to check the call arguments
    args, kwargs = service.create_item_definition.call_args
    # signature: create_item_definition(category, item_data, is_unique, can_buy)
    
    # Check 'can_buy' arg (it might be in kwargs or args depending on position)
    if 'can_buy' in kwargs:
        assert kwargs['can_buy'] is False
    else:
        # It's the 4th positional argument if following signature: 
        # (category, item_data, is_unique, can_buy)
        # But wait, python mocks capture calls. create_item_definition def is:
        # def create_item_definition(self, category_name: str, item_data: Dict[str, Any], is_unique: bool = False, can_buy: bool = False)
        # We need to ensure it was passed as False.
        assert kwargs.get('can_buy') is False or (len(args) > 3 and args[3] is False)


@pytest.mark.asyncio
async def test_fuzzy_search_suggestion(mock_run_context):
    """
    Test Case 3: Fuzzy Search Suggestions (Hybrid Step 1)
    Verify that typo inputs return a "Did you mean..." suggestion via difflib.
    """
    # Setup catalog for fuzzy search
    mock_equipment_manager = MagicMock()
    mock_equipment_manager.get_all_equipment.return_value = {
        "items": [
            {"id": "item_rope", "name": "Rope", "can_buy": True}
        ]
    }
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    # Ensure equipment_exists returns False so it triggers search
    mock_run_context.deps.equipment_service.equipment_exists.return_value = False
    
    # Execute with typo
    result = await inventory_add_item(mock_run_context, "item_ropey")
    
    # Assert
    assert "error" in result
    assert "Did you mean: 'item_rope'" in result["error"]


@pytest.mark.asyncio
async def test_hybrid_search_llm_fallback(mock_run_context):
    """
    Test Case 3b: Hybrid Search LLM Fallback (Hybrid Step 2)
    Verify that if fuzzy search fails, the LLM agent is called for semantic matching.
    """
    # Setup catalog
    mock_equipment_manager = MagicMock()
    mock_equipment_manager.get_all_equipment.return_value = {
        "items": [
            {"id": "item_healing_potion", "name": "Healing Potion", "can_buy": True},
            {"id": "item_rope", "name": "Rope", "can_buy": True}
        ]
    }
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    mock_run_context.deps.equipment_service.equipment_exists.return_value = False

    # Mock difflib to return empty (simulating no close text match)
    with patch('difflib.get_close_matches', return_value=[]):
        # Mock GenericAgent to prevent real API call
        # We need to mock the SOURCE module because it is imported at runtime
        with patch('back.agents.generic_agent.build_simple_gm_agent') as mock_build_agent:
            mock_agent_instance = AsyncMock()
            # Mock the .run() result structure
            mock_result = MagicMock()
            mock_result.data = "item_healing_potion"
            mock_agent_instance.run.return_value = mock_result
            
            mock_build_agent.return_value = mock_agent_instance
            
            # Execute with semantic query ("healing juice" != "healing potion" distantly, but semantically close)
            result = await inventory_add_item(mock_run_context, "healing juice")
            
            # Assert
            assert "error" in result
            assert "Did you mean: 'item_healing_potion'" in result["error"]
            mock_agent_instance.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_buy_item_security(mock_run_context):
    """
    Test Case 4: Buy Item Security
    Verify that you cannot buy an item that has can_buy=False.
    """
    mock_equipment_manager = MagicMock()
    # Mock item returned by get_equipment_by_id
    mock_equipment_manager.get_equipment_by_id.return_value = {
        "id": "quest_item", 
        "name": "Quest Item", 
        "cost_gold": 10,
        "can_buy": False  # Crucial
    }
    mock_equipment_manager.get_all_equipment.return_value = {} # Needed for fuzzy search fallback inside buy
    mock_run_context.deps.equipment_service.equipment_manager = mock_equipment_manager
    
    # Execute
    result = await inventory_buy_item(mock_run_context, "quest_item")
    
    # Assert
    assert "error" in result
    assert "not available for purchase" in result["error"]
