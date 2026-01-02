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

from back.agents.combat_agent import CombatAgent
from back.agents.text_analysis_agent import TextAnalysisAgent
from back.models.domain.races_manager import RacesManager
from back.utils.logger import log_error
from back.utils.tool_handlers import get_tool_handler


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
        **Purpose:** Initializes the LogicOracleService without dependencies.
        """
        # NOOP: Tool handlers are now centralized in utils/tool_handlers.py
        # Text: Analyze intent dynamically

        # Use settings to configure model if needed, or default
        self.text_agent = TextAnalysisAgent(get_llm_config())
        self.combat_agent = CombatAgent(get_llm_config())
            
        pass


    async def resolve_turn(
        self,
        session_id: str,
        player_input: PlayerInput,
        session_service: "GameSessionService",
        oracle_agent: "OracleAgent",  # Injected at method level
        history_messages: List[ModelMessage] = []
    ) -> LogicResult:
        """
        ### resolve_turn
        **Purpose:** Central entry point to process a player's turn.
        UNIFIED FLOW:
        1. Check Combat State -> Route to CombatAgent if active.
        2. Else -> Route to OracleAgent (Narrative/Exploration).
        """
        try:
            logs = []
            narrative_context_parts = []
            
            # --- PHASE 1: INPUT ANALYSIS (Exploration & Combat) ---
            skill_target, difficulty, input_desc, analysis_logs = await self._analyze_input(
                player_input, session_service, history_messages
            )
            logs.extend(analysis_logs)

            # --- PHASE 2: EXECUTION (Skill Check) ---
            skill_success, skill_result_context, skill_logs = self._execute_skill_check(
                skill_target, difficulty, session_service
            )
            logs.extend(skill_logs)
            if skill_result_context:
                narrative_context_parts.append(skill_result_context)

            # --- CHECK COMBAT STATE ---
            is_combat_active = False
            
            # Load Game State properly
            game_state = await session_service.load_game_state()
            
            if game_state and game_state.combat_state and game_state.combat_state.is_active:
                is_combat_active = True
                
            if is_combat_active:
                # Pass skill context to combat agent so it knows what happened
                return await self._resolve_combat_turn(
                    player_input, 
                    session_service, 
                    history_messages,
                    game_state.combat_state,
                    skill_result_context=skill_result_context,
                    pre_logs=logs # Pass existing logs (analysis/skills)
                )

            # --- PHASE 3: ORACLE CONSEQUENCES ---
            oracle_logs, oracle_text = await self._determine_consequences(
                input_desc, skill_result_context, skill_target, 
                session_service, oracle_agent, history_messages
            )
            logs.extend(oracle_logs)
            narrative_context_parts.append(oracle_text)
            
            # --- CHECK FOR COMBAT DECLARATION ---
            # If Oracle declared combat, we might want to immediately perform the initialization step using CombatAgent
            # to generate the enemies list right now, so the next turn is ready.
            for log in oracle_logs:
                if log.metadata and log.metadata.get("status") == "combat_declared":
                     description = log.metadata.get("description")
                     if description:
                         # IMMEDIATE HANDOFF: Call CombatAgent to Initialize
                         init_logs, init_text = await self._initialize_combat_with_agent(
                             description, session_service, history_messages
                         )
                         logs.extend(init_logs)
                         narrative_context_parts.append(init_text)

            final_narrative = " ".join(narrative_context_parts)
            
            return LogicResult(
                logs=logs,
                narrative_context=final_narrative
            )

        except Exception as e:
            log_error(f"Error in LogicOracleService.resolve_turn: {e}")
            import traceback
            traceback.print_exc()
            return LogicResult(
                logs=[TimelineEvent(type=TimelineEventType.SYSTEM_LOG, timestamp="", content=f"Error: {str(e)}", icon="⚠️")],
                narrative_context="The system encountered an error while processing your request."
            )

    async def _resolve_combat_turn(
        self,
        player_input: PlayerInput,
        session_service: "GameSessionService",
        history_messages: List[ModelMessage],
        combat_state: Any, # Type hinted as Any to avoid circular import or use CombatState if available
        skill_result_context: Optional[str] = None,
        pre_logs: List[TimelineEvent] = []
    ) -> LogicResult:
        """
        Handles a turn when Combat is Active. Delegates to CombatAgent.
        """
        
        # Prepare Combat Context
        combat_summary = "Combat Active."
        if combat_state:
             # Basic summary for the prompt
             current_turn_id = combat_state.current_turn_combatant_id
             combat_summary = f"Round {combat_state.round_number}. Turn: {current_turn_id}."
        
        traits_context = ""
        try:
             if session_service.character_service:
                 character = session_service.character_service.get_character()
                 if character:
                     traits_context = self._get_traits_context(character)
        except Exception as exc:
             log_error(
                 "Failed to build traits context in _resolve_combat_turn",
                 {"error": str(exc)}
             )

        user_text = player_input.text_content if player_input.input_mode == "text" else player_input.choice_data.label
        prompt = (
            f"PLAYER INPUT: {user_text}\n"
            f"COMBAT STATUS: {combat_summary}\n"
            f"{traits_context}\n"
        )
        if skill_result_context:
             # CRITICAL: Only apply skill check context if it is the PLAYER'S turn.
             # Otherwise, the Agent might apply the player's skill bonus to an Enemy's attack.
             is_player_turn = False
             if combat_state and combat_state.current_turn_combatant_id:
                 current_fighter = next((p for p in combat_state.participants if p.id == combat_state.current_turn_combatant_id), None)
                 if current_fighter and current_fighter.type == "player":
                     is_player_turn = True
             
             if is_player_turn:
                 prompt += f"PRE-ACTION SKILL CHECK: {skill_result_context}\n"
             else:
                 # Optional: Add a note that player tried to act out of turn?
                 # For now, we suppress the skill check context so it doesn't confuse the AI.
                 pass
             
        prompt += (
            f"TASK: Resolve the turn. If it is player's turn, execute their action. If NPC turn, execute AI action.\n" 
        )
        
        result = await self.combat_agent.run(prompt, deps=session_service, message_history=history_messages)
        
        logs = pre_logs + self._extract_logs_from_result(result)
        text_output = getattr(result, "output", str(result))
        
        return LogicResult(
            logs=logs,
            narrative_context=f"[COMBAT RESOLUTION]: {text_output}"
        )

    async def _initialize_combat_with_agent(
        self,
        description: str,
        session_service: "GameSessionService",
        history_messages: List[ModelMessage]
    ) -> Tuple[List[TimelineEvent], str]:
        """
        Calls CombatAgent to run `start_combat_tool` based on a description.
        """
        
        prompt = (
            f"COMBAT DECLARED: {description}\n"
            f"TASK: Initialize the combat IMMEDIATELY.\n"
            f"1. ANALYZE the description to identify all enemies (names, approximate numbers).\n"
            f"2. CONSTRUCT the `enemies` list explicitly. Example: `[{{'name': 'Wolf', 'archetype': 'wolf'}}, ...]`\n"
            f"3. CALL `start_combat_tool(enemies=..., description=...)`.\n"
            f"CRITICAL: You MUST provide the `enemies` argument. Do NOT leave it empty.\n"
        )
        
        # We run this as a "one-off" or as part of the stream.
        result = await self.combat_agent.run(prompt, deps=session_service, message_history=history_messages)
        
        logs = self._extract_logs_from_result(result)
        text_output = getattr(result, "output", str(result))
        
        return logs, f"[COMBAT INITIALIZED]: {text_output}"

    # ... [Keep existing _analyze_input, _execute_skill_check, _determine_consequences, etc.] ...
    async def _analyze_input(
        self,
        player_input: PlayerInput,
        session_service: "GameSessionService",
        history_messages: List[ModelMessage]
    ) -> Tuple[Optional[str], str, str, List[TimelineEvent]]:
        """
        Analyzes the player input to determine intent and potential skill checks.
        Returns: (skill_target, difficulty, input_desc, logs)
        """
        skill_target: Optional[str] = None
        difficulty: str = "normal"
        input_desc: str = ""
        logs: List[TimelineEvent] = []

        if player_input.input_mode == "choice" and player_input.choice_data:
            # Choice: Trust the pre-defined skill check
            skill_target = player_input.choice_data.skill_check
            difficulty = player_input.choice_data.difficulty
            input_desc = f"PLAYER CHOICE: {player_input.choice_data.label}"
        else:
            text_content = player_input.text_content
            analysis_result : TextIntentResult = await self.text_agent.analyze(text_content, session_service, history_messages)
            
            skill_target = analysis_result.skill_check
            difficulty = analysis_result.difficulty
            input_desc = f"PLAYER INPUT: {text_content}"
            if skill_target:
                logs.append(TimelineEvent(
                    type=TimelineEventType.SYSTEM_LOG,
                    timestamp="",
                    content=f"Skill checked needed : {skill_target} ({difficulty}) Generic Action Analysis: {analysis_result.reasoning}",
                    icon="🧠"
                ))
            
            # Defensive coding: If LLM returns string "null", treat as None
            if skill_target and str(skill_target).lower() == "null":
                skill_target = None
        
        return skill_target, difficulty, input_desc, logs

    async def _determine_consequences(
        self,
        input_desc: str,
        skill_result_context: Optional[str],
        skill_target: Optional[str],
        session_service: "GameSessionService",
        oracle_agent: "OracleAgent",
        history_messages: List[ModelMessage]
    ) -> Tuple[List[TimelineEvent], str]:
        """
        Uses the OracleAgent to determine the narrative and mechanical consequences.
        """
        skill_context_str = skill_result_context if skill_result_context else "No Skill Check performed."
        
        # Get Character Context
        character_context = ""
        try:
             # Defensive get
             if session_service.character_service:
                character = session_service.character_service.get_character()
                if character:
                    character_context = character.build_narrative_prompt_block()
        except Exception as e:
            log_error(f"Failed to get character context: {e}")

        # Construct a prompt that describes the input + skill result
        traits_context = ""
        try:
            if session_service.character_service:
                character = session_service.character_service.get_character()
                if character:
                    traits_context = self._get_traits_context(character)
        except Exception as e:
            log_error(f"Failed to retrieve character traits context: {e}")

        consequence_prompt = (
            f"{input_desc}\n"
            f"CONTEXT: The player performed this action.\n"
            f"STATUS: {skill_context_str}\n"
            f"CHARACTER STATUS:\n{character_context}\n"
            f"{traits_context}\n"
        )

        if skill_target:
            consequence_prompt += f"DO NOT perform new skill checks for '{skill_target}' if one was just done.\n"

        consequence_prompt += (
            f"TASK: Determine the narrative consequences and implied mechanics (e.g. 'Take item', 'Apply Damage').\n"
            f"EXECUTE necessary tools if implied.\n"
            f"REMINDER: If this action starts a fight, you MUST call 'declare_combat_start_tool'.\n" # Updated prompt
            f"CRITICAL INSTRUCTION: Provide ONLY a factual summary of what happens. DO NOT write a story or narrative. Use bullet points or concise sentences.\n"
            f"OUTPUT: A brief factual summary."
        )
        
        result = await oracle_agent.agent.run(consequence_prompt, deps=session_service, message_history=history_messages)
        
        # Extract any logs (e.g. Item Added, Damage Taken)
        oracle_logs = self._extract_logs_from_result(result)
        
        # Get agent output
        oracle_text = getattr(result, "output", str(result))
        
        return oracle_logs, oracle_text
        
    def _execute_skill_check(
        self,
        skill_target: Optional[str],
        difficulty: str,
        session_service: "GameSessionService"
    ) -> Tuple[bool, Optional[str], List[TimelineEvent]]:
        """
        Executes a skill check if a target skill is provided.
        """
        if not skill_target:
            return True, None, []

        logs = []
        
        skill_check_result : SkillCheckResult = session_service.character_service.perform_skill_check(
            skill_name=skill_target,
            difficulty_name=difficulty
        )
        
        # Build Log
        skill_success = skill_check_result.success
        icon = "✅" if skill_success else "❌"
        
        logs.append(TimelineEvent(
            type=TimelineEventType.SKILL_CHECK, 
            timestamp="", 
            content=skill_check_result.message, 
            icon=icon,
            metadata=skill_check_result.model_dump()
        ))
        
        skill_result_context = f"Skill Check '{skill_target}': {'SUCCESS' if skill_success else 'FAILURE'} (Roll: {skill_check_result.roll} vs {skill_check_result.target}). Full result : {skill_check_result.message}"
        
        return skill_success, skill_result_context, logs

    def _extract_logs_from_result(self, result: AgentRunResult) -> List[TimelineEvent]:
        """
        ### _extract_logs_from_result
        **Purpose:** Parses the PydanticAI execution result to extract logs from tool executions.
        """
        logs = []
        for msg in result.new_messages():
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    # Capture Reasoning
                    if part.part_kind == 'text':
                        content = part.content
                        if isinstance(content, str) and content.strip().startswith("REASONING:"):
                            logs.append(TimelineEvent(
                                type=TimelineEventType.SYSTEM_LOG,
                                timestamp="",
                                content=content.replace("REASONING:", "").strip(),
                                icon="🧠"
                            ))

                        # Capture Tool Calls
                        if part.part_kind == 'tool-call':
                            tool_name = part.tool_name
                            args = part.args
                            
                            # Ensure args is a dict for metadata
                            meta_args = args if isinstance(args, dict) else {"raw_args": str(args)}
                            
                            logs.append(TimelineEvent(
                                type=TimelineEventType.SYSTEM_LOG,
                                timestamp="",
                                content=f"Calling tool {tool_name} with args: {args}",
                                icon="⚙️",
                                metadata=meta_args
                            ))

                    if part.part_kind == 'tool-return':
                        content = part.content
                        tool_name = part.tool_name
                        
                        # Systematic Log for Return (Debug/Transparency)
                        logs.append(TimelineEvent(
                            type=TimelineEventType.SYSTEM_LOG,
                            timestamp="",
                            content=f"Tool {tool_name} returned: {str(content)[:200]}...", # Truncate if too long
                            icon="↩️"
                        ))

                        # Get handler or default from centralized utility
                        handler = get_tool_handler(tool_name)

                        
                        try:
                            # Invoke handler to get (type, text, icon, metadata)
                            event_type, text, icon, metadata = handler(content)
                            
                            # Filter out suppressed logs
                            if not text:
                                continue
                            
                            # Global Error Check
                            if isinstance(content, dict) and "error" in content:
                                icon = "⚠️"
                                text = content["error"]
                                event_type = TimelineEventType.SYSTEM_LOG
                                metadata = None

                            logs.append(TimelineEvent(
                                type=event_type,
                                timestamp="", 
                                content=text,
                                icon=icon,
                                metadata=metadata
                            ))

                            # Redundancy: Add SYSTEM_LOG for combat events
                            if event_type in [TimelineEventType.COMBAT_ATTACK, TimelineEventType.COMBAT_DAMAGE]:
                                logs.append(TimelineEvent(
                                    type=TimelineEventType.SYSTEM_LOG,
                                    timestamp="",
                                    content=text,
                                    icon="📝", 
                                    metadata=None
                                ))

                        except Exception as e:
                            log_error(f"Error formatting log for tool {tool_name}: {e}")
                            logs.append(TimelineEvent(
                                type=TimelineEventType.SYSTEM_LOG,
                                timestamp="",
                                content=str(content),
                                icon="⚙️"
                            ))
        return logs

    def _get_traits_context(self, character: Any) -> str:
        """Helper to fetch and format character traits"""
        try:
            manager = RacesManager()
            # character.race is the ID
            race = manager.get_race_by_id(character.race)
            if race:
                culture = next((c for c in race.cultures if c.id == character.culture), None)
                if culture and culture.traits:
                    return f"CHARACTER TRAITS: {culture.traits}"
        except Exception as e:
            log_error(f"Failed to load race/culture traits from race manager: {e}")
        return ""


