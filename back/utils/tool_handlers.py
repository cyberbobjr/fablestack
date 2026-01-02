from typing import Any, Dict, Optional, Tuple

from back.models.api.skills import SkillCheckResult
from back.models.enums import TimelineEventType


def format_skill_log(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_skill_log
    **Purpose:** Specific handler for skill check results (Pydantic Model).
    
    **Args:**
        content (Any): The result from the skill check tool.
        
    **Returns:**
        Tuple: (EventType, Message, Icon, Metadata)
    """
    if isinstance(content, SkillCheckResult):
        icon = "✅" if content.success else "❌"
        return TimelineEventType.SKILL_CHECK, content.message, icon, content.model_dump()
        
    elif isinstance(content, dict):
        # Legacy/Fallback if dict is returned
        return TimelineEventType.SKILL_CHECK, content.get("message", str(content)), "🎲", content
        
    return TimelineEventType.SKILL_CHECK, str(content), "🎲", None

def format_item_added(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_item_added
    **Purpose:** Formats the log for item additions/discoveries.
    
    **Args:**
        content (Any): Dictionary containing message, item_id, qty, and transaction info.
        
    **Returns:**
        Tuple: (EventType, Message, Icon, Metadata)
    """
    if not isinstance(content, dict):
        return format_default_log(content)
        
    return TimelineEventType.ITEM_ADDED, content.get("message"), "🎒", {
        "item_id": content.get("item_id"),
        "qty": content.get("qty"),
        "transaction": content.get("transaction") # For purchases
    }

def format_attack_log(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_attack_log
    **Purpose:** Formats the log for combat attacks.
    
    **Args:**
        content (Any): Dictionary containing message, damage, hit status, etc.
        
    **Returns:**
        Tuple: (EventType, Message, Icon, Metadata)
    """
    if not isinstance(content, dict):
        return format_default_log(content)
        
    return TimelineEventType.COMBAT_ATTACK, content.get("message"), "⚔️", content

def format_currency_log(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_currency_log
    **Purpose:** Formats logs for currency changes.
    
    **Args:**
        content (Any): Dictionary containing message and currency details.
        
    **Returns:**
        Tuple: (EventType, Message, Icon, Metadata)
    """
    if not isinstance(content, dict):
        return format_default_log(content)
        
    return TimelineEventType.CURRENCY_CHANGE, content.get("message"), "💰", content

def format_combat_declared(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_combat_declared
    **Purpose:** Formats log when combat is declared.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.SYSTEM_LOG, content.get("message", "Combat declared"), "⚠️", content


def format_direct_damage(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_direct_damage
    **Purpose:** Formats log for direct damage application.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.COMBAT_DAMAGE, content.get("message", "Damage applied"), "💥", content

def format_combat_started(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_combat_started
    **Purpose:** Formats log when combat starts.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.SYSTEM_LOG, content.get("message", "Combat started"), "⚔️", content

def format_end_turn(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_end_turn
    **Purpose:** Formats log when a turn ends.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.SYSTEM_LOG, content.get("message", "Turn ended"), "⏳", content

def format_check_combat_end(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_check_combat_end
    **Purpose:** Formats log for combat end checks.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    
    if content.get("status") in ["no_combat", "ongoing"]:
        return TimelineEventType.SYSTEM_LOG, None, None, None
        
    return (
        TimelineEventType.SYSTEM_LOG, 
        content.get("message", "Combat check"), 
        "🏁" if content.get("combat_ended") else "ℹ️", 
        content
    )

def format_end_combat(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_end_combat
    **Purpose:** Formats log when combat ends.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
        
    if content.get("status") == "no_combat":
        return TimelineEventType.SYSTEM_LOG, None, None, None
        
    return TimelineEventType.SYSTEM_LOG, content.get("message", "Combat ended"), "🏁", content

def format_combat_status_check(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_combat_status_check
    **Purpose:** Formats log for combat status requests (usually suppressed).
    """
    return TimelineEventType.SYSTEM_LOG, None, None, None

def format_search_enemy(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_search_enemy
    **Purpose:** Formats log for enemy search results.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.SYSTEM_LOG, content.get("message", "Search complete"), "🔎", None

def format_item_removed(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_item_removed
    **Purpose:** Formats log for item removals.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.ITEM_REMOVED, content.get("message", "Item removed"), "🗑️", {
        "item_id": content.get("item_id"), 
        "qty": content.get("qty")
    }

def format_quantity_decreased(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_quantity_decreased
    **Purpose:** Formats log when item quantity decreases.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.ITEM_REMOVED, content.get("message", "Quantity decreased"), "📉", {
        "item_id": content.get("item_id"), 
        "amount": content.get("amount")
    }

def format_quantity_increased(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_quantity_increased
    **Purpose:** Formats log when item quantity increases.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.ITEM_ADDED, content.get("message", "Quantity increased"), "📈", {
        "item_id": content.get("item_id"), 
        "amount": content.get("amount")
    }

def format_item_sold(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_item_sold
    **Purpose:** Formats log when an item is sold.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.CURRENCY_CHANGE, content.get("message", "Item sold"), "💰", {
        "item_id": content.get("item_id"), 
        "amount": content.get("refund")
    }

def format_item_crafted_weapon(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_item_crafted_weapon
    **Purpose:** Formats log for weapon crafting.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.ITEM_CRAFTED, content.get("message", "Weapon created"), "🔨", {
        "item_id": content.get("item_id")
    }

def format_item_crafted_armor(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_item_crafted_armor
    **Purpose:** Formats log for armor crafting.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.ITEM_CRAFTED, content.get("message", "Armor created"), "🛡️", {
        "item_id": content.get("item_id")
    }

def format_item_crafted_generic(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_item_crafted_generic
    **Purpose:** Formats log for general item crafting.
    """
    if not isinstance(content, dict):
        return format_default_log(content)
    return TimelineEventType.ITEM_CRAFTED, content.get("message", "Item created"), "🛠️", {
        "item_id": content.get("item_id")
    }

def format_equipment_list(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_equipment_list
    **Purpose:** Formats log for equipment list checking.
    """
    return TimelineEventType.SYSTEM_LOG, "Equipment list checked", "📋", None

def format_default_log(content: Any) -> Tuple[TimelineEventType, Optional[str], Optional[str], Optional[Dict]]:
    """
    ### format_default_log
    **Purpose:** Default handler for unknown tools.
    """
    if isinstance(content, dict):
         return TimelineEventType.TOOL_RESULT, content.get("message", str(content)), "⚙️", content
    return TimelineEventType.TOOL_RESULT, str(content), "⚙️", None

# Centralized mapping of tool names to their respective handlers
# This avoids scattered lambda definitions and ensures consistency across services.
TOOL_HANDLERS = {
    "skill_check_with_character": format_skill_log,
    "declare_combat_start_tool": format_combat_declared,
    "execute_attack_tool": format_attack_log,
    "apply_direct_damage_tool": format_direct_damage,
    "start_combat_tool": format_combat_started,
    "end_turn_tool": format_end_turn,
    "check_combat_end_tool": format_check_combat_end,
    "end_combat_tool": format_end_combat,
    "get_combat_status_tool": format_combat_status_check,
    "search_enemy_archetype_tool": format_search_enemy,
    "inventory_add_item": format_item_added,
    "inventory_remove_item": format_item_removed,
    "inventory_decrease_quantity": format_quantity_decreased,
    "inventory_increase_quantity": format_quantity_increased,
    "inventory_buy_item": format_item_added,
    "inventory_sell_item": format_item_sold,
    "find_or_create_item_tool": format_item_added,
    "create_weapon": format_item_crafted_weapon,
    "create_armor": format_item_crafted_armor,
    "create_item": format_item_crafted_generic,
    "list_available_equipment": format_equipment_list,
    "character_add_currency": format_currency_log,
    "character_remove_currency": format_currency_log,
}

def get_tool_handler(tool_name: str) -> Any:
    """
    ### get_tool_handler
    **Purpose:** Retrieves the uniformized handler for a given tool name.
    
    **Args:**
        tool_name (str): The name of the tool to handle.
        
    **Returns:**
        Callable: The formatting function (defaults to format_default_log).
    """
    return TOOL_HANDLERS.get(tool_name, format_default_log)
