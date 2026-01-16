from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pydantic_ai import AgentRunResult
from pydantic_ai.messages import ModelMessage
from pydantic_evals import set_eval_attribute

from back.config import get_llm_config
from back.models.api.game import (LogicResult, PlayerInput, TextIntentResult,
                                  TimelineEvent)
from back.models.enums import TimelineEventType

if TYPE_CHECKING:
    from back.agents.oracle_agent import OracleAgent
    from back.agents.combat_agent import CombatAgent
    from back.services.game_session_service import GameSessionService

import uuid
from langchain_core.messages import HumanMessage
from back.agents.game_graph import build_game_graph
from back.models.enums import TimelineEventType

from back.utils.logger import log_error, logger
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

    def __init__(self):
        """
        ### __init__
        **Purpose:** Initializes the LogicOracleService with the LangGraph Application.
        """
        # Graph is built lazily because it requires async db connection
        self.app = None

    async def _ensure_app(self):
        if self.app is None:
            self.app = await build_game_graph()
        return self.app


    async def resolve_turn(
        self,
        session_id: str,
        player_input: PlayerInput,
        session_service: "GameSessionService",
        oracle_agent: "OracleAgent",  # Kept for compatibility but unused
        history_messages: List[ModelMessage] = [] # Kept for compatibility but unused
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
            
            # LangGraph Config
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "session_service": session_service
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
            final_state = await app.ainvoke(
                {"messages": [input_message], "session_mode": "narrative"}, # triggers add_messages reducer
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


