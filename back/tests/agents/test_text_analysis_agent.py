
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from back.agents.text_analysis_agent import TextAnalysisAgent
from back.factories.agent_factory import AgentFactory
from back.models.api.game import TextIntentResult


@pytest.fixture
def mock_agent_factory():
    factory = MagicMock(spec=AgentFactory)
    return factory

@pytest.mark.asyncio
async def test_text_analysis_agent_initialization(mock_agent_factory):
    mock_agent = AsyncMock()
    mock_agent_factory.create_agent.return_value = mock_agent
    
    agent = TextAnalysisAgent(mock_agent_factory)
    
    # Verify Factory called with structured output and system prompt
    mock_agent_factory.create_agent.assert_called_once()
    _, kwargs = mock_agent_factory.create_agent.call_args
    assert kwargs["structured_output"] == TextIntentResult
    assert "system_prompt" in kwargs
    assert "expert Game Master Judge" in kwargs["system_prompt"]

@pytest.mark.asyncio
async def test_text_analysis_agent_analyze(mock_agent_factory):
    mock_langchain_agent = AsyncMock()
    mock_agent_factory.create_agent.return_value = mock_langchain_agent
    
    # Setup expected response
    expected_result = TextIntentResult(
        skill_check="athletics",
        difficulty="normal", 
        reasoning="Jumping over pit"
    )
    mock_langchain_agent.invoke.return_value = expected_result
    
    agent = TextAnalysisAgent(mock_agent_factory)
    
    result = await agent.analyze("I jump over the pit", None)
    
    assert result == expected_result
    
    # Verify invoke called with correct messages
    mock_langchain_agent.invoke.assert_called_once()
    messages = mock_langchain_agent.invoke.call_args.args[0]
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert "PLAYER ACTION: \"I jump over the pit\"" in messages[0].content

@pytest.mark.asyncio
async def test_text_analysis_agent_analyze_with_history(mock_agent_factory):
    mock_langchain_agent = AsyncMock()
    mock_agent_factory.create_agent.return_value = mock_langchain_agent
    mock_langchain_agent.invoke.return_value = TextIntentResult(skill_check=None, difficulty="normal", reasoning="none")
    
    agent = TextAnalysisAgent(mock_agent_factory)
    
    history = [HumanMessage(content="Previous")]
    await agent.analyze("New action", None, history_messages=history)
    
    # Verify history included
    messages = mock_langchain_agent.invoke.call_args.args[0]
    assert len(messages) == 2
    assert messages[0].content == "Previous"
    assert "PLAYER ACTION: \"New action\"" in messages[1].content
