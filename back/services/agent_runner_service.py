import json
import traceback
from typing import TYPE_CHECKING, AsyncGenerator
from uuid import UUID

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

from back.config import get_llm_config
from back.factories.agent_factory import AgentFactory
from back.models.api.game import PlayerInput, TimelineEvent
from back.utils.logger import log_error


class AgentRunnerService:
    """
    Orchestrates the Game Loop: Input -> Logic -> Logs -> Narrative -> Choices.

    This service is responsible for managing the flow of a game turn, handling user input,
    executing game logic via the LogicOracleService, generating narrative content via
    the NarrativeAgent, and presenting choices to the player via the ChoiceAgent.
    """

    def __init__(self, agent_factory: AgentFactory) -> None:
        """
        Initializes the AgentRunnerService.

        Sets up the necessary services and agents (LogicOracleService, NarrativeAgent, OracleAgent).
        ChoiceAgent is initialized lazily to avoid circular dependencies.
        
        Args:
            agent_factory: Factory for creating agents with injected configuration
        """
        # Initialize services/agents that are stateless or config-based
        from back.agents.narrative_agent import NarrativeAgent
        from back.agents.oracle_agent import OracleAgent
        from back.services.logic_oracle_service import LogicOracleService
        llm_config = get_llm_config()
        self.logic_oracle_service = LogicOracleService(agent_factory)
        self.narrative_agent = NarrativeAgent(llm_config)
        self.oracle_agent = OracleAgent(llm_config)
        # self.choice_agent = ChoiceAgent(llm_config) # Initialize later or lazily if needed

    async def run_agent_stream(
        self,
        session_id: UUID,
        player_input: PlayerInput,
        session_service: "GameSessionService"
    ) -> AsyncGenerator[str, None]:
        """
        Executes the "Logic-First" pipeline for a game turn.

        This method processes the player's input, executes game logic, generates a narrative
        response, and produces new choices for the player. It streams the results back to the
        client as Server-Sent Events (SSE) compatible data chunks.

        Flow:
        1. Persist User Input (if visible).
        2. Oracle Execution (Logic Analysis & Tools).
        3. Stream System Logs.
        4. Augmented Prompt Projection.
        5. Narrative Agent Streaming.
        6. Choice Generation.

        Args:
            session_id (UUID): The unique identifier of the game session.
            player_input (PlayerInput): The input provided by the player (text or choice).
            session_service (GameSessionService): The service for managing game session state.

        Yields:
            str: JSON-formatted strings prefixed with "data: " representing stream events
                 (e.g., stream_start, system_log, phase_change, token, choices, complete, error).
        """
        try:
            # 0. Persist User Input (if not hidden)
            from datetime import datetime, timezone

            from back.models.enums import TimelineEventType

            timestamp_now = datetime.now(timezone.utc).isoformat()

            player_action_text: str = ""
            is_hidden: bool = False

            if isinstance(player_input, str):
                player_action_text = player_input
                is_hidden = False
            else:
                player_action_text = player_input.text_content if player_input.input_mode == "text" else f"{player_input.choice_data.label if player_input.choice_data else 'Unknown choice'}"
                is_hidden = player_input.hidden

            # 2. Handle Text Input (LLM Oracle)
            if not is_hidden:
                user_event = TimelineEvent(
                    type=TimelineEventType.USER_INPUT,
                    content=player_action_text,
                    timestamp=timestamp_now,
                    icon="👤"
                )
                await session_service.save_timeline_events([user_event])

            # 1. Oracle Execution with Streaming
            yield f"data: {json.dumps({'type': 'stream_start', 'phase': 'logic'})}\n\n"
    
            # Get history for Oracle
            oracle_history = await session_service.get_last_n_messages("narrative", 10)

            # Stream the logic resolution using LangGraph streaming
            all_logs = []
            narrative_context = ""
            
            async for logic_chunk in self.logic_oracle_service.resolve_turn_stream(
                str(session_id),
                player_input,
                session_service,
                self.oracle_agent,
                history_messages=oracle_history
            ):
                # Stream node updates (e.g., oracle_node, combat_node, etc.)
                if logic_chunk["type"] == "node":
                    node_event = {
                        "type": "node_update",
                        "node_name": logic_chunk["node_name"],
                        "phase": "logic"
                    }
                    yield f"data: {json.dumps(node_event)}\n\n"
                
                # Stream logs as they are generated
                elif logic_chunk["type"] == "log":
                    log = logic_chunk["log"]
                    # Ensure timestamp if missing
                    if not log.timestamp:
                        log.timestamp = datetime.now(timezone.utc).isoformat()

                    # Build event data with specific TimelineEvent type
                    event_data = {
                        "type": log.type,
                        "content": log.content,
                        "icon": log.icon
                    }

                    # Add metadata if present
                    if log.metadata:
                        event_data["metadata"] = log.metadata

                    yield f"data: {json.dumps(event_data)}\n\n"
                    all_logs.append(log)
                
                # Capture narrative context
                elif logic_chunk["type"] == "narrative_context":
                    narrative_context = logic_chunk["content"]

            # Persist Logs
            if all_logs:
                await session_service.save_timeline_events(all_logs)

            # 3. Narrative Generation
            yield f"data: {json.dumps({'type': 'phase_change', 'phase': 'narrative'})}\n\n"

            augmented_prompt = (
                f"[PLAYER ACTION]: {player_action_text}\n\n"
                f"[SYSTEM REALITY]: {narrative_context}\n\n\n"
                f"INSTRUCTION: Based on PLAYER ACTION and the SYSTEM REALITY above, "
                f"describe the scene and outcome to the player in an immersive style. "
                f"Do not change the facts established in reality."
            )

            # Load message history before running the narrative agent
            message_history = await session_service.load_history_llm("narrative")

            generated_text = ""
            async with self.narrative_agent.agent.run_stream(
                user_prompt=augmented_prompt,
                deps=session_service,
                message_history=message_history
            ) as result:
                async for token in result.stream_text(delta=True):
                    token_event = {
                        "type": "token",
                        "content": token
                    }
                    yield f"data: {json.dumps(token_event)}\n\n"
                    generated_text += token

                # Persist LLM History (compact)
                await session_service.save_history_llm("narrative", result.all_messages())

            # Persist Narrative
            narrative_event = TimelineEvent(
                type=TimelineEventType.NARRATIVE,
                content=generated_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                icon="📜"
            )
            await session_service.save_timeline_events([narrative_event])

            # 4. Choices
            context_for_choices = narrative_context

            # Add generated narrative
            context_for_choices += f"\n\n[NARRATIVE]: {generated_text}\n\n"

            yield f"data: {json.dumps({'type': 'phase_change', 'phase': 'choices'})}\n\n"

            # Import ChoiceAgent at runtime to avoid circular dependencies
            from back.agents.choice_agent import ChoiceAgent
            choice_agent = ChoiceAgent(get_llm_config())

            # Generate choices based on narrative context
            user_language = "English"
            if session_service.settings_service:
                prefs = session_service.settings_service.get_preferences()
                if prefs:
                    user_language = prefs.language

            choices = await choice_agent.generate_choices(context_for_choices, session_service, user_language)

            # Persist Choices
            choices_event = TimelineEvent(
                type=TimelineEventType.CHOICE,
                content=[c.model_dump() for c in choices],
                timestamp=datetime.now(timezone.utc).isoformat(),
                icon="🤔"
            )
            await session_service.save_timeline_events([choices_event])

            yield f"data: {json.dumps({'type': 'choices', 'content': [c.model_dump() for c in choices]})}\n\n"

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            log_error(f"Error in run_agent_stream: {e}")
            error_msg = {
                "type": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            yield f"data: {json.dumps(error_msg)}\n\n"
