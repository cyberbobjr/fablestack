from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back.agents.choice_agent import ChoiceAgent
from back.models.api.game import LLMConfig

# from back.services.game_session_service import GameSessionService

@pytest.mark.asyncio
async def test_choice_agent_instantiation():
    """Verify ChoiceAgent can be instantiated without import errors."""
    config = LLMConfig(
        model="deepseek-chat",
        api_endpoint="https://api.deepseek.com",
        api_key="fake_key"
    )
    with patch("back.agents.choice_agent.StatsManager") as MockStatsManager, \
         patch("back.agents.choice_agent.UnifiedSkillsManager") as MockSkillsManager:
        
        MockStatsManager.return_value.get_all_stats_names.return_value = ["Strength", "Dexterity"]
        MockSkillsManager.return_value.get_all_skill_ids.return_value = ["Athletics", "Stealth"]

        try:
            agent = ChoiceAgent(config)
            assert agent is not None
            assert agent.agent is not None
        except Exception as e:
            pytest.fail(f"Failed to instantiate ChoiceAgent: {e}")

@pytest.mark.asyncio
async def test_choice_agent_generation_mock():
    """Verify generate_choices calls the agent and returns list."""
    config = LLMConfig(
        model="deepseek-chat", 
        api_endpoint="https://api.deepseek.com",
        api_key="fake_key"
    )
    
    # Mock the internal pydantic_ai Agent
    with patch("back.agents.choice_agent.Agent") as MockAgentClass, \
         patch("back.agents.choice_agent.StatsManager") as MockStatsManager, \
         patch("back.agents.choice_agent.UnifiedSkillsManager") as MockSkillsManager:
        
        mock_agent_instance = MagicMock()
        MockAgentClass.return_value = mock_agent_instance
        
        MockStatsManager.return_value.get_all_stats_names.return_value = ["Strength", "Dexterity"]
        MockSkillsManager.return_value.get_all_skill_ids.return_value = ["Athletics", "Stealth"]
        
        # Mock the run result
        mock_result = MagicMock()
        # MOCK THE OUTPUT ATTRIBUTE, NOT DATA
        mock_result.output.choices = [
            {"id": "1", "label": "Test choice"} 
        ]
        # Ensure result.data does NOT exist to verify we use output
        del mock_result.data 
        
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        agent = ChoiceAgent(config)
        
        # Mock Deps
        deps = MagicMock()
        
        choices = await agent.generate_choices("Context", deps)
        
        assert len(choices) == 1
        assert choices[0]["id"] == "1"
