"""
API Schemas for Equipment and Items.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from back.models.domain.items import EquipmentItem


class EquipmentResponse(BaseModel):
    """Response model for the /api/creation/equipment endpoint"""
    weapons: List[EquipmentItem]
    armor: List[EquipmentItem]
    accessories: List[EquipmentItem]
    consumables: List[EquipmentItem]
    general: List[EquipmentItem]
