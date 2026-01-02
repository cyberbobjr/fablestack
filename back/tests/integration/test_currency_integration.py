from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import Character, Equipment
from back.services.game_session_service import GameSessionService
from back.tools.character_tools import character_add_currency


@pytest.fixture
def mock_session_service():
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    service.character_service = AsyncMock()
    return service

@pytest.fixture
def mock_run_context(mock_session_service):
    mock_model = MagicMock()
    usage = RunUsage(requests=1)
    return RunContext(deps=mock_session_service, retry=0, tool_name="test_tool", model=mock_model, usage=usage)

@pytest.mark.asyncio
async def test_currency_integration_flow(mock_run_context):
    """
    Integration-like test to verify the flow from tool -> service -> character update.
    """
    # Setup mock character returned by service
    mock_updated_character = MagicMock(spec=Character)
    mock_updated_character.equipment = MagicMock(spec=Equipment)
    mock_updated_character.equipment.gold = 10
    mock_updated_character.equipment.silver = 5
    mock_updated_character.equipment.copper = 50
    
    mock_run_context.deps.character_service.add_currency.return_value = mock_updated_character
    
    # Execute tool
    result = await character_add_currency(mock_run_context, gold=10, silver=5, copper=50)
    
    # Verify service call
    mock_run_context.deps.character_service.add_currency.assert_called_once_with(10, 5, 50)
    
    # Verify result structure
    assert result["message"] == "Added 10G 5S 50C"
    assert result["currency"]["gold"] == 10
    assert result["currency"]["silver"] == 5
    assert result["currency"]["copper"] == 50
    
    print("Currency integration test passed successfully.")
