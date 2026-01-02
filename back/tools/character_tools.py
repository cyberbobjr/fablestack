from typing import TYPE_CHECKING, Optional

from pydantic_ai import RunContext

from back.interfaces.game_context_protocol import GameSessionContextProtocol

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService # Keep for backward compat if needed or remove

from back.utils.logger import log_debug, log_warning


async def character_add_currency(
    ctx: RunContext[GameSessionContextProtocol], 
    gold: int = 0, 
    silver: int = 0, 
    copper: int = 0
) -> dict:
    """
    Add currency (gold, silver, copper) to the character.

    This tool adds the specified amount of gold, silver, and copper to the character's inventory.
    It should be used when the character acquires money through looting, rewards, or other means.
    This action persists the changes to the character's state.

    Args:
        gold (int): Amount of gold to add. Must be non-negative. Default is 0.
        silver (int): Amount of silver to add. Must be non-negative. Default is 0.
        copper (int): Amount of copper to add. Must be non-negative. Default is 0.

    Returns:
        dict: A dictionary containing a success message and the updated currency totals.
    """
    try:
        log_debug(
            "Tool character_add_currency called",
            tool="character_add_currency",
            player_id=str(ctx.deps.character_id),
            gold=gold,
            silver=silver,
            copper=copper
        )
        
        if not ctx.deps.character_service:
            return {"error": "Character service not available"}
            
        # Add currency via service
        updated_character = await ctx.deps.character_service.add_currency(gold, silver, copper)
        
        return {
            "message": f"Added {gold}G {silver}S {copper}C",
            "currency": {
                "gold": updated_character.equipment.gold,
                "silver": updated_character.equipment.silver,
                "copper": updated_character.equipment.copper
            }
        }
        
    except Exception as e:
        log_warning(
            "Error in character_add_currency",
            error=str(e),
            character_id=str(ctx.deps.character_id)
        )
        return {"error": f"Failed to add currency: {str(e)}"}

async def character_remove_currency(
    ctx: RunContext[GameSessionContextProtocol], 
    gold: int = 0, 
    silver: int = 0, 
    copper: int = 0
) -> dict:
    """
    Remove currency (gold, silver, copper) from the character.

    This tool removes the specified amount of currency from the character's inventory.
    It should be used when the character LOSES money through theft, fines, bribes, tolls, or other narrative events.
    DO NOT use this for purchases - use inventory_buy_item instead, which handles costs automatically.
    
    The system automatically converts between denominations if needed (1 gold = 10 silver = 100 copper).
    For example, if the character has 5G 0S 0C and needs to pay 3S, the system will convert to 4G 7S 0C.
    
    VALIDATION: You do NOT need to check the character's balance before calling this tool.
    The tool will automatically validate funds and return an error if the character cannot afford it.
    Trust the tool to handle the validation.

    Args:
        gold (int): Amount of gold to remove. Must be non-negative. Default is 0.
        silver (int): Amount of silver to remove. Must be non-negative. Default is 0.
        copper (int): Amount of copper to remove. Must be non-negative. Default is 0.

    Returns:
        dict: A dictionary containing a success message and the updated currency totals, or an error if insufficient funds.
    """
    try:
        log_debug(
            "Tool character_remove_currency called",
            tool="character_remove_currency",
            player_id=str(ctx.deps.character_id),
            gold=gold,
            silver=silver,
            copper=copper
        )
        
        if not ctx.deps.character_service:
            return {"error": "Character service not available"}
            
        # Remove currency via service
        updated_character = await ctx.deps.character_service.remove_currency(gold, silver, copper)
        
        return {
            "message": f"Removed {gold}G {silver}S {copper}C",
            "currency": {
                "gold": updated_character.equipment.gold,
                "silver": updated_character.equipment.silver,
                "copper": updated_character.equipment.copper
            }
        }
        
    except ValueError as e:
        # Insufficient funds
        log_warning(
            "Insufficient funds in character_remove_currency",
            error=str(e),
            character_id=str(ctx.deps.character_id)
        )
        return {"error": str(e)}
    except Exception as e:
        log_warning(
            "Error in character_remove_currency",
            error=str(e),
            character_id=str(ctx.deps.character_id)
        )
        return {"error": f"Failed to remove currency: {str(e)}"}

