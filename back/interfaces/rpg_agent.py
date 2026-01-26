from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar, Union

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class RPGAgent(ABC, Generic[T]):
    """
    Abstract Base Class for an RPG Agent.
    """

    @abstractmethod
    async def invoke(self, input_data: List[BaseMessage]) -> Union[BaseMessage, T]:
        """
        Executes the agent with the given input.
        
        Args:
            input_data: The list of messages to process.
            
        Returns:
            The output of the agent (AIMessage or structured object of type T).
        """
        pass
