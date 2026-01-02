"""
API Schemas for Skills and Stats.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SkillStatBonus(BaseModel):
    """Model for stat bonuses on a skill"""
    min_value: int
    bonus_points: int

class SkillInfo(BaseModel):
    """Model for individual skill information"""
    id: str
    name: str
    description: str
    stat_bonuses: Optional[Dict[str, SkillStatBonus]] = None

class SkillGroup(BaseModel):
    """Model for a skill group"""
    name: str
    skills: Dict[str, SkillInfo]

class RacialAffinity(BaseModel):
    """Model for racial affinity"""
    skill: str
    base_points: int

class SkillsResponse(BaseModel):
    """Response model for the /api/creation/skills endpoint"""
    skill_groups: Dict[str, SkillGroup]
    racial_affinities: Dict[str, List[RacialAffinity]]
    skill_creation_rules: Optional[Dict[str, int]] = None


class StatInfo(BaseModel):
    """Model for stat information"""
    id: str
    name: str
    description: str
    min_value: int
    max_value: int

class ValueRange(BaseModel):
    """Model for stat value range"""
    min: int
    max: int

class StatsResponse(BaseModel):
    """Response model for the /api/creation/stats endpoint"""
    stats: Dict[str, StatInfo]
    value_range: ValueRange
    bonus_formula: str
    bonus_table: Dict[str, int]
    cost_table: Dict[str, int]
    starting_points: Optional[int] = None

class SkillCheckResult(BaseModel):
    """Result of a skill check tool execution"""
    message: str
    skill_name: str
    roll: int
    target: int
    success: bool
    degree: str
    source_used: str
    error: Optional[str] = None
