"""
API Schemas for Game Scenarios, Sessions, and Timeline.
"""
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from back.models.enums import TimelineEventType

# --- CONFIG MODELS ---

class LLMConfig(BaseModel):
    """Configuration for LLM provider"""
    api_endpoint: str
    api_key: str
    model: str
    token_limit: int = 4000
    keep_last_n_messages: int = 10

class WorldConfig(BaseModel):
    """Configuration for the game world."""
    lore: str
    art_style: str

# --- GAME DATA MODELS ---

class TextIntentResult(BaseModel):
    """Structured output for text analysis."""
    skill_check: Optional[str] = Field(
        default=None, 
        description="The exact ID of the skill or stat to check. NULL if the action is mundane or no check is needed."
    )
    difficulty: Literal["favorable", "normal", "unfavorable"] = Field(
        default="normal",
        description="The difficulty of the check. Favorable = advantage (-20 to target difficulty, easier), Normal = standard, Unfavorable = disadvantage (+20 to target difficulty, harder)."
    )
    reasoning: str = Field(
        ..., 
        description="Brief explanation of why a check is needed or not."
    )



class RaceData(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    characteristic_bonuses: Dict[str, int]
    special_abilities: Optional[List[str]] = []
    base_languages: List[str]
    optional_languages: List[str]
    cultures: Optional[List['CultureData']] = None
    is_playable: bool = True
    is_combatant: bool = True
    default_equipment: Optional[List[Union[str, List[str]]]] = []

class CultureData(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    skill_bonuses: Optional[Dict[str, int]] = None
    characteristic_bonuses: Optional[Dict[str, int]] = None
    free_skill_points: Optional[int] = None
    traits: Optional[str] = None
    special_traits: Optional[Dict[str, Any]] = None

class ScenarioStatus(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    name: str
    status: str # Ex: "available", "in_progress", "completed"
    session_id: Optional[UUID] = None
    scenario_name: Optional[str] = None  # Nom du scénario pour les sessions en cours
    character_name: Optional[str] = None  # Nom du personnage pour les sessions en cours
    is_played: bool = False

class ScenarioGenerationRequest(BaseModel):
    description: str

class ScenarioList(BaseModel):
    scenarios: List[ScenarioStatus]






# --- INPUT MODELS ---
class ChoiceData(BaseModel):
    """Metadata payload for a specific button click."""
    id: str
    label: str
    skill_check: Optional[str] = None # e.g., "athletics"
    difficulty: Literal["favorable", "normal", "unfavorable"] = "normal"

class PlayerInput(BaseModel):
    """Polymorphic input: either raw text or a structured choice."""
    input_mode: Literal["text", "choice"]
    text_content: str  # The user text OR the button label
    choice_data: Optional[ChoiceData] = None
    hidden: bool = False # If true, this input is not saved to history (e.g. system commands)

# --- OUTPUT / TIMELINE MODELS ---
class TimelineEvent(BaseModel):
    """
    A single event in the game history.
    Types:
    - USER_INPUT: What the user said/clicked.
    - SYSTEM_LOG: Mechanical feedback (Dice, Inventory).
    - NARRATIVE: The GM's description.
    - CHOICE: The interactive options presented.
    """
    type: TimelineEventType
    timestamp: str
    content: Any # Polymorphic: String for Text, Dict for Logs/Choices
    icon: Optional[str] = None # e.g., "🎲", "⚔️", "🎒", "💀"
    metadata: Optional[Dict[str, Any]] = None # Structured data for frontend rendering

class LogicResult(BaseModel):
    """Result from the Logic Oracle Service."""
    logs: List[TimelineEvent]
    narrative_context: str


class PlayScenarioRequest(BaseModel):
    """Request model for the merged /gamesession/play endpoint"""
    session_id: str
    input: PlayerInput


# Response models for other scenario endpoints

class SessionInfo(BaseModel):
    """Model for active session information"""
    session_id: str
    scenario_id: str
    scenario_name: str
    character_id: str
    character_name: str

class ActiveSessionsResponse(BaseModel):
    """Response model for the /scenarios/sessions endpoint"""
    sessions: List[SessionInfo]

class StartScenarioRequest(BaseModel):
    """Request model for the /scenarios/start endpoint"""
    scenario_name: str
    character_id: str

class StartScenarioResponse(BaseModel):
    """Response model for the /scenarios/start endpoint"""
    session_id: str
    scenario_name: str
    character_id: str
    message: str
    llm_response: str


class PlayScenarioResponse(BaseModel):
    """Response model for the /scenarios/play endpoint"""
    response: List[TimelineEvent]
    session_id: UUID

class ScenarioHistoryResponse(BaseModel):
    """Response model for the /scenarios/history/{session_id} endpoint"""
    history: List[TimelineEvent]

class DeleteMessageResponse(BaseModel):
    """Response model for the DELETE /scenarios/history/{session_id}/{message_index} endpoint"""
    message: str
    deleted_message_info: Dict[str, Any]
    remaining_messages_count: int


class RestoreRequest(BaseModel):
    """Request model for the restore history endpoint"""
    timestamp: str
