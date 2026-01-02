
from unittest.mock import patch

import pytest

from back.services.scenario_service import ScenarioService


@pytest.mark.asyncio
async def test_list_scenarios_ignores_sessions(tmp_path):
    """Test that list_scenarios does NOT return sessions."""
    # Create scenarios
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    (scenarios_dir / "scenario1.md").write_text("# Scenario 1")

    # Create sessions
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "session1").mkdir()
    
    with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
        result = await ScenarioService.list_scenarios()
        
        assert len(result.scenarios) == 1
        assert result.scenarios[0].name == "scenario1.md"
