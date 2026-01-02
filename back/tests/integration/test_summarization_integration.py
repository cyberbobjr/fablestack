import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import (ModelRequest, ModelResponse, TextPart,
                                  UserPromptPart)

from back.agents.narrative_agent import NarrativeAgent
from back.models.api.game import LLMConfig
from back.models.domain.game_state import GameState
from back.services.game_session_service import (HISTORY_NARRATIVE,
                                                GameSessionService)


@pytest.fixture
def mock_llm_config():
    with patch("back.utils.history_processors.get_llm_config") as mock:
        # Set very low limit to trigger summarization immediately
        config = LLMConfig(
            api_endpoint="http://test",
            api_key="test",
            model="openai:test-model",
            token_limit=10, # Very low limit
            keep_last_n_messages=1
        )
        mock.return_value = config
        yield config

@pytest.fixture
def mock_deps(tmp_path):
    # Mock GameSessionService dependencies
    with patch("back.services.game_session_service.get_data_dir", return_value=str(tmp_path)):
        session_id = "test-session-integration"
        (tmp_path / "sessions" / session_id).mkdir(parents=True)
        (tmp_path / "sessions" / session_id / "character.txt").write_text("char1")
        (tmp_path / "sessions" / session_id / "scenario.txt").write_text("scen1")
        (tmp_path / "sessions" / session_id / "game_state.json").write_text("{}")
        
        with patch("back.services.game_session_service.GameSessionService._initialize_services"):
            service = GameSessionService(session_id)
            # service.build_narrative_system_prompt = AsyncMock(return_value="System Prompt") # Removed

            service.character_service = MagicMock()
            service.character_service.get_character.return_value = None
            service.load_current_scenario_content = AsyncMock(return_value="Scenario Content")
            

            service.load_history_llm = AsyncMock(return_value=[])
            service.save_history = AsyncMock()
            service.save_history_llm = AsyncMock()
            
            return service

@pytest.mark.asyncio
async def test_narrative_summarization_integration(mock_deps, mock_llm_config):
    """
    Test that NarrativeAgent correctly integrates with summarization logic
    when history exceeds token limits.
    """
    # Initialize NarrativeAgent
    agent = NarrativeAgent(mock_llm_config)
    
    # We must mock the underlying agent.run because we don't want real LLM calls,
    # BUT we want the history_processor to run.
    # pydantic_ai.Agent.run executes:
    # 1. prepare_messages (runs history_processors)
    # 2. model.request
    
    # So we should mock the MODEL, not the agent.run.
    
    with patch("pydantic_ai.models.openai.OpenAIChatModel.request") as mock_request:
        # Mock responses
        # We need to handle multiple calls if summarization invokes an agent too.
        # However, summarize_old_messages uses a SEPARATE agent instance, 
        # which will also try to call a model.
        
        # We can detect which call is which by checking the messages passed?
        # Or we can just return a generic response.
        
        mock_msg = ModelResponse(parts=[TextPart(content="Response Text")])
        mock_request.return_value = mock_msg
        
        # To test summarization, we need to inject a LONG history into deps.load_history_llm
        # The agent.run will call deps.load_history_llm (via our custom logic? No, pydantic_ai manages history)
        # Wait, our Agent usage in AgentRunnerService manages loading/saving history.
        # NarrativeAgent.run just takes a prompt and history?
        
        # Let's check NarrativeAgent.run signature:
        # async def run(self, *args, **kwargs): return await self.agent.run(*args, **kwargs)
        
        # We invoke it usually as: agent.run(user_prompt, message_history=history, deps=deps)
        
        # So we construct a long history
        long_history = [
            ModelRequest(parts=[UserPromptPart(content="Msg " + str(i))]) for i in range(20)
        ]
        
        # Mock token counting to report high usage
        with patch("back.utils.history_processors.estimate_history_tokens", return_value=100) as mock_estimate:
            
            # Mock the summarization agent's run method to avoid recursion or second model call complexity
            # summarize_old_messages imports Agent inside the function? No, it uses a global or imported Agent.
            # actually it creates `Agent(model, ...)` inside `summarize_old_messages` usually.
            
            # Let's inspect `back.utils.history_processors` logic if possible, 
            # or just mock the entire summarizer function if we want to test correct integration of the *result* 
            # rather than the *process* of summarization.
            
            # The test name implies "Integration", so we want to ensure the processor IS CALLED and IT MODIFIES history.
            
            # The test name implies "Integration", so we want to ensure the processor IS CALLED and IT MODIFIES history.
            
            with patch("back.agents.narrative_agent.summarize_old_messages") as mock_summarize:
                # Initialize NarrativeAgent AFTER patching
                agent = NarrativeAgent(mock_llm_config)

                # Mock the summarizer to return a summarized history
                summary_msg = ModelRequest(parts=[UserPromptPart(content="Summary of old messages")])
                recent_msg = long_history[-1]
                mock_summarize.return_value = [summary_msg, recent_msg]
                
                # Execute Agent Run
                user_prompt = "New User Action"
                
                # We do NOT pass message_history to run() if we want the agent to use the one we prepared?
                # pydantic_ai Agent.run takes `message_history`.
                
                result = await agent.agent.run(user_prompt, deps=mock_deps, message_history=long_history)
                
                # Verify summarizer was called
                mock_summarize.assert_called_once()
                
                # Verify that the model received the SUMMARIZED history, not the full one
                # mock_request is called with (messages, ...)
                # generic syntax: call_args[0][0] are messages
                
                calls = mock_request.call_args_list
                assert len(calls) == 1
                sent_messages = calls[0].args[0]
                
                # Validation:
                # 1. System Prompt (injected)
                # 2. Summary (from mock_summarize)
                # 3. Recent Msg (from mock_summarize)
                # 4. New User Prompt
                
                # We expect "Summary of old messages" to be present
                has_summary = any("Summary of old messages" in str(m) for m in sent_messages)
                assert has_summary, "Model should have received the summary"
                
                # We expect the full list of 20 messages to NOT be present (at least not all of them)
                # The logic replaced them.
                assert len(sent_messages) < 20 + 2 # +2 for system/user
