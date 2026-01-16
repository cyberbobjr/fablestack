"""
Unified state object for the game session.
This is the single source of truth for the LangGraph execution.
"""
from typing import Any, List, Literal, Optional, Annotated
import operator

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

from back.models.domain.combat_state import CombatState
from back.models.domain.character import Character
from back.models.api.game import TimelineEvent

def add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    """Append-only reducer for messages."""
    return left + right

def update_ui_messages(left: List[TimelineEvent], right: List[TimelineEvent]) -> List[TimelineEvent]:
    """Append-only reducer for UI events."""
    return left + right

class GameState(BaseModel):
    """
    Unified state object for the LangGraph-based game engine.
    Persisted automatically via LangGraph checkpointer.
    """
    
    # --- Checkpointer Managed State ---
    
    # LLM Context: The actual conversation history for the AI
    # Annotated with add_messages to allow partial updates (appending)
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    
    # Frontend Context: The "Golden Source" for UI
    # Append-only list of TimelineEvents
    ui_messages: Annotated[List[TimelineEvent], update_ui_messages] = Field(default_factory=list)

    # Core Game Objects
    character: Optional[Character] = None
    combat_state: Optional[CombatState] = None
    
    # Game Context
    session_mode: Literal["narrative", "combat"] = "narrative"
    scenario_status: Literal["active", "success", "failure", "death"] = "active"
    
    # References
    user_id: Optional[str] = None
    
    # Transient / Processing Data (Not typically persisted long-term, but part of state flow)
    last_combat_result: Optional[dict[str, Any]] = None
    scenario_end_summary: Optional[str] = None
    
    # Input Buffer (Cleared after processing)
    pending_player_input: Optional[str] = None
