"""
Unified state object for the game session.
Combines persistent data (saved to JSON) and transient data (runtime only).
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage

from back.models.domain.combat_state import CombatState


class GameState(BaseModel):
    """
    Unified state object for the game session.
    Combines persistent data (saved to JSON) and transient data (runtime only).
    """
    # ==========================================
    # PERSISTENT STATE (Saved to game_state.json)
    # ==========================================
    
    # Core Session Data
    session_mode: Literal["narrative", "combat"] = "narrative"
    scenario_status: Literal["active", "success", "failure", "death"] = "active"
    
    # References (Foreign Keys)
    narrative_history_id: str = "default"
    combat_history_id: str = "default"
    character_uuid: Optional[str] = None
    user_id: Optional[str] = None # Or UUID, but persisted as str probably. Let's use str for now to match other IDs.
    
    # Context Continuity
    combat_state: Optional[CombatState] = None
    last_combat_result: Optional[dict[str, Any]] = None
    scenario_end_summary: Optional[str] = None
    
    # ==========================================
    # TRANSIENT STATE (Runtime only, exclude=True)
    # ==========================================
    
    # Input / Output
    pending_player_message: Optional[str] = Field(default=None, exclude=True)
    
    # LLM Context Buffer
    model_messages: Optional[list[ModelMessage]] = Field(default=None, exclude=True)
    
    # Runtime Metadata
    processing_meta: dict[str, Any] = Field(default_factory=dict, exclude=True)
