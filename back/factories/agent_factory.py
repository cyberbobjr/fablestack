from typing import Callable, List, Optional, Type

from pydantic import BaseModel

from back.agents.langchain_agent import LangChainRPGAgent
from back.interfaces.rpg_agent import RPGAgent


class AgentFactory:
    """
    Factory class to create instances of RPGAgent.
    Decouples the client code from the specific agent implementation.
    Uses dependency injection for configuration.
    """

    def __init__(self, model_config: dict):
        """
        Initialize the factory with LLM configuration.

        Args:
            model_config: LLM configuration (from get_llm_config())
        """
        self._model_config = model_config

    def create_agent(
        self,
        tools: List[Callable] = [], 
        structured_output: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None
    ) -> RPGAgent:
        """
        Creates and returns an RPGAgent instance.

        Args:
            tools: Optional list of tools to provide to the agent.
            structured_output: Optional Pydantic model for structured output definition.
            system_prompt: Optional system prompt to define the agent's behavior.

        Returns:
            An instance implementing the RPGAgent interface.
        """
        # Currently defaults to LangChainRPGAgent, but could switch based on config or logic
        return LangChainRPGAgent(
            model_config=self._model_config,
            tools=tools,
            structured_output=structured_output,
            system_prompt=system_prompt or ""
        )
