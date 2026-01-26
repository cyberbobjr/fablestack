from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

from back.config import LLMConfig, get_llm_config
from back.interfaces.rpg_agent import RPGAgent
from back.utils.tool_utils import get_cleaned_tool_definitions

T = TypeVar('T', bound=BaseModel)


class LangChainRPGAgent(RPGAgent[T]):
    """
    Concrete implementation of RPGAgent using LangChain's create_agent.
    """
    
    def __init__(
        self, 
        model_config: Optional[LLMConfig] = None, 
        tools: List[Callable] = [], 
        structured_output: Optional[Type[T]] = None,
        system_prompt: str = "You are a helpful assistant"
    ):
        if model_config is None:
            model_config = get_llm_config()
        
        api_key = SecretStr(model_config.api_key) if model_config.api_key else None
            
        self.model = ChatOpenAI(
            model=model_config.model, 
            api_key=api_key,
            base_url=model_config.api_endpoint
        )
        
        self.tools = tools
        self.structured_output = structured_output
        self.system_prompt = system_prompt or "You are a helpful assistant"
        
        tool_defs = get_cleaned_tool_definitions(self.tools) if self.tools else []
        
        interrupts = []
        if self.tools and not self.structured_output:
            interrupts = ["tools"]
            
        self.agent = create_agent(
            model=self.model,
            tools=tool_defs or [],
            system_prompt=self.system_prompt,
            response_format=self.structured_output,
            interrupt_before=interrupts
        )

    async def invoke(self, input_data: List[BaseMessage]) -> Union[BaseMessage, T]:
        """
        Executes the agent logic.
        """
        inputs: Dict[str, Any] = {"messages": input_data}

        result = await self.agent.ainvoke(inputs)  # type: ignore
        
        if self.structured_output:
            if "structured_response" in result:
                return result["structured_response"]
            return AIMessage(content="Error: No structured response found in state.")

        if "messages" in result and result["messages"]:
            return result["messages"][-1]
            
        return AIMessage(content="Error: No response from agent.")
