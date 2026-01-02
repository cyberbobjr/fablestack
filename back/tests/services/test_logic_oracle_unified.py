from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from back.models.api.game import (ChoiceData, LogicResult, PlayerInput,
                                  TimelineEvent)
from back.models.enums import TimelineEventType
from back.services.logic_oracle_service import LogicOracleService


@pytest.fixture
def mock_session_service():
    service = AsyncMock()
    # Mock character_service as MagicMock (Synchronous)
    service.character_service = MagicMock()
    service.settings_service.get_llm_config.return_value = MagicMock()
    service.load_game_state.return_value = None # Ensure no combat state
    return service

@pytest.fixture
def mock_oracle_agent():
    agent = MagicMock()
    agent.agent.run = AsyncMock()
    # Mock result structure
    mock_result = MagicMock()
    mock_result.output = "Oracle consequence narrative."
    mock_result.new_messages.return_value = []
    agent.agent.run.return_value = mock_result
    return agent

@pytest.mark.asyncio
async def test_resolve_choice_with_skill(mock_session_service, mock_oracle_agent):
    """Test that a choice with a skill check triggers the tool and oracle."""
    service = LogicOracleService()
    
    choice = ChoiceData(id="1", label="Jump", skill_check="athletics", difficulty="unfavorable")
    player_input = PlayerInput(input_mode="choice", text_content="Jump", choice_data=choice)
    
    # Setup mock result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.message = "Skill Check Passed"
    mock_result.roll = 15
    mock_result.target = 10
    mock_result.model_dump.return_value = {}
    mock_session_service.character_service.perform_skill_check.return_value = mock_result

    result = await service.resolve_turn("session_1", player_input, mock_session_service, mock_oracle_agent)
    
    # Verify character service called
    mock_session_service.character_service.perform_skill_check.assert_called_once()
    assert mock_session_service.character_service.perform_skill_check.call_args.kwargs['skill_name'] == "athletics"
    assert mock_session_service.character_service.perform_skill_check.call_args.kwargs['difficulty_name'] == "unfavorable"
    
    # Verify oracle called with context
    mock_oracle_agent.agent.run.assert_called_once()
    prompt_arg = mock_oracle_agent.agent.run.call_args.args[0]
    assert "PLAYER CHOICE: Jump" in prompt_arg
    assert "Skill Check 'athletics': SUCCESS" in prompt_arg
    
    # Verify logs
    skill_log = next((l for l in result.logs if l.type == TimelineEventType.SKILL_CHECK), None)
    assert skill_log is not None
    assert skill_log.content == "Skill Check Passed"

@pytest.mark.asyncio
async def test_resolve_choice_no_skill(mock_session_service, mock_oracle_agent):
    """Test that a choice without skill check skips the tool but calls oracle."""
    service = LogicOracleService()
    
    choice = ChoiceData(id="2", label="Look", skill_check=None)
    player_input = PlayerInput(input_mode="choice", text_content="Look", choice_data=choice)
    
    result = await service.resolve_turn("session_1", player_input, mock_session_service, mock_oracle_agent)
    
    # Verify tool NOT called
    mock_session_service.character_service.perform_skill_check.assert_not_called()
    
    # Verify oracle called
    mock_oracle_agent.agent.run.assert_called_once()
    prompt_arg = mock_oracle_agent.agent.run.call_args.args[0]
    assert "PLAYER CHOICE: Look" in prompt_arg
    assert "No Skill Check performed" in prompt_arg

