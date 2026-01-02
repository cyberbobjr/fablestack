from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from back.tools.combat_tools import start_combat_tool


@pytest.mark.asyncio
async def test_start_combat_tool_minimal_args():
    """
    Verify that start_combat_tool accepts minimal enemy argument (just name).
    And correctly assigns defaults.
    """
    # Mock Context
    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = MagicMock()
    
    # Mock Game State
    mock_game_state = MagicMock()
    mock_game_state.combat_state = None
    mock_ctx.deps.load_game_state = AsyncMock(return_value=mock_game_state)
    mock_ctx.deps.update_game_state = AsyncMock()
    
    # Mock Character Service to return None (no player for this specific test, avoids mocking Character model)
    mock_char_service = MagicMock()
    mock_char_service.get_character = MagicMock(return_value=None)
    mock_ctx.deps.character_service = mock_char_service
    
    # Input with MINIMAL args (just name)
    enemies_input = [{"name": "Test Goblin"}]
    
    # Execute
    result = await start_combat_tool(mock_ctx, enemies=enemies_input, description="Test Fight")
    
    # Assert
    assert "error" not in result
    assert "Combat started!" in result["message"]
    assert len(result["participants"]) >= 1 # At least the enemy (player might be missing in this mock if not set up, but tool returns summary)
    
    # Check that defaults were applied in the service call
    # We can inspect the combat_state argument passed to update_game_state
    updated_state = mock_ctx.deps.update_game_state.call_args[0][0]
    assert updated_state.combat_state is not None
    assert len(updated_state.combat_state.participants) == 1
    enemy = updated_state.combat_state.participants[0]
    assert enemy.name == "Test Goblin"
    assert enemy.current_hit_points == 10 # Default from tool logic
    assert enemy.armor_class == 10 # Default
