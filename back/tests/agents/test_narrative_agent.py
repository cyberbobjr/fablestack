"""
Tests for NarrativeAgent.
"""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from pydantic_ai import RunContext

from back.agents.narrative_agent import NarrativeAgent
from back.models.api.game import LLMConfig
from back.models.domain.payloads import CombatIntentPayload, ScenarioEndPayload
from back.services.game_session_service import GameSessionService

# Global mock for the tool implementation to allow verification
mock_tool_impl = MagicMock()

# Wrapper function that mimics the signature of the real tool
def search_enemy_archetype_tool(ctx: RunContext[GameSessionService], query: str) -> dict:
    mock_tool_impl(query) # Call the mock for verification
    return {
        "results": [{"id": "goblin_scout", "name": "Goblin Scout", "description": "A small goblin."}],
        "count": 1,
        "message": f"Found 1 archetypes matching '{query}'."
    }




class TestNarrativeAgent:
    """Test cases for NarrativeAgent."""

    def test_init_valid_config(self):
        """Test initialization with valid LLM config."""
        llm_config = LLMConfig(
            api_endpoint="https://api.example.com",
            api_key="test_key",
            model="test-model"
        )
        agent = NarrativeAgent(llm_config)
        assert agent.agent is not None
        assert agent.agent.output_type == str

    def test_init_missing_api_endpoint(self):
        """Test that LLMConfig raises ValidationError with missing api_endpoint."""
        with pytest.raises(ValidationError):
            LLMConfig(  # type: ignore
                api_key="test_key",
                model="test-model"
            )

    def test_init_missing_api_key(self):
        """Test that LLMConfig raises ValidationError with missing api_key."""
        with pytest.raises(ValidationError):
            LLMConfig(  # type: ignore
                api_endpoint="https://api.example.com",
                model="test-model"
            )

    def test_init_missing_model(self):
        """Test that LLMConfig raises ValidationError with missing model."""
        with pytest.raises(ValidationError):
            LLMConfig(  # type: ignore
                api_endpoint="https://api.example.com",
                api_key="test_key"
            )

    def test_init_empty_strings(self):
        """Test initialization with empty strings."""
        llm_config = LLMConfig(
            api_endpoint="",
            api_key="",
            model=""
        )
        agent = NarrativeAgent(llm_config)
        assert agent.agent is not None
