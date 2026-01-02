"""
API Schemas for Character Management and Creation.
"""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from back.models.domain.items import EquipmentItem


class AllocateAttributesRequest(BaseModel):
    race: str

class AllocateAttributesResponse(BaseModel):
    attributes: Dict[str, int]

class CheckAttributesRequest(BaseModel):
    attributes: Dict[str, int]

class CheckAttributesResponse(BaseModel):
    valid: bool

class SaveCharacterRequest(BaseModel):
    character_id: str
    character: dict

class SaveCharacterResponse(BaseModel):
    character: dict
    status: str

class CheckSkillsRequest(BaseModel):
    skills: Dict[str, int]

class CheckSkillsResponse(BaseModel):
    valid: bool
    cost: int

class CreationStatusResponse(BaseModel):
    id: str
    status: str
    created_at: Optional[str] = None

class CharacterListAny(BaseModel):
    characters: List[dict]

class CharacteristicSchema(BaseModel):
    """Schema for an individual characteristic"""
    short_name: str
    category: str  # 'physical', 'mental', or 'social'
    description: str
    examples: List[str]

class CharacteristicsResponse(BaseModel):
    """Response schema for the /api/creation/characteristics endpoint"""
    characteristics: Dict[str, CharacteristicSchema]
    bonus_table: Dict[str, int]
    cost_table: Dict[str, int]
    starting_points: int

class UpdateSkillsRequest(BaseModel):
    character_id: str
    skills: Dict[str, int]

class UpdateSkillsResponse(BaseModel):
    status: str

class AddEquipmentRequest(BaseModel):
    character_id: str
    equipment_name: str

class AddEquipmentResponse(BaseModel):
    status: str
    gold: float
    total_weight: float
    equipment_added: dict

class RemoveEquipmentRequest(BaseModel):
    character_id: str
    equipment_name: str

class RemoveEquipmentResponse(BaseModel):
    status: str
    gold: float
    total_weight: float
    equipment_removed: dict

class UpdateMoneyRequest(BaseModel):
    character_id: str
    amount: float  # Positive to add, negative to subtract

class UpdateMoneyResponse(BaseModel):
    status: str
    gold: float
