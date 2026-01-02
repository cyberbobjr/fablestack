"""
Domain models for items and equipment.
"""
from typing import Optional
from pydantic import BaseModel

class EquipmentItem(BaseModel):
    """
    Standardized equipment item model.
    
    Purpose:
    This model represents any equipment item in the game, including weapons, armor,
    and general items. It provides a unified structure for inventory management,
    ensuring type safety and validation of all equipment data loaded from YAML files.
    The model supports various equipment types with optional fields for specific
    attributes like weapon damage/range or armor protection values.
    
    Attributes:
        id (str): Unique UUID for this specific item INSTANCE in the character's inventory.
                  This is generated automatically and is unique per stack/instance.
                  Example: "a3f2c1b0-1234-5678-90ab-cdef12345678"
        item_id (str): Catalog reference ID from equipment.yaml. This identifies WHAT the item is.
                       Use this when adding/buying items. Multiple instances can share the same item_id.
                       Example: "weapon_longsword", "armor_leather", "item_rope"
        name (str): Display name of the item (e.g., "Longbow", "Leather Armor").
        category (str): Equipment category (e.g., "melee", "ranged", "armor", "equipment").
        cost_gold (int): Gold cost of the item. Default: 0.
        cost_silver (int): Silver cost of the item. Default: 0.
        cost_copper (int): Copper cost of the item. Default: 0.
        weight (float): Weight of the item in kilograms.
        quantity (int): Number of items in this stack.
        equipped (bool): Whether the item is currently equipped by the character.
        description (Optional[str]): Textual description of the item.
        damage (Optional[str]): Damage dice formula for weapons (e.g., "1d8+2").
        range (Optional[int]): Range in meters for ranged weapons (e.g., 150 for Longbow).
        protection (Optional[int]): Armor protection value (e.g., 3 for Leather Armor).
        type (Optional[str]): Specific type classification (e.g., "weapon", "armor", "consumable").
    """
    id: str
    item_id: str
    name: str
    category: str
    cost_gold: int = 0
    cost_silver: int = 0
    cost_copper: int = 0
    weight: float
    quantity: int
    equipped: bool
    description: Optional[str] = None
    damage: Optional[str] = None
    range: Optional[int] = None
    protection: Optional[int] = None
    type: Optional[str] = None