async def character_take_damage(ctx: RunContext[GameSessionContextProtocol], damage: int, source: str = "unknown") -> dict:
    """
    Apply damage to the character.

    This tool inflicts damage on the character from a specified source.
    It should be used when the character takes damage from traps, environmental hazards,
    or narrative events outside of combat. This updates the character's current hit points.

    Args:
        damage (int): Amount of damage to take. Must be a positive integer.
        source (str): The source of the damage (e.g., "trap", "fall"). Default is "unknown".

    Returns:
        dict: A dictionary containing the damage details and updated character status (HP, is_alive).
    """
    try:
        log_debug(
            "Tool character_take_damage called",
            tool="character_take_damage",
            player_id=str(ctx.deps.character_id),
            damage=damage,
            source=source
        )
        
        if not ctx.deps.character_service:
            return {"error": "Character service not available"}
            
        # Apply damage via service
        updated_character = await ctx.deps.character_service.take_damage(damage, source)
        
        return {
            "message": f"Took {damage} damage from {source}",
            "current_hp": updated_character.combat_stats.current_hit_points,
            "max_hp": updated_character.combat_stats.max_hit_points,
            "is_alive": updated_character.combat_stats.is_alive()
        }
        
    except Exception as e:
        log_warning("Error in character_take_damage", error=str(e))
        return {"error": f"Failed to take damage: {str(e)}"}

async def character_heal(ctx: RunContext[GameSessionContextProtocol], amount: int, source: str = "magic") -> dict:
    """
    Heal the character.

    This tool restores the character's hit points.
    It should be used when the character is healed by potions, spells, resting, or other means.
    This updates the character's current hit points, up to their maximum.

    Args:
        amount (int): Amount of HP to restore. Must be a positive integer.
        source (str): The source of the healing (e.g., "potion", "spell"). Default is "magic".

    Returns:
        dict: A dictionary containing the healing details and updated character status (HP).
    """
    try:
        log_debug(
            "Tool character_heal called",
            tool="character_heal",
            player_id=str(ctx.deps.character_id),
            amount=amount,
            source=source
        )
        
        if not ctx.deps.character_service:
            return {"error": "Character service not available"}
            
        # Apply healing via service
        updated_character = await ctx.deps.character_service.heal(amount, source)
        
        return {
            "message": f"Healed {amount} HP from {source}",
            "current_hp": updated_character.combat_stats.current_hit_points,
            "max_hp": updated_character.combat_stats.max_hit_points
        }
        
    except Exception as e:
        log_warning("Error in character_heal", error=str(e))
        return {"error": f"Failed to heal: {str(e)}"}

async def character_apply_xp(ctx: RunContext[GameSessionContextProtocol], amount: int, reason: str = "milestone") -> dict:
    """
    Award experience points to the character.

    This tool adds experience points (XP) to the character.
    It should be used when the character completes a quest, defeats enemies, or reaches a milestone.
    This may result in the character leveling up if the XP threshold is reached.

    Args:
        amount (int): Amount of XP to award. Must be a positive integer.
        reason (str): The reason for the award (e.g., "quest_completion"). Default is "milestone".

    Returns:
        dict: A dictionary containing the XP gained, total XP, and current level.
    """
    try:
        log_debug(
            "Tool character_apply_xp called",
            tool="character_apply_xp",
            player_id=str(ctx.deps.character_id),
            amount=amount,
            reason=reason
        )
        
        if not ctx.deps.character_service:
            return {"error": "Character service not available"}
            
        # Add XP via service
        updated_character = await ctx.deps.character_service.apply_xp(amount)
        
        return {
            "message": f"Gained {amount} XP for {reason}",
            "total_xp": updated_character.experience_points,
            "level": updated_character.level
        }
        
    except Exception as e:
        log_warning("Error in character_apply_xp", error=str(e))
        return {"error": f"Failed to apply XP: {str(e)}"}


