from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import (AgentRunResultEvent, FunctionToolCallEvent,
                         FunctionToolResultEvent, PartDeltaEvent,
                         TextPartDelta)
from pydantic_ai.messages import TextPart

from back.models.domain.game_state import GameState
from back.models.enums import TimelineEventType
from back.services.agent_runner_service import AgentRunnerService
from back.services.game_session_service import GameSessionService


@pytest.mark.asyncio
async def test_run_agent_stream_narrative():
    # Setup
    service = AgentRunnerService()
    session_id = uuid4()
    user_message = "Hello"
    
    # Mock GameSessionService
    mock_session_service = AsyncMock(spec=GameSessionService)
    mock_session_service.load_game_state.return_value = GameState(
        session_mode="narrative",
        narrative_history_id="default",
        combat_history_id="default"
    )
    mock_session_service.load_history_llm.return_value = []
    # mock_session_service.build_narrative_system_prompt.return_value = "System Prompt" # Removed

    mock_session_service.save_history_llm.return_value = None

    mock_session_service.save_history.return_value = None
    mock_session_service.settings_service = MagicMock()
    mock_session_service.settings_service.get_preferences.return_value.language = "English"

    # Mock LogicOracleService
    # We need to mock it on the service instance because it is initialized in __init__
    mock_logic_oracle = AsyncMock()
    mock_logic_oracle.resolve_turn.return_value = MagicMock(
        logs=[],
        narrative_context="Context"
    )
    service.logic_oracle_service = mock_logic_oracle

    # Mock Global Container (for other dependencies if any)
    mock_container = MagicMock()
    mock_container.settings_service.get_preferences.return_value.language = "English"
    
        # Mock NarrativeAgent
    with patch("back.agents.narrative_agent.NarrativeAgent") as MockNarrativeAgent:
        mock_wrapper = MagicMock()
        MockNarrativeAgent.return_value = mock_wrapper
        
        # Mock inner agent
        mock_inner_agent = MagicMock()
        mock_wrapper.agent = mock_inner_agent
        
        service.narrative_agent = mock_wrapper

        # Mock run_stream result (StreamedRunResult)
        mock_result = MagicMock()
        mock_result.all_messages.return_value = [{"role": "user", "content": "foo"}, {"role": "model", "content": "bar"}]

        async def mock_stream_text(delta=True):
            yield "Hello"
            yield " World"
        
        mock_result.stream_text = mock_stream_text

        # Mock Async Context Manager returned by agent.run_stream
        class AsyncContextManagerMock:
            async def __aenter__(self):
                return mock_result
            async def __aexit__(self, exc_type, exc, tb):
                pass
        
        mock_inner_agent.run_stream.return_value = AsyncContextManagerMock()

        # Mock ChoiceAgent
        with patch("back.agents.choice_agent.ChoiceAgent") as MockChoiceAgent:
            mock_choice_agent = MagicMock()
            MockChoiceAgent.return_value = mock_choice_agent
            mock_choice_agent.generate_choices = AsyncMock(return_value=[])

            # Execute
            events = []
            async for event in service.run_agent_stream(session_id, user_message, mock_session_service):
                events.append(event)

        # Verify
        assert len(events) > 0
        # Check for types in events
        event_types = []
        for e in events:
            if "stream_start" in e: event_types.append("stream_start")
            elif "phase_change" in e: event_types.append("phase_change") 
            elif "token" in e: event_types.append("token")
            elif "complete" in e: event_types.append("complete")

        assert "stream_start" in event_types
        assert "phase_change" in event_types
        assert "token" in event_types
        assert "complete" in event_types
        
        # Verify persistence
        mock_session_service.save_timeline_events.assert_called()
        
        # Specific verification for CHOICE event
        # usages of save_timeline_events:
        # 1. USER_INPUT (optional)
        # 2. SYSTEM_LOG (optional)
        # 3. NARRATIVE
        # 4. CHOICE
        
        # We want to check if at least one call contained a CHOICE event
        found_choice_event = False
        for call in mock_session_service.save_timeline_events.call_args_list:
            args, _ = call
            events_list = args[0]
            for event in events_list:
                if event.type == TimelineEventType.CHOICE:
                    found_choice_event = True
                    assert isinstance(event.content, list)
                    break
        
        assert found_choice_event, "No TimelineEvent of type CHOICE was saved"

@pytest.mark.asyncio
async def test_run_agent_stream_combat():
    # Setup
    service = AgentRunnerService()
    session_id = uuid4()
    user_message = "Attack"
    
    # Mock GameSessionService
    mock_session_service = AsyncMock(spec=GameSessionService)
    mock_session_service.load_game_state.return_value = GameState(
        session_mode="combat",
        narrative_history_id="default",
        combat_history_id="default"
    )
    mock_session_service.load_history_llm.return_value = []
    # mock_session_service.build_combat_prompt.return_value = "Combat Prompt" # Removed

    mock_session_service.save_history_llm.return_value = None

    mock_session_service.save_history.return_value = None
    mock_session_service.settings_service = MagicMock()
    mock_session_service.settings_service.get_preferences.return_value.language = "English"

    # Mock LogicOracleService
    mock_logic_oracle = AsyncMock()
    mock_logic_oracle.resolve_turn.return_value = MagicMock(
        logs=[],
        narrative_context="Combat Context"
    )
    service.logic_oracle_service = mock_logic_oracle

    # Mock Global Container
    mock_container = MagicMock()
    mock_container.settings_service.get_preferences.return_value.language = "English"

    # Mock NarrativeAgent (AgentRunnerService uses NarrativeAgent for output even in combat?)
    # Yes, AgentRunnerService flow is: Oracle -> Narrative -> Choice
    # So it uses NarrativeAgent.
    
    mock_wrapper = MagicMock()
    mock_inner_agent = MagicMock()
    mock_wrapper.agent = mock_inner_agent
    service.narrative_agent = mock_wrapper
    
    # Mock run_stream result (StreamedRunResult)
    mock_result = MagicMock()
    mock_result.all_messages.return_value = []

    async def mock_stream_text(delta=True):
        yield "Hit"
    
    mock_result.stream_text = mock_stream_text

    # Mock Async Context Manager returned by agent.run_stream
    class AsyncContextManagerMock:
        async def __aenter__(self):
            return mock_result
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    mock_inner_agent.run_stream.return_value = AsyncContextManagerMock()

    # Mock ChoiceAgent
    with patch("back.agents.choice_agent.ChoiceAgent") as MockChoiceAgent:
        mock_choice_agent = MagicMock()
        MockChoiceAgent.return_value = mock_choice_agent
        mock_choice_agent.generate_choices = AsyncMock(return_value=[])

        # Execute
        events = []
        async for event in service.run_agent_stream(session_id, user_message, mock_session_service):
            events.append(event)

    # Verify
    assert len(events) > 0
    assert any("stream_start" in e for e in events)
    assert any("token" in e for e in events)
    assert any("complete" in e for e in events)
    
    # Verify persistence
    mock_session_service.save_timeline_events.assert_called()
