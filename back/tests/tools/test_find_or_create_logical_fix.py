
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import RunContext

from back.tools.equipment_tools import find_or_create_item_tool


@pytest.mark.asyncio
async def test_find_or_create_semantic_resolution():
    """Test that generic terms are resolved to catalog IDs via Semantic Search."""
    
    # 1. Setup Mock Context
    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = MagicMock()
    mock_ctx.deps.character_id = "char123"
    
    # Mock Equipment Service
    mock_eq_service = MagicMock()
    mock_ctx.deps.equipment_service = mock_eq_service
    
    # Mock Equipment Manager & Catalog
    mock_eq_manager = MagicMock()
    mock_eq_service.equipment_manager = mock_eq_manager
    mock_eq_manager.get_all_equipment.return_value = {
        "weapons": [
            {"id": "weapon_longsword", "name": "Longsword"},
            {"id": "weapon_dagger", "name": "Dagger"}
        ]
    }
    
    # Mock equipment_exists check
    mock_eq_service.equipment_exists.side_effect = lambda id: id in ["weapon_longsword", "weapon_dagger"]
    
    # Mock add_item and get_equipment_list for successful addition
    mock_eq_service.add_item = AsyncMock(return_value=MagicMock()) # updated character
    mock_eq_service.get_equipment_list.return_value = [{"id": "weapon_longsword", "qty": 1}]

    # 2. Patch the Agent (GenericAgent)
    # The tool imports build_simple_gm_agent locally
    with patch("back.agents.generic_agent.build_simple_gm_agent") as mock_build:
        mock_agent = AsyncMock()
        mock_build.return_value = mock_agent
        
        # Mock the LLM response to map "arme de base" -> "weapon_longsword"
        mock_result = MagicMock()
        mock_result.data = "weapon_longsword"
        mock_agent.run.return_value = mock_result
        
        # 3. Execute Tool
        result = await find_or_create_item_tool(
            mock_ctx, 
            name="arme de base", 
            acquisition_type="GIVE",
            description="A basic weapon for testing"
        )
        
        # 4. Assertions
        # Should have called Semantic Search
        mock_agent.run.assert_called_once()
        
        # Should have called add_item with "weapon_longsword"
        mock_eq_service.add_item.assert_called_with(
            mock_ctx.deps.character_service.get_character(),
            item_id="weapon_longsword",
            quantity=1
        )
        
        # Should return success message with the resolved ID
        assert "weapon_longsword" in str(result)
        assert "Added 1 x weapon_longsword" in result["message"]

@pytest.mark.asyncio
async def test_find_or_create_fallback_creation():
    """Test that truly unknown items fall back to creation."""
    
    # 1. Setup Mock Context
    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = MagicMock()
    mock_ctx.deps.character_id = "char123"
    
    # Mock Equipment Service
    mock_eq_service = MagicMock()
    mock_ctx.deps.equipment_service = mock_eq_service
    
    mock_eq_manager = MagicMock()
    mock_eq_service.equipment_manager = mock_eq_manager
    mock_eq_manager.get_all_equipment.return_value = {
        "weapons": [{"id": "weapon_longsword", "name": "Longsword"}]
    }
    
    # Mock create_item_definition (used by create_item tool)
    mock_eq_service.create_item_definition.return_value = "item_weird_thing_123"
    
    # Mock add_item
    mock_eq_service.add_item.return_value = MagicMock()
    mock_eq_service.get_equipment_list.return_value = []

    # Mock translation_agent access on deps
    mock_ctx.deps.translation_agent.translate_item.return_value = AsyncMock() 

    # 2. Patch the Agent
    with patch("back.agents.generic_agent.build_simple_gm_agent") as mock_build:
        mock_agent = AsyncMock()
        mock_build.return_value = mock_agent
        
        # Mock LLM saying "None" (no match found)
        mock_result = MagicMock()
        mock_result.data = "None"
        mock_agent.run.return_value = mock_result
        
        # Patch create_item tool also (since it's called by find_or_create)
        # Actually create_item is imported in the module, so we might need to patch it if we want to mock it.
        # But create_item logic is simple enough to run if we mock the service properly.
        # The tool calls `await create_item(...)`.
        
        # Let's run it. "Weird Thing" -> LLM says None -> fallback to create_item -> add_item
        
        # Note: create_item triggers background translation: asyncio.create_task(...)
        # We should patch asyncio.create_task to avoid errors in test
        with patch("asyncio.create_task"):
            await find_or_create_item_tool(
                mock_ctx, 
                name="Weird Thing", 
                acquisition_type="GIVE",
                description="A weird thing found in the void"
            )
        
        # 4. Assertions
        # Should have tried semantic search
        mock_agent.run.assert_called_once()
        
        # Should have called create_item_definition (via create_item)
        mock_eq_service.create_item_definition.assert_called()
        call_args = mock_eq_service.create_item_definition.call_args
        assert call_args[0][0] == "accessory" # defaults to accessory
        assert call_args[0][1]["name"] == "Weird Thing"
        
        # Should have called add_item with the NEW ID
        mock_eq_service.add_item.assert_called_with(
            mock_ctx.deps.character_service.get_character(),
            item_id="item_weird_thing_123",
            quantity=1
        )
