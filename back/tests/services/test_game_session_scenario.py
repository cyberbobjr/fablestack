
from unittest.mock import AsyncMock, patch

import pytest

from back.services.game_session_service import GameSessionService
from back.utils.exceptions import ScenarioNotFoundError


@pytest.mark.asyncio
async def test_load_current_scenario_content_success():
    """Test loading scenario content successfully."""
    service = GameSessionService("test-session")
    service.scenario_id = "test_scenario.md"
    
    with patch('back.services.scenario_service.ScenarioService.get_scenario_details', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "Scenario Content"
        
        content = await service.load_current_scenario_content()
        assert content == "Scenario Content"

@pytest.mark.asyncio
async def test_load_current_scenario_content_not_found():
    """Test that ScenarioNotFoundError is raised when file is missing."""
    service = GameSessionService("test-session")
    service.scenario_id = "missing_scenario.md"
    
    with patch('back.services.scenario_service.ScenarioService.get_scenario_details', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(ScenarioNotFoundError) as excinfo:
            await service.load_current_scenario_content()
        
        assert "Scenario missing_scenario.md not found" in str(excinfo.value)
