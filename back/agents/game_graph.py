"""
LangGraph implementation for the FableStack Game Engine.
Orchestrates the flow between Analysis, Oracle, Combat, Narrative, and Choice agents.
"""
import json
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Literal

import aiosqlite
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import tools_condition

# PydanticAI / Context Imports
from pydantic import BaseModel
from pydantic_ai import RunContext

from back.config import get_llm_config
from back.models.api.game import ChoiceData, TextIntentResult, TimelineEvent
from back.models.domain.game_state import GameState
from back.models.enums import TimelineEventType

# --- Import Tools ---
from back.tools.character_tools import (
    character_add_currency,
    character_apply_xp,
    character_heal,
    character_remove_currency,
    character_take_damage,
)
from back.tools.combat_tools import (
    check_combat_end_tool,
    declare_combat_start_tool,
    end_combat_tool,
    end_turn_tool,
    execute_attack_tool,
    get_combat_status_tool,
    search_enemy_archetype_tool,
    start_combat_tool,
)
from back.tools.equipment_tools import (
    check_inventory_quantity,
    find_or_create_item_tool,
    inventory_add_item,
    inventory_decrease_quantity,
    inventory_increase_quantity,
    inventory_remove_item,
    inventory_sell_item,
    list_available_equipment,
)
from back.tools.scenario_tools import end_scenario_tool
from back.tools.skill_tools import skill_check_with_character
from back.utils.logger import log_error, logger

# We need a protocol or class for the dependencies
# from back.services.game_session_service import GameSessionService # Circular import risk, use Any or Protocol



# --- Constants ---
MAX_HISTORY_LENGTH = 20 # Number of messages before summarization trigger

# --- Helper Functions ---

def get_cleaned_tool_definitions(tools: List[Callable]) -> List[Dict]:
    """
    Generates OpenAI-compatible tool definitions, stripping the 'ctx' argument
    that PydanticAI tools expect.
    """
    definitions = []
    # We can use LangChain's utils or pydantic to generate schema, 
    # but simplest is to use langchain_core.utils.function_calling.convert_to_openai_tool
    # and then manually remove 'ctx' from properties.
    from langchain_core.utils.function_calling import convert_to_openai_tool
    
    for tool in tools:
        schema = convert_to_openai_tool(tool)
        # Check parameters
        if "function" in schema and "parameters" in schema["function"]:
            params = schema["function"]["parameters"]
            if "properties" in params and "ctx" in params["properties"]:
                del params["properties"]["ctx"]
            if "required" in params and "ctx" in params["required"]:
                params["required"].remove("ctx")
        definitions.append(schema)
    return definitions

# --- Node Implementations ---

async def analysis_node(state: GameState):
    """
    Analyzes the latest user message to determine intent and potential skill checks.
    """
    logger.info("--- Analysis Node ---")
    
    # Get the last user message
    last_message = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
    if not last_message:
        return {} # No new input to analyze

    llm_config = get_llm_config()
    model = ChatOpenAI(model=llm_config.model, api_key=llm_config.api_key, base_url=llm_config.api_endpoint)
    
    # Simple structured output for intent
    analyzed = model.with_structured_output(TextIntentResult).invoke(
        f"Analyze this player action for skill checks: '{last_message.content}'"
    )

    # Log analysis result to UI if there's a skill check needed
    events = []
    if analyzed.skill_check and str(analyzed.skill_check).lower() != "null":
        events.append(TimelineEvent(
            type=TimelineEventType.SYSTEM_LOG,
            timestamp=datetime.now().isoformat(),
            content=f"Skill check needed: {analyzed.skill_check} ({analyzed.difficulty}). Reasoning: {analyzed.reasoning}",
            icon="🧠"
        ))

    # We store the analysis result in processing_meta to pass to the next node
    return {
        "processing_meta": {"analysis": analyzed.model_dump()},
        "ui_messages": events
    }


