from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back.models.api.game import PlayerInput, TimelineEvent, TimelineEventType
from back.services.game_session_service import GameSessionService
from back.services.logic_oracle_service import LogicOracleService, LogicResult


@pytest.mark.asyncio
async def test_combat_declaration_flow():
    """
    Test full flow: 
    1. Oracle Declares Combat -> 2. Logic Service Initializes (mock CombatAgent call) -> 3. Logic Service Sets State
    """
    service = LogicOracleService()
    mock_session = AsyncMock(spec=GameSessionService)
    
    # Properly mock nested game_state property
    mock_game_state = MagicMock()
    mock_game_state.combat_state = None
    mock_session.load_game_state = AsyncMock(return_value=mock_game_state)
    mock_session.character_service = MagicMock()
    
    # Mock Oracle Agent Response (Decides to start combat)
    mock_oracle_agent = MagicMock()
    mock_oracle_result = MagicMock()
    mock_oracle_result.output = "Combat Declared."
    
    # Mock the tool call inside the Oracle's result
    # We need to simulate the message structure PydanticAI returns
    from pydantic_ai.messages import (ModelResponse, ToolCallPart,
                                      ToolReturnPart)

    # 1. Oracle CALLS the tool
    mock_call_msg = ModelResponse(parts=[ToolCallPart(tool_name="declare_combat_start_tool", args={"description": "Two goblins attack!"}, tool_call_id="call_1")])
    # 2. Tool RETURNS
    mock_return_msg = ModelResponse(parts=[ToolReturnPart(
        tool_name="declare_combat_start_tool", 
        content={"status": "combat_declared", "description": "Two goblins attack!"}, 
        tool_call_id="call_1"
    )])
    
    # LogicOracleService iterates specific messages or "new_messages" from the result
    mock_oracle_result.new_messages.return_value = [mock_call_msg, mock_return_msg] 
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_oracle_result)

    # Mock TextAnalysisAgent (so it doesn't try to run)
    with patch('back.agents.text_analysis_agent.TextAnalysisAgent') as MockTextAgent:
        mock_text = MagicMock()
        mock_text.analyze = AsyncMock(return_value=MagicMock(skill_check=None))
        MockTextAgent.return_value = mock_text

        # Mock CombatAgent (Verification Target)
        with patch('back.agents.combat_agent.CombatAgent') as MockCombatAgentCls:
            mock_combat_agent = MagicMock()
            mock_combat_result = MagicMock()
            mock_combat_result.output = "Enemies Spawned: Goblin A, Goblin B."
            mock_combat_result.new_messages.return_value = [] # Assume start_combat_tool log handled elsewhere or skipped here
            mock_combat_agent.run = AsyncMock(return_value=mock_combat_result)
            MockCombatAgentCls.return_value = mock_combat_agent
            
            # Inject existing instance
            service.text_agent = mock_text
            
            # Inject the mock into the ALREADY instantiated service
            service.combat_agent = mock_combat_agent

            # EXECUTE
            input_data = PlayerInput(input_mode="text", text_content="Attack them!")
            result = await service.resolve_turn("sess-1", input_data, mock_session, mock_oracle_agent)

            # ASSERTIONS
            
            # 1. Verify CombatAgent was instantiated and RUN
            # MockCombatAgentCls.assert_called() # Skipped because service already instantiated
            mock_combat_agent.run.assert_called()
            
            # Check prompt payload to combat agent contained description
            call_args = mock_combat_agent.run.call_args
            assert "Two goblins attack!" in call_args[0][0] # prompt string
            
            # 2. Verify Output contains Combat Agent's output
            assert "[COMBAT INITIALIZED]: Enemies Spawned: Goblin A, Goblin B." in result.narrative_context