@pytest.mark.asyncio
async def test_resolve_text_mundane(mock_session_service, mock_oracle_agent):
    """Test text input that TextAnalysisAgent deems mundane."""
    player_input = PlayerInput(input_mode="text", text_content="I look around")
    
    with patch("back.agents.text_analysis_agent.TextAnalysisAgent") as MockAgentClass:
        service = LogicOracleService()
        mock_text_inst = MockAgentClass.return_value
        # Important: LogicOracleService instantiates TextAnalysisAgent in __init__, 
        # but since we patched the class, it got a Mock.
        # However, MockAgentClass.return_value returns the SAME mock instance every time.
        # But wait, LogicOracleService calls TextAnalysisAgent(config).
        # So service.text_agent IS the return value of the call.
        # We need to make sure we configure THAT exact instance.
        
        # When we do: with patch(...) as M:
        # M is the MagicMock wrapping the class.
        # instance = M.return_value (default instance returned by constructor)
        # But wait, if __init__ is called, M() returns a NEW mock unless configured otherwise?
        # MagicMock by default returns a new child mock on call.
        # So service.text_agent will be M().
        # mock_text_inst = MockAgentClass.return_value IS that mock (if accessed as property).
        # Actually M.return_value is what M() returns.
        
        service.text_agent = mock_text_inst # Explicitly assign to be safe and sure.
        
        mock_text_inst.analyze = AsyncMock()
        mock_text_inst.analyze.return_value.skill_check = None
        mock_text_inst.analyze.return_value.difficulty = "normal"
        mock_text_inst.analyze.return_value.reasoning = "Mundane action."
        
        result = await service.resolve_turn("session_1", player_input, mock_session_service, mock_oracle_agent)
        
        # Verify Text Analysis
        mock_text_inst.analyze.assert_called_once()
        
        # Verify Tool NOT called
        mock_session_service.character_service.perform_skill_check.assert_not_called()
        
        # Verify Oracle called
        mock_oracle_agent.agent.run.assert_called_once()
        prompt_arg = mock_oracle_agent.agent.run.call_args.args[0]
        assert "PLAYER INPUT: I look around" in prompt_arg
        assert "No Skill Check performed" in prompt_arg

@pytest.mark.asyncio
async def test_resolve_text_exceptional(mock_session_service, mock_oracle_agent):
    """Test text input that implies a skill check."""
    player_input = PlayerInput(input_mode="text", text_content="I jump over the pit")
    
    with patch("back.agents.text_analysis_agent.TextAnalysisAgent") as MockAgentClass:
        service = LogicOracleService()
        mock_text_inst = MockAgentClass.return_value
        service.text_agent = mock_text_inst # Explicit assignment
        
        mock_text_inst.analyze = AsyncMock()
        mock_text_inst.analyze.return_value.skill_check = "athletics"
        mock_text_inst.analyze.return_value.difficulty = "favorable"
        mock_text_inst.analyze.return_value.reasoning = "Risky jump."
        
        # Mock skill check failure
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "You fell!"
        mock_result.roll = 2
        mock_result.target = 15
        mock_result.model_dump.return_value = {}
        mock_session_service.character_service.perform_skill_check.return_value = mock_result
        
        result = await service.resolve_turn("session_1", player_input, mock_session_service, mock_oracle_agent)
        
        # Verify Text Analysis
        mock_text_inst.analyze.assert_called_once()
        
        # Verify Tool CALLED
        mock_session_service.character_service.perform_skill_check.assert_called_once()
        assert mock_session_service.character_service.perform_skill_check.call_args.kwargs['skill_name'] == "athletics"
        assert mock_session_service.character_service.perform_skill_check.call_args.kwargs['difficulty_name'] == "favorable"
        
        # Verify Oracle called with failure
        mock_oracle_agent.agent.run.assert_called_once()
        prompt_arg = mock_oracle_agent.agent.run.call_args.args[0]
        assert "Skill Check 'athletics': FAILURE" in prompt_arg
        
        # Check Logs
        logs = result.logs
        # We look for "Generic Action Analysis" log for reasoning
        assert any(l.type == TimelineEventType.SYSTEM_LOG and "Generic Action Analysis" in str(l.content) for l in logs)
        assert any(l.type == TimelineEventType.SKILL_CHECK and "You fell" in str(l.content) for l in logs)