async def oracle_node(state: GameState):
    """
    Handles Narrative/Adventure logic (Non-Combat).
    Executes tools and determines consequences.
    """
    logger.info("--- Oracle Node ---")
    
    llm_config = get_llm_config()
    model = ChatOpenAI(model=llm_config.model, api_key=llm_config.api_key, base_url=llm_config.api_endpoint)
    
    # Bind tools with CLEANED schema
    tools = [
        declare_combat_start_tool, find_or_create_item_tool, inventory_add_item, inventory_remove_item,
        inventory_sell_item, inventory_decrease_quantity, inventory_increase_quantity, check_inventory_quantity,
        list_available_equipment, character_add_currency, character_remove_currency, character_heal,
        character_take_damage, character_apply_xp, skill_check_with_character, end_scenario_tool
    ]
    tool_defs = get_cleaned_tool_definitions(tools)
    model_with_tools = model.bind_tools(tool_defs)
    
    # Context Construction
    analysis = state.processing_meta.get("analysis", {})
    skill_target = analysis.get("skill_check")
    
    char_context = ""
    if state.character:
        char_context = state.character.build_narrative_prompt_block()

    system_prompt = (
        "You are the Game Engine and Referee. STRICTLY adjudicate game mechanics.\n"
        "1. Analyze intent and context.\n"
        "2. Check for scenario triggers.\n"
        "3. Execute appropriate tools (Transactions, Skill Checks, Spawning Combat using `declare_combat_start_tool`).\n"
        "4. If a fight breaks out, you MUST call `declare_combat_start_tool`.\n"
        f"CONTEXT: Player intends to '{skill_target if skill_target else 'act'}'."
        f"\nCHARACTER STATUS:\n{char_context}"
    )
    
    messages = [SystemMessage(content=system_prompt)] + state.messages
    
    response = await model_with_tools.ainvoke(messages)
    
    return {"messages": [response]}


async def combat_node(state: GameState):
    """
    Handles Round-based Tactical Combat.
    """
    logger.info("--- Combat Node ---")
    
    llm_config = get_llm_config()
    model = ChatOpenAI(model=llm_config.model, api_key=llm_config.api_key, base_url=llm_config.api_endpoint)
    
    tools = [
        start_combat_tool, execute_attack_tool, end_turn_tool, check_combat_end_tool,
        end_combat_tool, get_combat_status_tool, search_enemy_archetype_tool, skill_check_with_character
    ]
    tool_defs = get_cleaned_tool_definitions(tools)
    model_with_tools = model.bind_tools(tool_defs)
    
    combat_state = state.combat_state
    
    char_context = ""
    if state.character:
        # For combat we might strictly need combat stats, but narrative block is good context
        char_context = state.character.build_narrative_prompt_block()

    system_prompt = (
        "You are the Tactical Combat Engine. Manage the specific combat mechanics.\n"
        "MODES:\n"
        "1. INITIALIZATION: If combat just started, call `start_combat_tool` with enemies list.\n"
        "2. RESOLUTION: Execute turn for current combatant. One major action -> `end_turn_tool`.\n"
        f"CURRENT STATUS: {combat_state.current_turn_combatant_id if combat_state else 'Not Started'}\n"
        f"CHARACTER STATUS:\n{char_context}"
    )
    
    messages = [SystemMessage(content=system_prompt)] + state.messages
    response = await model_with_tools.ainvoke(messages)
    
    return {"messages": [response]}



async def choice_node(state: GameState):
    """
    Generates 3-4 options for the player based on the current context.
    """
    logger.info("--- Choice Node ---")
    
    llm_config = get_llm_config()
    model = ChatOpenAI(model=llm_config.model, api_key=llm_config.api_key, base_url=llm_config.api_endpoint)
    
    messages = state.messages
    char_context = ""
    if state.character:
        char_context = state.character.build_narrative_prompt_block()
        
    system_prompt = (
        "You are the Game Master. Provide 3 to 4 distinct choices for the player's next action.\n"
        "Consider the recent narrative and character abilities.\n"
        "Options should be concise and drive the story forward.\n"
        f"CHARACTER STATUS:\n{char_context}"
    )

    class ChoicesOutput(BaseModel):
        choices: List[ChoiceData]

    response = await model.with_structured_output(ChoicesOutput).ainvoke(
        [SystemMessage(content=system_prompt)] + messages
    )
    
    # Convert to TimelineEvent
    event = TimelineEvent(
        type=TimelineEventType.CHOICES,
        timestamp=datetime.now().isoformat(),
        content=response.choices if response else [],
        icon="🤔"
    )
    
    return {"ui_messages": [event]}


