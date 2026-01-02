"""
Shared enumerations for the FableStack project.
"""
from enum import Enum


class CharacterStatus(str, Enum):
    """Character lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    IN_GAME = "in_game"

class CharacterSex(str, Enum):
    """Character biological sex"""
    MALE = "male"
    FEMALE = "female"


class ItemType(str, Enum):
    """Possible item types"""
    MATERIAL = "Materiel"
    WEAPON = "Arme" 
    ARMOR = "Armure"
    FOOD = "Nourriture"
    MAGIC_ITEM = "Objet_Magique"

class TimelineEventType(str, Enum):
    """Types of events in the timeline"""
    USER_INPUT = "USER_INPUT"
    SYSTEM_LOG = "SYSTEM_LOG"
    NARRATIVE = "NARRATIVE"
    CHOICE = "CHOICE"
    TOOL_RESULT = "TOOL_RESULT" # Deprecated/Generic fallback
    
    # New Structured Types
    SKILL_CHECK = "SKILL_CHECK"
    COMBAT_ATTACK = "COMBAT_ATTACK"
    COMBAT_DAMAGE = "COMBAT_DAMAGE"
    COMBAT_INFO = "COMBAT_INFO"
    COMBAT_TURN = "COMBAT_TURN"
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_REMOVED = "ITEM_REMOVED"
    ITEM_CRAFTED = "ITEM_CRAFTED"
    CURRENCY_CHANGE = "CURRENCY_CHANGE"
