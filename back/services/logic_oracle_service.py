from typing import TYPE_CHECKING, AsyncGenerator


from back.factories.agent_factory import AgentFactory
from back.models.api.game import (LogicResult, PlayerInput, TimelineEvent)
from back.models.domain.game_state import GameState
from back.models.enums import TimelineEventType

if TYPE_CHECKING:
    from back.agents.oracle_agent import OracleAgent
    from back.agents.combat_agent import CombatAgent
    from back.services.game_session_service import GameSessionService

import uuid
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from back.agents.game_graph import build_game_graph
from back.models.enums import TimelineEventType

from back.utils.logger import log_error
# from back.utils.tool_handlers import get_tool_handler # No longer needed if ToolNode logic is inside graph


class LogicOracleService:
    """
    The Central Game Engine (Referee).

    Responsibilities:
    1. Analyzes Player Input (Text or Choice).
    2. Determines Game Rules & Mechanics.
    3. Executes Deterministic Logic Tools.
    4. Routing: Decisions -> OracleAgent vs CombatAgent.
    5. Returns a Fact-Based context for the Narrative Agent.
    """

    def __init__(self, agent_factory: AgentFactory):
        """
        ### __init__
        **Purpose:** Initializes the LogicOracleService with the LangGraph Application.
        
        Args:
            agent_factory: Factory for creating agents with injected configuration
        """
        # Graph is built lazily because it requires async db connection
        self.app = None
        self.agent_factory = agent_factory

    async def _ensure_app(self):
        if self.app is None:
            self.app = await build_game_graph()
        return self.app


    async def resolve_turn(
        self,
        session_id: str,
        player_input: PlayerInput,
        session_service: "GameSessionService",
        oracle_agent=None,
        history_messages=None
    ) -> LogicResult:
        """
        ### resolve_turn
        **Purpose:** Central entry point to process a player's turn using LangGraph.
        """
        try:
            # Prepare Input
            user_text = player_input.text_content
            if player_input.input_mode == "choice" and player_input.choice_data:
                user_text = player_input.choice_data.label
                
            input_message = HumanMessage(content=user_text, id=str(uuid.uuid4()))
            
            # LangGraph Config - Using dict as it's compatible with RunnableConfig
            config: RunnableConfig = {  # type: ignore
                "configurable": {
                    "thread_id": session_id,
                    "session_service": session_service,
                    "agent_factory": self.agent_factory
                }
            }
            
            # Ensure App is loaded
            app = await self._ensure_app()

            # Get Current State (to calculate delta)
            current_state = await app.aget_state(config)
            start_ui_len = 0
            if current_state and current_state.values:
                start_ui_len = len(current_state.values.get("ui_messages", []))
            
            # Invoke Graph
            # We explicitly update the 'messages' key in the state
            input_state = GameState(messages=[input_message], session_mode="narrative")
            final_state = await app.ainvoke(
                input_state,
                config=config
            )
            
            # Extract Output
            all_ui_messages = final_state.get("ui_messages", [])
            new_logs = all_ui_messages[start_ui_len:]
            
            # Extract Narrative Context (for immediate frontend display/audio)
            # Find the last Narrative event
            narrative_context = ""
            for log in reversed(new_logs):
                if log.type == TimelineEventType.NARRATIVE:
                    narrative_context = log.content
                    break
            
            return LogicResult(
                logs=new_logs,
                narrative_context=narrative_context
            )

        except Exception as e:
            log_error(f"Error in LogicOracleService.resolve_turn: {e}")
            import traceback
            traceback.print_exc()
            return LogicResult(
                logs=[TimelineEvent(type=TimelineEventType.SYSTEM_LOG, timestamp="", content=f"Error: {str(e)}", icon="⚠️")],
                narrative_context="The system encountered an error while processing your request."
            )

    async def resolve_turn_stream(
        self,
        session_id: str,
        player_input: PlayerInput,
        session_service: "GameSessionService",
        oracle_agent=None,
        history_messages=None
    ) -> AsyncGenerator[dict, None]:
        """
        ### resolve_turn_stream
        **Purpose:** Stream the logic resolution process using LangGraph streaming.
        
        Yields:
            dict: Stream events with type 'node', 'log', or 'narrative_context'
        """
        try:
            # Prepare Input
            user_text = player_input.text_content
            if player_input.input_mode == "choice" and player_input.choice_data:
                user_text = player_input.choice_data.label
                
            input_message = HumanMessage(content=user_text, id=str(uuid.uuid4()))
            
            # LangGraph Config
            config: RunnableConfig = {  # type: ignore
                "configurable": {
                    "thread_id": session_id,
                    "session_service": session_service,
                    "agent_factory": self.agent_factory
                }
            }
            
            # Ensure App is loaded
            app = await self._ensure_app()

            # Get Current State (to calculate delta)
            current_state = await app.aget_state(config)
            start_ui_len = 0
            if current_state and current_state.values:
                start_ui_len = len(current_state.values.get("ui_messages", []))
            
            # Stream Graph Execution with updates mode
            input_state = GameState(messages=[input_message], session_mode="narrative")
            
            # Use astream with stream_mode="updates" to get node-by-node updates
            async for chunk in app.astream(
                input_state,
                config=config,
                stream_mode="updates"
            ):
                # chunk is a dict with node_name as key and state update as value
                # Example: {'oracle_node': {'messages': [...], 'ui_messages': [...]}}
                for node_name, node_update in chunk.items():
                    # Yield node update
                    yield {
                        "type": "node",
                        "node_name": node_name
                    }
                    
                    # Check if there are new ui_messages (logs)
                    if "ui_messages" in node_update:
                        ui_messages = node_update["ui_messages"]
                        # Yield each new log
                        for log in ui_messages:
                            yield {
                                "type": "log",
                                "log": log
                            }
            
            # Get final state to extract narrative context
            final_state = await app.aget_state(config)
            all_ui_messages = final_state.values.get("ui_messages", [])
            new_logs = all_ui_messages[start_ui_len:]
            
            # Extract Narrative Context
            narrative_context = ""
            for log in reversed(new_logs):
                if log.type == TimelineEventType.NARRATIVE:
                    narrative_context = log.content
                    break
            
            # Yield narrative context
            if narrative_context:
                yield {
                    "type": "narrative_context",
                    "content": narrative_context
                }

        except Exception as e:
            log_error(f"Error in LogicOracleService.resolve_turn_stream: {e}")
            import traceback
            traceback.print_exc()
            # Yield error log
            yield {
                "type": "log",
                "log": TimelineEvent(
                    type=TimelineEventType.SYSTEM_LOG,
                    timestamp="",
                    content=f"Error: {str(e)}",
                    icon="⚠️"
                )
            }


