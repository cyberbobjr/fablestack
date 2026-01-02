from unittest.mock import AsyncMock, MagicMock

import pytest

from back.models.api.game import (PlayerInput, TextIntentResult,
                                  TimelineEventType)
from back.services.logic_oracle_service import LogicOracleService


@pytest.mark.asyncio
async def test_resolve_turn_handles_null_skill_target_string():
    """
    Reproduce the issue where the LLM returns "null" as a string for skill_check.
    The service should sanitize this and NOT perform a skill check.
    """
    service = LogicOracleService()
    
    # Mock dependencies
    mock_session_service = AsyncMock()
    
    # Properly mock nested game_state property
    mock_game_state = MagicMock()
    # Mock combat_state to prevent errors if tools access it
    mock_combat_state = MagicMock()
    mock_combat_state.turn_order = ["combatant_1", "combatant_2"] # Real list to avoid coroutine/mock errors
    mock_combat_state.current_turn_combatant_id = "combatant_1"
    mock_combat_state.participants = []
    mock_combat_state.is_active = False # Default inactive
    
    mock_game_state.combat_state = None 
    
    mock_session_service.load_game_state.return_value = mock_game_state
    mock_oracle_agent = MagicMock()
    
    # Configure mock_run_result
    mock_run_result = MagicMock()
    mock_run_result.output = "Narrative result"
    mock_run_result.new_messages.return_value = [] # Valid synchronous return
    
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_run_result)

    # Mock TextAnalysisAgent to return "null" string
    with pytest.MonkeyPatch.context() as mp:
        mock_text_agent = AsyncMock()
        # Simulate LLM returning the string "null"
        mock_text_agent.analyze.return_value = TextIntentResult(
            skill_check="null", 
            reasoning="Context implies no check."
        )
        
        mp.setattr("back.agents.text_analysis_agent.TextAnalysisAgent", MagicMock(return_value=mock_text_agent))
        
        # Inject mock into service instance
        service.text_agent = mock_text_agent

        input_data = PlayerInput(input_mode="text", text_content="I look around")
        
        result = await service.resolve_turn(
            session_id="test_session",
            player_input=input_data,
            session_service=mock_session_service,
            oracle_agent=mock_oracle_agent
        )

        # Assert no error occurred
        error_logs = [l for l in result.logs if "Error:" in str(l.content)]
        assert len(error_logs) == 0, f"Service returned errors: {error_logs}"

        # Assertions
        # 1. No SKILL_CHECK log should be present
        skill_logs = [l for l in result.logs if l.type == TimelineEventType.SKILL_CHECK]
        assert len(skill_logs) == 0, f"Found unexpected skill check logs: {skill_logs}"
        
        # 2. System log should mention the analysis reasoning
        system_logs = [l for l in result.logs if l.type == TimelineEventType.SYSTEM_LOG]
        assert any("Context implies no check" in str(l.content) for l in system_logs)

@pytest.mark.asyncio
async def test_resolve_turn_handles_real_null_skill_target():
    """
    Verify normal behavior when skill_check is None (JSON null).
    """
    service = LogicOracleService()
    mock_session_service = AsyncMock()
    mock_oracle_agent = MagicMock()
    
    # Configure mock_run_result
    mock_run_result = MagicMock()
    mock_run_result.output = "Narrative result"
    mock_run_result.new_messages.return_value = []
    
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_run_result)

    with pytest.MonkeyPatch.context() as mp:
        mock_text_agent = AsyncMock()
        mock_text_agent.analyze.return_value = TextIntentResult(
            skill_check=None, 
            reasoning="No check needed."
        )
        mp.setattr("back.agents.text_analysis_agent.TextAnalysisAgent", MagicMock(return_value=mock_text_agent))
        
        # Inject mock into service instance
        service.text_agent = mock_text_agent

        input_data = PlayerInput(input_mode="text", text_content="Walking")
        
        result = await service.resolve_turn(
            session_id="test_session",
            player_input=input_data,
            session_service=mock_session_service,
            oracle_agent=mock_oracle_agent
        )
        
        # Assert no error occurred
        error_logs = [l for l in result.logs if "Error:" in str(l.content)]
        assert len(error_logs) == 0, f"Service returned errors: {error_logs}"

        skill_logs = [l for l in result.logs if l.type == TimelineEventType.SKILL_CHECK]
        assert len(skill_logs) == 0
