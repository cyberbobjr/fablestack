from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from back.tools.equipment_tools import find_or_create_item_tool


@pytest.mark.asyncio
async def test_find_or_create_description_bug():
    """
    Reproduce the bug where created items always get a hardcoded description.
    """
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
    # Empty catalog so it forces creation
    mock_eq_manager.get_all_equipment.return_value = {"weapons": [], "armor": [], "accessories": [], "consumables": []}
    
    # Mock create_item_definition to return a new ID
    mock_eq_service.create_item_definition.return_value = "item_new_custom_id"
    
    # Mock add_item
    mock_eq_service.add_item.return_value = MagicMock()
    mock_eq_service.get_equipment_list.return_value = []

    # 2. Run the tool with a custom description
    item_name = "Mysterious Artifact"
    custom_desc = "A strange glowing artifact from the old world."
    result = await find_or_create_item_tool(
        mock_ctx, 
        name=item_name, 
        acquisition_type='GIVE',
        description=custom_desc
    )

    # 3. Assert creation was called with the CUSTOM description
    # Verify create_item_definition was called
    mock_eq_service.create_item_definition.assert_called()
    call_args = mock_eq_service.create_item_definition.call_args
    
    # Check the 'description' field in the item_data dict (2nd argument)
    item_data = call_args[0][1]
    
    # Expected success: custom description
    assert item_data["description"] == custom_desc, \
        f"Expected '{custom_desc}', got '{item_data.get('description')}'"
