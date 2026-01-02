from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from back.models.domain.payloads import CombatIntentPayload
from back.services.combat_service import CombatService
from back.utils.logger import log_error, log_info

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

import functools

from back.models.domain.combat_state import AttackResult, CombatantType

# combat_service will be instantiated per request from context
# combat_service = CombatService()



def tool_with_logging(func):
    """
    Decorator to log tool execution and errors.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        try:
            # log_debug(f"Tool {tool_name} called", args={k: str(v)[:100] for k, v in kwargs.items()})
            return await func(*args, **kwargs)
        except Exception as e:
            log_error(f"Error in {tool_name}: {e}")
            return {"error": str(e)}
    return wrapper





def search_enemy_archetype_tool(ctx: RunContext[Any], query: str) -> dict:
    """
    Searches for valid enemy archetypes (ID and name) based on a query.
    
    Use this tool to find the `archetype_id` required for starting a combat.
    NEVER invent an archetype ID. Always use one returned by this tool.
    
    Args:
        query (str): The search term (e.g., "goblin", "orc", "spider").
        
    Returns:
        dict: A dictionary containing a list of matching archetypes.
              Example: {"results": [{"id": "goblin_warrior", "name": "Goblin Warrior", "description": "..."}]}
    """
    log_info("Tool search_enemy_archetype_tool called", tool="search_enemy_archetype_tool", query=query)
    
    try:
        races_service = ctx.deps.races_service
        if not races_service:
            return {"error": "Races service not available in context"}
        
        results = races_service.search_archetypes(query)
        
        return {
            "results": results,
            "count": len(results),
            "message": f"Found {len(results)} archetypes matching '{query}'."
        }
        
    except Exception as e:
        log_error(f"Error in search_enemy_archetype_tool: {e}")
        return {"error": str(e)}

@tool_with_logging
async def declare_combat_start_tool(ctx: RunContext[Any], description: str) -> dict:
    """
    Use this tool ONLY when a fight breaks out or the player attacks someone who isn't already in combat.
    Result: Signals the system to switch to Combat Mode. The Combat Agent will handle the setup.

    Args:
        description (str): A description of the encounter (e.g. "Three goblins jump from the bushes", "The merchant draws a dagger").

    Returns:
        dict: A status message confirming the intent.
    """
    try:
        session_service = ctx.deps
        # We assume session_service has a way to store this pending state.
        # For now, we can set a flag on the GameSessionService logic side or handle it via return value inspection.
        # However, to be "stateful", let's update proper game state.
        
        # We'll treat 'initializing' as a special combat state if needed, or just specific flag.
        # Let's set a 'pending_combat' attribute on the runtime session object if possible,
        # or rely on the LogicOracleService to see this tool call and act.
        
        return {
            "status": "combat_declared",
            "message": "Combat declaration registered. Switching to Combat Engine.",
            "description": description
        }
    except Exception as e:
        return {"error": str(e)}

async def start_combat_tool(ctx: RunContext[Any], enemies: list[dict], description: str = None) -> dict:
    """
    Starts a new combat encounter with the specified enemies.

    This tool initializes the combat state, generating enemies and rolling initiative.
    **CRITICAL:** This MUST be the first tool called when a fight breaks out. 
    You cannot attack enemies until you have successfully called this tool.
    Use this when the narrative dictates a fight should begin.

    Args:
        enemies (list[dict]): **REQUIRED**. A list of dictionaries, each representing an enemy. 
                              Each dict MUST contain 'name' (str). 
                              Optional keys: 'archetype' (str), 'hp' (int), 'ac' (int), 'attack_bonus' (int).
                              
                              **CHEAT SHEET FOR UNKNOWN STATS:**
                              If you don't know the exact stats, use placeholders!
                              Example: `[{"name": "Mysterious Assassin", "archetype": "human"}]`
                              The system will fill in defaults for stats. DO NOT pass an empty list or omit this argument.
        description (str, optional): A brief narrative description of the combat start.

    Returns:
        dict: A summary of the started combat, including participants and turn order.
    """
    log_info("Tool start_combat_tool called", tool="start_combat_tool", enemies_count=len(enemies))

    try:
        game_state = await ctx.deps.load_game_state()
        if not game_state:
            return {"error": "Game state not found"}

        if game_state.combat_state and game_state.combat_state.is_active:
             return {"error": "Combat is already active. End current combat before starting a new one."}

        # 1. Construct Intent
        from back.models.domain.payloads import (CombatIntentPayload,
                                                 EnemyIntent)
        
        enemy_intents = []
        for e in enemies:
             # Ensure defaults if missing
             enemy_intents.append(EnemyIntent(
                 name=e.get("name", "Unknown Enemy"),
                 archetype=e.get("archetype", "Generic Enemy"),
                 hp=e.get("hp", 10),
                 max_hp=e.get("hp", 10), # Assume full HP start
                 ac=e.get("ac", 10),
                 attack_bonus=e.get("attack_bonus", 2)
             ))

        intent = CombatIntentPayload(
            enemies_detected=enemy_intents,
            description=description
        )

        # 2. Start Combat via Service
        combat_service = CombatService(
            races_data_service=ctx.deps.races_service,
            character_data_service=ctx.deps.data_service
        )
        new_combat_state = combat_service.start_combat(intent, ctx.deps)

        # 3. Update Game State
        game_state.combat_state = new_combat_state
        game_state.session_mode = "combat"
        
        await ctx.deps.update_game_state(game_state)

        # 4. Return Summary
        summary = combat_service.get_combat_summary(new_combat_state).model_dump()
        summary["message"] = f"Combat started! {len(enemy_intents)} enemies engaged."
        return summary

    except Exception as e:
        log_error(f"Error in start_combat_tool: {e}")
        return {"error": str(e)}



async def execute_attack_tool(ctx: RunContext[Any], target_name: str, attack_modifier: int = 0, advantage: bool = False) -> AttackResult:
    """
    Executes a standard physical attack (Melee/Ranged) against a target by name.
    
    This tool performs an attack using the CURRENT turn holder against the specified target.
    It automatically calculates hit/miss and damage.
    
    Args:
        target_name (str): The name (or partial name) of the target to attack (e.g. "Goblin", "Goblin A").
        attack_modifier (int): Bonus to add to the attack roll. **MANDATORY**: Set to 2 if 'PRE-ACTION SKILL CHECK' was a Success.
        advantage (bool): If True, rolls 2d20. **MANDATORY**: Set to True if context implies significant tactical advantage (hidden, prone target).

    Returns:
        dict: A dictionary containing the result of the attack (message, updated state summary, and auto-end info).
    """
    import difflib
    log_info("Tool execute_attack_tool called", tool="execute_attack_tool", target_name=target_name, mod=attack_modifier, adv=advantage)
    
    try:
        game_state = await ctx.deps.load_game_state()
        
        if not game_state:
            return {"error": "Game state not found"}
            
        combat_state = game_state.combat_state
        
        if not combat_state or not combat_state.is_active:
            return {"error": "No active combat found"}
            
        # 1. Identify Attacker (Current Turn Holder)
        attacker = combat_state.get_current_combatant()
        if not attacker:
             return {"error": "Could not identify current attacker from turn order."}
             
        # 2. Identify Target (Name Matching)
        target_id = None
        target_real_name = "Unknown"
        
        # Filter potential targets (exclude self)
        candidates = {p.id: p.name for p in combat_state.participants if p.id != attacker.id and p.is_alive()}
        
        if not candidates:
             return {"error": "No valid targets found (all enemies dead?). check_combat_end_tool might be needed."}
        
        # A. Exact Match (Case Insensitive)
        target_name_lower = target_name.lower()
        for eid, name in candidates.items():
            if name.lower() == target_name_lower:
                target_id = eid
                target_real_name = name
                break
                
        # B. Partial Match (if no exact)
        if not target_id:
            for eid, name in candidates.items():
                if target_name_lower in name.lower():
                    target_id = eid
                    target_real_name = name
                    break
        
        # C. Fuzzy Match (if no partial)
        if not target_id:
             best_match = None
             best_score = 0
             for eid, name in candidates.items():
                 s = difflib.SequenceMatcher(None, target_name_lower, name.lower()).ratio()
                 if s > 0.4 and s > best_score:
                     best_match = eid
                     best_score = s
                     target_real_name = name
             if best_match:
                 target_id = best_match

        # D. Fallback: If only 1 enemy exists, assume them
        if not target_id and len(candidates) == 1:
             target_id = list(candidates.keys())[0]
             target_real_name = list(candidates.values())[0]

        if not target_id:
             available = ", ".join(candidates.values())
             return {"error": f"Could not find target '{target_name}'. Available: {available}"}

        # Execute attack (State is modified in-place)
        # Note: combat_service still expects UUID strings
        combat_service = CombatService(
            races_data_service=ctx.deps.races_service,
            character_data_service=ctx.deps.data_service
        )
        attack_result = await combat_service.execute_attack(
            combat_state, 
            str(attacker.id), 
            str(target_id),
            attack_modifier=attack_modifier,
            advantage=advantage
        )
        result_message = attack_result.message
        
        # Check for combat end
        is_ended = combat_service.check_combat_end(combat_state)
        auto_end_info = None
        
        if is_ended:
            players_alive = any(p.type == CombatantType.PLAYER and p.is_alive() for p in combat_state.participants)
            enemies_alive = any(p.type == CombatantType.NPC and p.is_alive() for p in combat_state.participants)
            
            if not players_alive:
                reason = "defeat"
            elif not enemies_alive:
                reason = "victory"
            else:
                reason = "draw"
            
            combat_state = await combat_service.end_combat(combat_state, reason)
            auto_end_info = {"ended": True, "reason": reason}
            
            # Combat ended, remove state
            game_state.combat_state = None
            game_state.session_mode = "narrative"
            game_state.last_combat_result = {"outcome": reason}
        else:
            # Update state
            game_state.combat_state = combat_state
            
        await ctx.deps.update_game_state(game_state)
        
        # Add resolved target name to result for clarity
        details = attack_result.model_dump()
        details['resolved_target_name'] = target_real_name
            
        return {
            "message": result_message,
            "attack_details": details,
            "combat_state": combat_service.get_combat_summary(combat_state).model_dump(),
            "auto_ended": auto_end_info
        }
    
    except Exception as e:
        log_error(f"Error in execute_attack_tool: {e}")
        return {"error": str(e)}

async def apply_direct_damage_tool(ctx: RunContext[Any], target_id: str, amount: int, reason: str = "effect") -> dict:
    """
    Applies direct damage to a target (e.g., from a spell, trap, or environment).

    This tool inflicts damage without an attack roll.
    It should be used for spells (like Magic Missile), traps, or environmental effects.
    This updates the target's health and checks for combat end conditions.

    Args:
        target_id (str): The UUID of the target.
        amount (int): Amount of damage to apply. Must be a positive integer.
        reason (str): The source or reason for the damage (e.g., "fireball", "trap"). Default is "effect".

    Returns:
        dict: A dictionary containing the result of the damage application.
    """
    log_info("Tool apply_direct_damage_tool called", tool="apply_direct_damage_tool", target_id=target_id, amount=amount)
    
    try:
        game_state = await ctx.deps.load_game_state()
        
        if not game_state:
            return {"error": "Game state not found"}
            
        combat_state = game_state.combat_state
        
        if not combat_state:
            return {"error": "No active combat found"}
            
        # Apply damage
        combat_service = CombatService(
            races_data_service=ctx.deps.races_service,
            character_data_service=ctx.deps.data_service
        )
        combat_state = await combat_service.apply_direct_damage(combat_state, target_id, amount, is_attack=False)
        combat_state.add_log_entry(f"Damage applied to target {target_id}: {amount} ({reason})")
        
        # Check for combat end
        is_ended = combat_service.check_combat_end(combat_state)
        auto_end_info = None
        
        if is_ended:
            players_alive = any(p.type == CombatantType.PLAYER and p.is_alive() for p in combat_state.participants)
            enemies_alive = any(p.type == CombatantType.NPC and p.is_alive() for p in combat_state.participants)
            
            if not players_alive:
                reason = "defeat"
            elif not enemies_alive:
                reason = "victory"
            else:
                reason = "draw"
            
            combat_state = await combat_service.end_combat(combat_state, reason)
            auto_end_info = {"ended": True, "reason": reason}
            
            game_state.combat_state = None
            game_state.session_mode = "narrative"
            game_state.last_combat_result = {"outcome": reason}
        else:
            game_state.combat_state = combat_state
            
        await ctx.deps.update_game_state(game_state)
            
        return {
            "message": f"Applied {amount} damage to {target_id}.",
            "combat_state": combat_service.get_combat_summary(combat_state).model_dump(),
            "auto_ended": auto_end_info
        }

    except Exception as e:
        log_error(f"Error in apply_direct_damage_tool: {e}")
        return {"error": str(e)}

async def end_turn_tool(ctx: RunContext[Any]) -> dict:
    """
    Ends the current turn and moves to the next combatant.

    This tool advances the combat to the next participant's turn.
    It should be used after the current combatant has completed their actions.
    This updates the initiative order and current turn holder.

    Returns:
        dict: A dictionary containing the updated combat summary and the name of the next combatant.
    """
    log_info("Tool end_turn_tool called", tool="end_turn_tool")
    
    try:
        game_state = await ctx.deps.load_game_state()
        
        if not game_state:
            return {"error": "Game state not found"}
            
        combat_state = game_state.combat_state
        
        if not combat_state:
            return {"message": "No active combat found to end turn.", "status": "no_combat"}
        
        combat_service = CombatService(
            races_data_service=ctx.deps.races_service,
            character_data_service=ctx.deps.data_service
        )
        combat_state = combat_service.end_turn(combat_state)
        game_state.combat_state = combat_state
        await ctx.deps.update_game_state(game_state)
        
        summary = combat_service.get_combat_summary(combat_state).model_dump()
        current_participant = combat_state.get_current_combatant()
        
        summary["message"] = f"Turn ended. It's now {current_participant.name if current_participant else 'Unknown'}'s turn"
        
        return summary
        
    except Exception as e:
        log_error(f"Error in end_turn_tool: {e}")
        return {"error": str(e)}

async def check_combat_end_tool(ctx: RunContext[Any]) -> dict:
    """
    Checks if the combat has ended and performs cleanup if so.

    This tool verifies if victory or defeat conditions have been met.
    It should be used periodically or after significant events (like a death) to see if combat is over.
    If ended, it cleans up the combat state.

    Returns:
        dict: A dictionary containing the combat status (ended/ongoing) and end reason if applicable.
    """
    log_info("Tool check_combat_end_tool called", tool="check_combat_end_tool")
    
    try:
        game_state = await ctx.deps.load_game_state()
        
        if not game_state:
            return {"error": "Game state not found"}
            
        combat_state = game_state.combat_state
        
        if not combat_state:
            return {
                "combat_ended": True, # Technically true if no combat
                "status": "no_combat",
                "message": "No active combat found."
            }
            
        combat_service = CombatService(
            races_data_service=ctx.deps.races_service,
            character_data_service=ctx.deps.data_service
        )
        is_ended = combat_service.check_combat_end(combat_state)
        
        if is_ended:
            players_alive = any(p.type == CombatantType.PLAYER and p.is_alive() for p in combat_state.participants)
            enemies_alive = any(p.type == CombatantType.NPC and p.is_alive() for p in combat_state.participants)
            
            if not players_alive:
                reason = "defeat"
            elif not enemies_alive:
                reason = "victory"
            else:
                reason = "draw"
            
            combat_state = await combat_service.end_combat(combat_state, reason)
            
            game_state.combat_state = None
            game_state.session_mode = "narrative"
            game_state.last_combat_result = {"outcome": reason}
            await ctx.deps.update_game_state(game_state)
            
            return {
                "combat_ended": True,
                "status": "ended",
                "end_reason": reason,
                "message": f"Combat ended: {reason}",
                "summary": combat_service.get_combat_summary(combat_state).model_dump()
            }
        else:
            return {
                "combat_ended": False,
                "status": "ongoing",
                "message": "Combat ongoing"
            }
            
    except Exception as e:
        log_error(f"Error in check_combat_end_tool: {e}")
        return {"error": str(e)}

async def end_combat_tool(ctx: RunContext[Any], reason: str) -> dict:
    """
    Forcefully ends the combat.

    This tool terminates the combat session immediately.
    It should be used when the narrative requires combat to stop (e.g., surrender, interruption).
    This deletes the combat state.

    Args:
        reason (str): The reason for ending the combat (e.g., "fled", "negotiated").

    Returns:
        dict: A dictionary containing the final combat summary.
    """
    log_info("Tool end_combat_tool called", tool="end_combat_tool", reason=reason)
    
    try:
        game_state = await ctx.deps.load_game_state()
        
        if not game_state:
            return {"error": "Game state not found"}
            
        combat_state = game_state.combat_state
        
        if combat_state:
            combat_service = CombatService(
                races_data_service=ctx.deps.races_service,
                character_data_service=ctx.deps.data_service
            )
            combat_state = await combat_service.end_combat(combat_state, reason)
            
            game_state.combat_state = None
            game_state.session_mode = "narrative"
            game_state.last_combat_result = {"outcome": reason}
            await ctx.deps.update_game_state(game_state)
            
            return combat_service.get_combat_summary(combat_state).model_dump()
        else:
            return {"message": "No active combat found to end.", "status": "no_combat"}
            
    except Exception as e:
        log_error(f"Error in end_combat_tool: {e}")
        return {"error": str(e)}

async def get_combat_status_tool(ctx: RunContext[Any]) -> dict:
    """
    Retrieves the current status of the combat.

    This tool fetches the current state of the combat.
    It should be used to get a summary of participants, health, and turn order.
    This does not modify the combat state.

    Returns:
        dict: A dictionary containing the combat summary.
    """
    log_info("Tool get_combat_status_tool called", tool="get_combat_status_tool")
    
    try:
        game_state = await ctx.deps.load_game_state()
        
        if not game_state:
            return {"error": "Game state not found"}
            
        combat_state = game_state.combat_state
        
        if not combat_state:
             return {"message": "No active combat.", "status": "no_combat", "participants": []}
            
        combat_service = CombatService(
            races_data_service=ctx.deps.races_service,
            character_data_service=ctx.deps.data_service
        )
        return combat_service.get_combat_summary(combat_state).model_dump()
        
    except Exception as e:
        log_error(f"Error in get_combat_status_tool: {e}")
        return {"error": str(e)}