async def summarization_node(state: GameState):
    """
    Summarizes older messages to save context window.
    """
    logger.info("--- Summarization Node ---")
    
    llm_config = get_llm_config()
    model = ChatOpenAI(model=llm_config.model, api_key=llm_config.api_key, base_url=llm_config.api_endpoint)
    
    # Keep last 5 messages, summarize the rest
    messages = state.messages
    if len(messages) > MAX_HISTORY_LENGTH:
        # Determine split index (keep last 5)
        split_idx = len(messages) - 5
        messages_to_summarize = messages[:split_idx]
        
        summary_prompt = "Summarize the conversation so far, focusing on key events and current status."
        
        summary_response = await model.ainvoke([
            SystemMessage(content=summary_prompt),
            *messages_to_summarize
        ])
        
        # Create summary message
        summary_message = SystemMessage(
            content=f"PREVIOUS SUMMARY: {summary_response.content}",
            id=str(uuid.uuid4())
        )
        
        # Delete old messages
        delete_messages = [RemoveMessage(id=m.id) for m in messages_to_summarize if m.id]
        
        return {"messages": [summary_message] + delete_messages}
        
    return {}


async def narrative_node(state: GameState):
    """
    Generates the immersive story description based on the system events.
    """
    logger.info("--- Narrative Node ---")
    
    llm_config = get_llm_config()
    model = ChatOpenAI(model=llm_config.model, api_key=llm_config.api_key, base_url=llm_config.api_endpoint)

    last_ai_msg = state.messages[-1]
    
    char_context = ""
    if state.character:
        char_context = state.character.build_narrative_prompt_block()

    # Create a prompt that summarizes what just happened (tool outputs are in history)
    system_prompt = (
        "You are the NARRATOR. Your role is purely DESCRIPTIVE.\n"
        "Turn the recent system logs and tool outputs into an immersive, atmospheric narrative.\n"
        "Do NOT invent new actions. Just describe the scene.\n"
        f"CHARACTER CONTEXT:\n{char_context}"
    )
    
    messages = [SystemMessage(content=system_prompt)] + state.messages
    response = await model.ainvoke(messages)
    
    # Extract text and create a UI event for it
    narrative_text = response.content
    event = TimelineEvent(
        type=TimelineEventType.NARRATIVE,
        timestamp=datetime.now().isoformat(),
        content=str(narrative_text),
        icon="📖"
    )
    
    return {"messages": [response], "ui_messages": [event]}


async def execute_tools_node(state: GameState, config: RunnableConfig):
    """
    Custom Tool Execution Node that injects dependencies (GameSessionService) into PydanticAI tools.
    """
    logger.info("--- Execute Tools Node ---")
    
    # Retrieve Dependencies from Config
    session_service = config.get("configurable", {}).get("session_service")
    if not session_service:
        log_error("GameSessionService not found in runnable config")
        return {
            "messages": [
                ToolMessage(
                    tool_call_id="error", 
                    content="System Error: Dependencies not initialized.",
                    name="system"
                )
            ]
        }
    
    # Mock RunContext and Deps
    class MockDeps:
        def __init__(self, svc):
            self.character_service = svc.character_service
            self.character_id = svc.character_id
            self.session_service = svc # Or however deps are structured
            
    # Map all relevant tools
    all_tools = [
        declare_combat_start_tool, find_or_create_item_tool, inventory_add_item, inventory_remove_item,
        inventory_sell_item, inventory_decrease_quantity, inventory_increase_quantity, check_inventory_quantity,
        list_available_equipment, character_add_currency, character_remove_currency, character_heal,
        character_take_damage, character_apply_xp, skill_check_with_character, end_scenario_tool,
        start_combat_tool, execute_attack_tool, end_turn_tool, check_combat_end_tool,
        end_combat_tool, get_combat_status_tool, search_enemy_archetype_tool
    ]
    tool_map = {t.__name__: t for t in all_tools}
    
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {} # Should not happen if routed correctly
        
    outputs = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]
        
        tool_func = tool_map.get(tool_name)
        if not tool_func:
            outputs.append(ToolMessage(tool_call_id=call_id, content=f"Error: Tool {tool_name} not found.", name=tool_name))
            continue
            
        try:
            # Inject Context
            ctx = RunContext(
                deps=MockDeps(session_service),
                retry=0,
                tool_name=tool_name
            )
            
            # Execute
            # The tool functions are async, so await them
            result = await tool_func(ctx, **args)
            
            # Format Result
            content = str(result)
            if isinstance(result, dict):
                content = json.dumps(result)
                
            outputs.append(ToolMessage(tool_call_id=call_id, content=content, name=tool_name))
            
        except Exception as e:
            msg = f"Error executing {tool_name}: {str(e)}"
            logger.error(msg)
            outputs.append(ToolMessage(tool_call_id=call_id, content=msg, name=tool_name))
            
    # Sync Character State
    updated_character = None
    try:
        if session_service.character_service:
            updated_character = session_service.character_service.get_character()
    except Exception as e:
        logger.error(f"Failed to sync character state: {e}")

    return {"messages": outputs, "character": updated_character}


