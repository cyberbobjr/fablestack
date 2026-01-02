"""
Domain payloads for agent communication and state transitions.
Replaces DTOs previously located in back/graph/dto/
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class EnemyIntent(BaseModel):
    """
    Intent to spawn an enemy.
    """
    name: str
    archetype: str = "Generic Enemy"
    max_hp: int = 10
    hp: int = 10
    ac: int = 10
    attack_bonus: int = 2

class CombatIntentPayload(BaseModel):
    """
    Payload indicating detection of a combat situation.
    """
    enemies_detected: List[EnemyIntent]
    description: Optional[str] = None 

class ScenarioEndPayload(BaseModel):
    """
    Payload indicating the scenario has ended.
    """
    outcome: str # "success", "failure", "death"
    summary: str
    rewards: Optional[Dict[str, Any]] = None

class CombatTurnContinuePayload(BaseModel):
    """
    Payload indicating combat continues (e.g. AI finished its turn, now player's turn).
    """
    message: str # Narrative description of what happened

class CombatTurnEndPayload(BaseModel):
    """
    Payload indicating combat has ended.
    """
    reason: str
    summary: str
    winner: str = "unknown" # "player", "enemy", "unknown"
