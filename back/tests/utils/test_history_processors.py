from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import (ModelMessage, ModelRequest, ModelResponse,
                                  SystemPromptPart, TextPart, UserPromptPart)

from back.models.api.game import LLMConfig
from back.utils.history_processors import (count_tokens,
                                           estimate_history_tokens,
                                           summarize_old_messages)


@pytest.fixture
def mock_llm_config():
    with patch("back.utils.history_processors.get_llm_config") as mock:
        config = LLMConfig(
            api_endpoint="http://test",
            api_key="test",
            model="test-model",
            token_limit=100,
            keep_last_n_messages=2
        )
        mock.return_value = config
        yield config

def test_count_tokens():
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0

def test_estimate_history_tokens():
    msg1 = ModelRequest(parts=[UserPromptPart(content="Hello")])
    msg2 = ModelResponse(parts=[TextPart(content="World")])
    
    tokens = estimate_history_tokens([msg1, msg2])
    assert tokens > 0
    assert tokens == count_tokens("Hello") + count_tokens("World")

@pytest.mark.asyncio
async def test_summarize_old_messages_below_limit(mock_llm_config):
    # Create messages that are definitely below the 100 token limit
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Short message 1")]),
        ModelResponse(parts=[TextPart(content="Short message 2")])
    ]
    
    result = await summarize_old_messages(messages)
    assert result == messages
    assert len(result) == 2

@pytest.mark.asyncio
async def test_summarize_old_messages_above_limit(mock_llm_config):
    # Create messages that exceed the limit
    # Limit is 100. "Long message" repeated many times will exceed it.
    long_text = "Long message " * 20
    
    messages = [
        ModelRequest(parts=[SystemPromptPart(content="System Prompt")]), # 0
        ModelRequest(parts=[UserPromptPart(content="Old message 1")]),  # 1 (Summarize)
        ModelResponse(parts=[TextPart(content=long_text)]),             # 2 (Summarize - huge)
        ModelRequest(parts=[UserPromptPart(content="Recent 1")]),       # 3 (Keep)
        ModelResponse(parts=[TextPart(content="Recent 2")])              # 4 (Keep)
    ]
    # keep_last_n_messages = 2. So we keep index 3 and 4.
    # System prompt (index 0) should be kept.
    # Index 1 and 2 should be summarized.
    
    # Mock the Agent run
    with patch("back.utils.history_processors.Agent") as MockAgent:
        mock_agent_instance = MockAgent.return_value
        mock_run_result = MagicMock()
        mock_run_result.data = "Summarized content"
        mock_agent_instance.run = AsyncMock(return_value=mock_run_result)
        
        # Force token count high
        with patch("back.utils.history_processors.estimate_history_tokens", return_value=200):
            result = await summarize_old_messages(messages)
            
            # Expected structure: [SystemPrompt, SummaryMessage, Recent 1, Recent 2]
            assert len(result) == 4
        assert isinstance(result[0].parts[0], SystemPromptPart)
        assert result[0].parts[0].content == "System Prompt"
        
        assert isinstance(result[1].parts[0], TextPart)
        assert "**SYSTEM SUMMARY OF PAST EVENTS**" in result[1].parts[0].content
        assert "Summarized content" in result[1].parts[0].content
        
        assert result[2].parts[0].content == "Recent 1"
        assert result[3].parts[0].content == "Recent 2"

@pytest.mark.asyncio
async def test_summarize_old_messages_no_system_prompt(mock_llm_config):
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Old 1")]),
        ModelRequest(parts=[UserPromptPart(content="Old 2")]),
        ModelRequest(parts=[UserPromptPart(content="Recent 1")]),
        ModelRequest(parts=[UserPromptPart(content="Recent 2")])
    ]
    # keep 2. Summarize Old 1 and Old 2.
    
    with patch("back.utils.history_processors.Agent") as MockAgent:
        mock_agent_instance = MockAgent.return_value
        mock_run_result = MagicMock()
        mock_run_result.data = "Summary"
        mock_agent_instance.run = AsyncMock(return_value=mock_run_result)
        
        # Force token count high
        with patch("back.utils.history_processors.estimate_history_tokens", return_value=200):
            result = await summarize_old_messages(messages)
            
            # Expected: [Summary, Recent 1, Recent 2]
            assert len(result) == 3
            assert "**SYSTEM SUMMARY" in result[0].parts[0].content
