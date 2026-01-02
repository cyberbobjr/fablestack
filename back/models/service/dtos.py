"""
DTOs (Data Transfer Objects) for Service responses.
Ensures strict type safety for internal service-to-router communication.
"""

from typing import List, Optional

from pydantic import BaseModel


class SessionSummary(BaseModel):
    """
    Summary of a game session.
    Used by list_all_sessions.
    """
    session_id: str
    character_id: str
    scenario_id: str

class SessionMetadata(BaseModel):
    """
    Detailed metadata information about a session.
    Used by get_session_info as an internal service DTO.
    """
    character_id: str
    scenario_name: str

class SessionStartResult(BaseModel):
    """
    Result of starting a new session/scenario.
    """
    session_id: str
    scenario_name: str
    character_id: str
    message: str

class ParticipantSummary(BaseModel):
    """
    Summary of a combat participant.
    """
    id: str
    name: str
    hp: int
    max_hp: int
    camp: str

class CombatSummary(BaseModel):
    """
    Summary of a combat state.
    Used by get_combat_summary.
    """
    combat_id: str
    round: int
    participants: List[ParticipantSummary]
    turn_order: List[str]
    current_turn: Optional[str] = None
    status: str
    log: List[str]
