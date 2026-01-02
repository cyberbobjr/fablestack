
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from back.models.api.game import (ChoiceData, LLMConfig, LogicResult,
                                  PlayerInput, TimelineEvent)
from back.models.enums import TimelineEventType
from back.services.agent_runner_service import AgentRunnerService


@pytest.fixture
def mock_logic_oracle():
    with patch('back.services.logic_oracle_service.LogicOracleService') as MockService:
        mock_instance = MockService.return_value
        yield mock_instance

@pytest.fixture
def mock_narrative_agent():
    # Patch where it is defined, as it is imported inside __init__
    with patch('back.agents.narrative_agent.NarrativeAgent') as MockAgent:
        mock_instance = MockAgent.return_value
        yield mock_instance

@pytest.fixture
def agent_runner(mock_logic_oracle, mock_narrative_agent):
    # Initializes services with mocks
    return AgentRunnerService()

@pytest.mark.asyncio
async def test_run_agent_stream_flow(agent_runner, mock_logic_oracle, mock_narrative_agent):
    # Setup Data
    session_id = uuid4()
    player_input = PlayerInput(text_content="Hello", input_mode="text")
    mock_session_service = MagicMock()
    mock_session_service.settings_service = None # Default no settings service
    mock_session_service.save_timeline_events = AsyncMock()
    mock_session_service.get_last_n_messages = AsyncMock(return_value=[])
    mock_session_service.load_history_llm = AsyncMock(return_value=[])
    mock_session_service.save_history_llm = AsyncMock()
    
    # 1. Setup LogicOracle response
    mock_logs = [
        TimelineEvent(type=TimelineEventType.SYSTEM_LOG, content="Log 1", icon="info", timestamp="2024-01-01T00:00:00Z"),
        TimelineEvent(type=TimelineEventType.SYSTEM_LOG, content="Log 2", icon="combat", timestamp="2024-01-01T00:00:01Z")
    ]
    mock_result = LogicResult(
        logs=mock_logs,
        narrative_context="The situation is tense."
    )
    mock_logic_oracle.resolve_turn = AsyncMock(return_value=mock_result)
    
    # 2. Setup NarrativeAgent response (Async Context Manager Generator)
    mock_stream_result = MagicMock()
    mock_stream_result.all_messages.return_value = []
    
    async def mock_stream_text_gen(delta=True):
        tokens = ["The", " goblin", " attacks!"]
        for t in tokens:
            yield t
            
    mock_stream_result.stream_text = mock_stream_text_gen
    
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_stream_result
    mock_context_manager.__aexit__.return_value = None
    
    # Configure the mock chain: narrative_agent.agent.run_stream -> context manager
    mock_narrative_agent.agent = MagicMock()
    mock_narrative_agent.agent.run_stream.return_value = mock_context_manager

    # 3. Setup ChoiceAgent response
    with patch('back.agents.choice_agent.ChoiceAgent') as MockChoiceAgent:
        mock_choice_instance = MagicMock()
        MockChoiceAgent.return_value = mock_choice_instance
        
        # Mock generate_choices to return ChoiceData objects (Pydantic models)
        mock_choice_instance.generate_choices = AsyncMock(return_value=[
            ChoiceData(id="1", label="Valid Choice", skill_check=None),
            ChoiceData(id="2", label="Other Choice", skill_check="Athletics")
        ])
        
        # Execute Flow
        events = []
        async for event_str in agent_runner.run_agent_stream(session_id, player_input, mock_session_service):
            assert event_str.startswith("data: ")
            data_str = event_str.replace("data: ", "").strip()
            # If line is "data: [DONE]" or similar, it might fail json load if not valid JSON
            # Our code yields {"type": "complete"} then finishes.
            try:
                data = json.loads(data_str)
                events.append(data)
            except json.JSONDecodeError:
                pass
            
        # Verify JSON serialization of choices
        choice_chunk = next((e for e in events if e.get('type') == 'choices'), None)
        assert choice_chunk is not None
        
        # Ensure 'content' is a list of DICTS, not ChoiceData objects
        assert isinstance(choice_chunk['content'], list)
        assert isinstance(choice_chunk['content'][0], dict)
        assert choice_chunk['content'][0]['label'] == "Valid Choice"
        assert choice_chunk['content'][1]['skill_check'] == "Athletics"

@pytest.mark.asyncio
async def test_run_agent_stream_error(agent_runner, mock_logic_oracle):
    # Setup Error
    session_id = uuid4()
    player_input = PlayerInput(text_content="Error Case", input_mode="text")
    mock_session_service = MagicMock()
    mock_session_service.settings_service = None
    mock_session_service.save_timeline_events = AsyncMock()
    mock_session_service.get_last_n_messages = AsyncMock(return_value=[])
    
    # Force error in Oracle
    mock_logic_oracle.resolve_turn = AsyncMock(side_effect=Exception("Something bad happened"))
    
    # Execute Flow
    events = []
    async for event_str in agent_runner.run_agent_stream(session_id, player_input, mock_session_service):
        data_str = event_str.replace("data: ", "").strip()
        data = json.loads(data_str)
        events.append(data)
        
    # Verify Error Handling
    error_events = [e for e in events if e.get('type') == 'error']
    assert len(error_events) == 1
    assert error_events[0]['error'] == "Something bad happened"
