from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back.models.api.game import ChoiceData, LLMConfig, PlayerInput
from back.models.api.skills import SkillCheckResult
from back.models.enums import TimelineEventType
from back.services.game_session_service import GameSessionService
from back.services.logic_oracle_service import LogicOracleService


@pytest.fixture
def mock_llm_config():
    return LLMConfig(
        api_key="sk-fake",
        model="gpt-4o-mini",
        api_endpoint="https://api.openai.com/v1",
        is_local=False
    )

@pytest.fixture
def mock_session_service():
    service = AsyncMock(spec=GameSessionService)
    # Mock load_current_scenario_content
    service.load_current_scenario_content.return_value = "You are in a dark room."

    # Mock character_service
    service.character_service = MagicMock()
    service.character_service.get_character.return_value = None # Default no character
    
    # Mock game_state.combat_state via load_game_state
    mock_game_state = MagicMock()
    mock_game_state.combat_state = None # Default inactive
    service.load_game_state = AsyncMock(return_value=mock_game_state)
    
    return service

@pytest.mark.asyncio
async def test_resolve_turn_choice_deterministic(mock_llm_config, mock_session_service):
    """
    Test that choice input bypasses the LLM and returns specific logs.
    """
    service = LogicOracleService()
    # Mock OracleAgent and its run method to be async
    mock_oracle_agent = MagicMock()
    # We need to mock agent.run which is awaited in _resolve_choice (step 2)
    mock_run_result = MagicMock()
    mock_run_result.new_messages.return_value = [] # No extra logs from oracle
    mock_run_result.output = "Item acquired."
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_run_result)
    
    # Mock skill_check tool call inside _resolve_choice
    with patch('back.tools.skill_tools.skill_check_with_character') as mock_tool:
        # Create a real Pydantic model response to avoid validation errors
        from back.models.api.skills import SkillCheckResult
        mock_result = SkillCheckResult(
            success=True,
            message="Success!",
            roll=15,
            target=10,
            difficulty_class=10,
            outcome="success", 
            skill_name="Athletics",
            character_id="char-1",
            degree="success",
            source_used="skill"
        )
        mock_tool.return_value = mock_result
        
        # FIX: Also mock on character_service because LogicOracleService calls it, not the tool directly
        mock_session_service.character_service.perform_skill_check.return_value = mock_result

        input_data = PlayerInput(
            input_mode="choice",
            text_content="",
            choice_data=ChoiceData(id="1", label="Jump", skill_check="Athletics")
        )

        result = await service.resolve_turn("session-123", input_data, mock_session_service, mock_oracle_agent)

        # Expect 1 log from deterministic check
        assert len(result.logs) == 1
        assert result.logs[0].type == TimelineEventType.SKILL_CHECK 
        assert result.logs[0].content == "Success!"
        assert result.logs[0].metadata is not None
        assert result.logs[0].metadata["success"] is True

        # Narrative context should combine both parts
        # Updated format: "Skill Check 'Athletics': SUCCESS (Roll: 15 vs 10)."
        assert "Skill Check 'Athletics': SUCCESS" in result.narrative_context
        # And also the oracle part
        assert "Item acquired." in result.narrative_context

@pytest.mark.asyncio
async def test_resolve_turn_choice_failure_triggers_oracle(mock_llm_config, mock_session_service):
    """
    Test that even if a skill check fails, the Oracle Agent is still invoked
    to check for negative consequences (e.g. traps, damage).
    """
    service = LogicOracleService()
    mock_oracle_agent = MagicMock()
    
    mock_run_result = MagicMock()
    mock_run_result.new_messages.return_value = [] 
    mock_run_result.output = "Trap triggered!"
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_run_result)
    
    with patch('back.tools.skill_tools.skill_check_with_character') as mock_tool:
        mock_result = MagicMock()
        mock_result.message = "Failure!"
        mock_result.success = False
        mock_result.roll = 5
        mock_result.target = 10
        mock_result.model_dump.return_value = {"success": False, "message": "Failure!"}
        mock_tool.return_value = mock_result
        
        # FIX: Also mock on character_service
        mock_session_service.character_service.perform_skill_check.return_value = mock_result
        
        input_data = PlayerInput(
            input_mode="choice", 
            text_content="", 
            choice_data=ChoiceData(id="2", label="Disarm Trap", skill_check="Thievery")
        )
        
        result = await service.resolve_turn("session-123", input_data, mock_session_service, mock_oracle_agent)
        
        # 1. Check we got the failure log from the tool
        assert result.logs[0].content == "Failure!"
        assert result.logs[0].type == "SKILL_CHECK"
        
        # 2. Check that Oracle Agent was STILL called
        mock_oracle_agent.agent.run.assert_called_once()
        
        # 3. Check combined narrative
        # Updated format: "Skill Check 'Thievery': FAILURE (Roll: 5 vs 10)."
        assert "Skill Check 'Thievery': FAILURE" in result.narrative_context
        assert "Trap triggered!" in result.narrative_context