# --- Edge Logic ---

def route_after_analysis(state: GameState) -> Literal["combat_node", "oracle_node"]:
    """Decides where to go after analysis."""
    if state.session_mode == "combat":
        return "combat_node"
    return "oracle_node"


def should_continue_combat(state: GameState) -> Literal["combat_node", "narrative_node"]:
    """Loops combat if not ended."""
    if state.combat_state and state.combat_state.is_active:
        return "combat_node"
    return "narrative_node"


def should_summarize(state: GameState) -> Literal["summarization_node", "end"]:
    """Check if summarization is needed."""
    if len(state.messages) > MAX_HISTORY_LENGTH:
        return "summarization_node"
    return "end"


def route_after_tools(state: GameState) -> Literal["combat_node", "narrative_node"]:
    """Routes back to combat or narrative after tool execution."""
    if state.session_mode == "combat":
        return "combat_node"
    return "narrative_node"


# --- Graph Construction ---

async def build_game_graph():
    """Builds and compiles the Game Graph."""
    workflow = StateGraph(GameState)

    # Add Nodes
    workflow.add_node("analysis_node", analysis_node)
    workflow.add_node("oracle_node", oracle_node)
    workflow.add_node("combat_node", combat_node)
    workflow.add_node("narrative_node", narrative_node)
    workflow.add_node("choice_node", choice_node)
    workflow.add_node("summarization_node", summarization_node)
    
    # Custom Tool Node
    workflow.add_node("tools", execute_tools_node)

    # Add Edges
    workflow.set_entry_point("analysis_node")
    
    workflow.add_conditional_edges(
        "analysis_node",
        route_after_analysis
    )
    
    # Oracle Flow: Oracle -> (maybe Tools) -> Narrative
    workflow.add_conditional_edges(
        "oracle_node",
        tools_condition,
        {
            "tools": "tools",
            "end": "narrative_node" 
        }
    )
    
    # Combat Flow: Combat -> (maybe Tools) -> Combat (Loop) OR Narrative (if Ended)
    workflow.add_conditional_edges(
        "combat_node",
        tools_condition,
        {
            "tools": "tools",
            "end": "narrative_node" # Default fallback if no tools call (shouldn't happen in loop ideally)
        }
    )

    # Tool Routing
    # If tools were called by Oracle, go to Narrative
    # If tools were called by Combat, go back to Combat Node (Loop)
    workflow.add_conditional_edges(
        "tools",
        route_after_tools
    )
    
    workflow.add_edge("narrative_node", "choice_node")
    
    workflow.add_conditional_edges(
        "choice_node",
        should_summarize,
        {
            "summarization_node": "summarization_node",
            "end": END
        }
    )
    workflow.add_edge("summarization_node", END)

    # Checkpointer
    conn = await aiosqlite.connect("game_state.db", check_same_thread=False)
    memory = AsyncSqliteSaver(conn)
    
    graph = workflow.compile(checkpointer=memory)
    graph_png = graph.get_graph().draw_mermaid_png()

    with open("graph.png", "wb") as f:
        f.write(graph_png)
    return graph