@pytest.mark.asyncio
async def test_resolve_turn_text_llm(mock_llm_config, mock_session_service):
    """
    Test that text input calls the agent.
    We mock the agent's run method to avoid real LLM calls.
    """
    service = LogicOracleService()
    
    # Mock agent.run
    mock_result = MagicMock()
    mock_result.output = "The goblin dies."  # Use output, not data
    mock_result.new_messages.return_value = [] # No logs for this simple test
    
    mock_oracle_agent = MagicMock()
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_result)
    
    input_data = PlayerInput(input_mode="text", text_content="I attack!")
    
    # We must patch TextAnalysisAgent where it is imported FROM, because it is a local import in the method
    # and not present in the module namespace of logic_oracle_service
    with patch('back.agents.text_analysis_agent.TextAnalysisAgent') as MockTextAgentCls:
        mock_text_agent = MagicMock()
        # Mock analyze return value
        mock_analysis_result = MagicMock()
        mock_analysis_result.skill_check = None
        mock_text_agent.analyze = AsyncMock(return_value=mock_analysis_result)
        MockTextAgentCls.return_value = mock_text_agent
        
        # Inject existing instance
        service.text_agent = mock_text_agent
        
        # Inject existing instance
        service.text_agent = mock_text_agent
    
        result = await service.resolve_turn("session-123", input_data, mock_session_service, mock_oracle_agent)
        
        # If no skill check, narrative context purely comes from oracle output (which is mocked above as "The goblin dies.")
        # But wait, logic_oracle_service appends "No Skill Check performed." as skill_result_context if None?
        # Let's check logic_oracle_service: 
        # skill_result_context = "No Skill Check performed."
        # ...
        # if skill_result_context: narrative_context_parts.append(skill_result_context)
        # So "No Skill Check performed." might be included?
        # Actually in _execute_skill_check: if not skill_target: return True, None, []
        # So skill_result_context comes back as None. 
        # So "No Skill Check performed." is NOT added to narrative_context_parts in "resolve_turn"
        # BUT it IS used in "consequence_prompt".
        # So final narrative should just be oracle text.
        
        assert "The goblin dies." in result.narrative_context
        # Verify agent was called
        mock_oracle_agent.agent.run.assert_called_once()

@pytest.mark.asyncio
async def test_combat_log_duplication(mock_llm_config, mock_session_service):
    """
    Test that combat events generate a redundant SYSTEM_LOG entry.
    """
    service = LogicOracleService()
    
    # Mock result from generic agent run (simulate extract_logs behavior)
    # We need to manually invoke _extract_logs_from_result or simulate a run that returns tool calls.
    # Easiest is to unit test _tool_handlers or _extract_logs_from_result directly, 
    # but let's test via resolve_turn with mocked tool output.
    
    # Mock Oracle Agent to return a tool call that returns a combat event
    mock_oracle_agent = MagicMock()
    mock_run_result = MagicMock()
    
    from pydantic_ai.messages import (ModelResponse, ToolCallPart,
                                      ToolReturnPart)

    from back.models.enums import TimelineEventType

    # Simulate tool call to 'execute_attack_tool'
    # We don't actually call the tool if we mock the return message directly?
    # extract_logs iterates 'new_messages'.
    # 1. Tool Call
    msg_call = ModelResponse(parts=[ToolCallPart(tool_name="execute_attack_tool", args={"attacker_id": "p1", "target_id": "e1"}, tool_call_id="c1")])
    # 2. Tool Return (Mocked content)
    tool_content = {"message": "Hit outcome", "damage": 5}
    msg_return = ModelResponse(parts=[ToolReturnPart(tool_name="execute_attack_tool", content=tool_content, tool_call_id="c1")])
    
    mock_run_result.new_messages.return_value = [msg_call, msg_return]
    mock_run_result.output = "Narrative"
    mock_oracle_agent.agent.run = AsyncMock(return_value=mock_run_result)

    # We patch the handler for execute_attack_tool to ensure it returns COMBAT_ATTACK type without running real tool logic
    # Actually the tool handler is now resolved via get_tool_handler utility.
    # We can patch the instance's handler map or just rely on the existing one.
    # The existing one calls format_attack_log (from tool_handlers.py) which returns COMBAT_ATTACK.
    # So we don't need to patch the tool or handler if we pass the right dict content.
    
    input_data = PlayerInput(input_mode="text", text_content="Attack")
    
    # Needs text analysis mock
    with patch('back.agents.text_analysis_agent.TextAnalysisAgent') as MockTextAgent:
        mock_text = MagicMock()
        mock_text.analyze = AsyncMock(return_value=MagicMock(skill_check=None))
        MockTextAgent.return_value = mock_text
        
        # Inject existing instance
        service.text_agent = mock_text

        result = await service.resolve_turn("session-123", input_data, mock_session_service, mock_oracle_agent)

        # Expected Logs:
        # 1. Calling tool ... (SYSTEM_LOG) - generated by extract loop
        # 2. Tool returned ... (SYSTEM_LOG) - generated by extract loop
        # 3. COMBAT_ATTACK event (Main)
        # 4. SYSTEM_LOG event (Redundant)
        
        # Check for specific contents
        combat_logs = [l for l in result.logs if l.type == TimelineEventType.COMBAT_ATTACK]
        redundant_logs = [l for l in result.logs if l.type == TimelineEventType.SYSTEM_LOG and l.content == "Hit outcome"]
        
        assert len(combat_logs) == 1
        assert combat_logs[0].content == "Hit outcome"
        
        assert len(redundant_logs) == 1
        assert redundant_logs[0].content == "Hit outcome"
        assert redundant_logs[0].icon == "📝"

