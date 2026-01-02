import asyncio
import difflib
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from pydantic_ai import RunContext

from back.interfaces.game_context_protocol import GameSessionContextProtocol

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

from back.utils.logger import log_debug, log_warning


async def inventory_add_item(ctx: RunContext[GameSessionContextProtocol], item_id: str, qty: int = 1) -> dict:
    """
    Add a free item to the character's inventory.

    This tool adds an item to the character's inventory without any cost.
    It should be used for rewards, loot, gifts, or quest items found during the game.
    This action persists the changes to the character's state.
    
    IMPORTANT - CRITICAL WORKFLOW:
    1. ALWAYS call list_available_equipment() FIRST to see what items exist
    2. Use exact item_id from the list if possible
    3. Only create new items if ABSOLUTELY necessary for the story
    
    IMPORTANT - WHICH ID TO USE:
    - ALWAYS use the CATALOG ID (item_id) from equipment.yaml
    - CATALOG ID examples: "weapon_longsword", "armor_leather", "item_rope"
    - DO NOT use UUIDs (36-character strings like "a3f2c1b0-1234-5678-90ab-cdef12345678")
    - The system will automatically generate a unique UUID for each item instance
    
    WHEN NOT TO USE:
    - DO NOT use this for purchases - use `inventory_buy_item` instead
    
    Args:
        item_id (str): The CATALOG ID from equipment.yaml (e.g., 'weapon_longsword', 'armor_leather', 'item_rope').
                       This identifies WHAT the item is, not a specific instance.
        qty (int): The quantity of the item to add. Must be a positive integer. Default is 1.

    Returns:
        dict: A dictionary containing a success message and the updated inventory list.
    """

    try:
        if qty < 1:
            return {"error": "Quantity must be a positive integer."}

        log_debug(
            "Tool inventory_add_item called", 
            tool="inventory_add_item", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id, 
            qty=qty
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
        
        # Check if item exists in catalog
        if not ctx.deps.equipment_service.equipment_exists(item_id):
            # --- Hybrid Search for Suggestions ---
            # 1. Gather all valid item IDs and names
            all_equipment = ctx.deps.equipment_service.equipment_manager.get_all_equipment()
            valid_ids = []
            id_to_name = {}
            for category in all_equipment.values():
                for item in category:
                    valid_ids.append(item['id'])
                    id_to_name[item['id']] = item['name']
            
            # 2. Fuzzy Search (difflib) - Fast & Deterministic
            matches = difflib.get_close_matches(item_id.lower(), valid_ids, n=3, cutoff=0.6)
            
            suggestion_msg = ""
            if matches:
                suggestions = [f"'{m}' ({id_to_name.get(m, '?')})" for m in matches]
                suggestion_msg = f" Did you mean: {', '.join(suggestions)}?"
            else:
                # 3. Semantic Search (LLM) - Smart Fallback
                # Only use if fuzzy search failed completely to save latency
                try:
                    from back.agents.generic_agent import build_simple_gm_agent

                    # Build a concise context of available items description
                    # Limit to avoid huge context, maybe just names/descriptions?
                    # For now let's just use names for speed
                    catalog_str = ", ".join([f"{i['id']} ({i['name']})" for cat in all_equipment.values() for i in cat])
                    
                    agent = build_simple_gm_agent()
                    prompt = (
                        f"The user requested item ID '{item_id}' which does not exist. "
                        f"Here is the valid catalog: {catalog_str}. "
                        f"Find the single best match ID for '{item_id}' based on name or concept. "
                        f"Return ONLY the ID, nothing else. If no match, return 'None'."
                    )
                    
                    # Run generic agent
                    result_msg = await agent.run(prompt)
                    best_match = result_msg.data.strip()
                    
                    if best_match and best_match != 'None' and best_match in valid_ids:
                         suggestion_msg = f" Did you mean: '{best_match}' ({id_to_name.get(best_match, '?')})?"
                except Exception as e:
                    log_warning(f"Hybrid search generic agent failed: {e}")

            return {
                "error": f"Item '{item_id}' not found in catalog.{suggestion_msg} If this is a new custom item, use the appropriate creation tool: 'create_weapon', 'create_armor', or 'create_item' (for consumables/accessories).",
                "suggestion": "Use create_weapon, create_armor, or create_item to create the item first."
            }

        # Add item to inventory (this also saves the character)
        updated_character = await ctx.deps.equipment_service.add_item(
            ctx.deps.character_service.get_character(),
            item_id=item_id,
            quantity=qty
        )
        
        # Get updated inventory list
        inventory_items = ctx.deps.equipment_service.get_equipment_list(updated_character)
        
        return {
            "message": f"Added {qty} x {item_id}",
            "item_id": item_id,
            "qty": qty,
            "inventory": inventory_items
        }
        
    except Exception as e:
        log_warning(
            "Error in inventory_add_item",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to add item: {str(e)}"}


async def inventory_buy_item(
    ctx: RunContext[GameSessionContextProtocol], 
    item_id: str, 
    qty: int = 1
) -> dict:
    """
    Purchase an item and add it to the character's inventory.

    This tool handles item purchases by deducting the cost from the character's currency.
    It should be used when the player purchases something from a shop or merchant.
    The cost is automatically deducted from the character's currency.
    It automatically checks availability (canBuy), affordability and performs currency conversion if necessary.
    
    IMPORTANT - WHICH ID TO USE:
    - ALWAYS use the CATALOG ID (item_id) from equipment.yaml
    - CATALOG ID examples: "weapon_longsword", "armor_leather", "item_healing_potion"
    - DO NOT use UUIDs (36-character strings)
    - The system will automatically generate a unique UUID for the purchased item

    Args:
        item_id (str): The CATALOG ID from equipment.yaml (e.g., 'weapon_longsword', 'armor_leather').
                       This identifies WHAT to buy, not a specific instance.
        qty (int): The quantity of the item to purchase. Must be a positive integer. Default is 1.

    Returns:
        dict: A dictionary containing the transaction details, updated inventory, and remaining currency.
              Returns an error if the item is not found or funds are insufficient.
    """

    try:
        if qty < 1:
            return {"error": "Quantity must be a positive integer."}

        log_debug(
            "Tool inventory_buy_item called", 
            tool="inventory_buy_item", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id, 
            qty=qty
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
            
        # Get item details to check cost and availability
        item_data = ctx.deps.equipment_service.equipment_manager.get_equipment_by_id(item_id)
        if not item_data:
            # Re-use fuzzy/semantic logic could be good here too, but for buying let's stick to strict
            # or maybe just simple fuzzy
             # --- Hybrid Search for Suggestions (Simplified for Buy) ---
            all_equipment = ctx.deps.equipment_service.equipment_manager.get_all_equipment()
            valid_ids = [item['id'] for cat in all_equipment.values() for item in cat if item.get('can_buy', True)]
            matches = difflib.get_close_matches(item_id.lower(), valid_ids, n=1, cutoff=0.6)
            suggestion = f" Did you mean '{matches[0]}'?" if matches else ""
            return {"error": f"Item not found (or not for sale): {item_id}.{suggestion}"}
            
        # Check canBuy
        if not item_data.get('can_buy', True):
             return {"error": f"Item '{item_id}' is not available for purchase in shops."}

        cost_gold = item_data.get("cost_gold", 0) * qty
        cost_silver = item_data.get("cost_silver", 0) * qty
        cost_copper = item_data.get("cost_copper", 0) * qty
        
        # Get current character
        character = ctx.deps.character_service.get_character()
        
        # Check affordability
        if not character.equipment.can_afford(cost_gold, cost_silver, cost_copper):
            total_cost_copper = (cost_gold * 100) + (cost_silver * 10) + cost_copper
            current_copper = character.equipment.get_total_in_copper()
            return {
                "error": f"Insufficient funds. Cost: {cost_gold}G {cost_silver}S {cost_copper}C (Total: {total_cost_copper}C). Available: {current_copper}C",
                "transaction": "failed"
            }
            
        # Deduct currency
        if not character.equipment.deduct_currency(cost_gold, cost_silver, cost_copper):
             return {"error": "Transaction failed during currency deduction"}
             
        # Add item
        updated_character = await ctx.deps.equipment_service.add_item(
            character,
            item_id=item_id,
            quantity=qty
        )
        
        # Get updated inventory list
        inventory_items = ctx.deps.equipment_service.get_equipment_list(updated_character)
        
        return {
            "message": f"Purchased {qty} x {item_id} for {cost_gold}G {cost_silver}S {cost_copper}C",
            "inventory": inventory_items,
            "item": item_id,
            "quantity": qty,
            "transaction": {
                "item": item_id,
                "quantity": qty,
                "cost": {"gold": cost_gold, "silver": cost_silver, "copper": cost_copper},
                "currency_remaining": {
                    "gold": updated_character.gold,
                    "silver": updated_character.silver,
                    "copper": updated_character.copper
                }
            }
        }
        
    except Exception as e:
        log_warning(
            "Error in inventory_buy_item",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to buy item: {str(e)}"}


async def inventory_sell_item(
    ctx: RunContext[GameSessionContextProtocol], 
    item_id: str, 
    qty: int = 1
) -> dict:
    """
    Sell an item from the character's inventory for currency.

    This tool removes an item from the character's inventory and refunds 50% of its catalog cost 
    (Gold/Silver/Copper). It should be used when the player sells items to a shopkeeper or merchant.
    
    Logic:
    1. Validation: Checks if item exists and quantity is valid.
    2. Pricing: Looks up the base cost from the equipment catalog.
    3. Refund: Calculates 50% of the total value (rounding down).
    4. Transaction: Removes the item and adds the refund currency.

    Args:
        item_id (str): The ID (catalog ID, UUID, or name) of the item to sell.
        qty (int): The quantity of the item to sell. Must be a positive integer. Default is 1.

    Returns:
        dict: A dictionary containing the transaction details, refund amount, and updated status.
    """

    try:
        if qty < 1:
            return {"error": "Quantity must be a positive integer."}

        log_debug(
            "Tool inventory_sell_item called", 
            tool="inventory_sell_item", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id, 
            qty=qty
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
            
        # 1. Resolve item and check ownership
        # We need to find the item to know what it is (for price lookup) and if we have it
        character = ctx.deps.character_service.get_character()
        
        target_item = None
        target_list = None
        
        # Helper to find item details in inventory
        # We need the catalog ID to look up the original price, or use the item's stored cost
        # The service's remove_item handles removal by UUID or ID, but we need cost first.
        
        found_in_inventory = False
        item_catalog_id = None
        item_cost_gold = 0
        item_cost_silver = 0
        item_cost_copper = 0
        
        # Search in inventory
        all_lists = [character.equipment.weapons, character.equipment.armor, 
                     character.equipment.accessories, character.equipment.consumables]
        
        for lst in all_lists:
            for item in lst:
                # Match by UUID (exact instance) or Catalog ID or Name
                if item.id == item_id or item.item_id == item_id or item.name.lower() == item_id.lower():
                    target_item = item
                    found_in_inventory = True
                    break
            if found_in_inventory:
                break
                
        if not found_in_inventory:
             return {"error": f"Item '{item_id}' not found in inventory. Cannot sell what you don't have."}

        # 2. Determine Value
        # Prefer catalog price to avoid exploits with modified items, 
        # unless it's a unique item without catalog entry (rare).
        # We'll rely on the stored costs in the item instance first as they are copied from catalog on creation,
        # but catalog lookup is safer for "current market value".
        
        # Let's try to get fresh catalog data
        catalog_id = target_item.item_id
        catalog_item = ctx.deps.equipment_service.equipment_manager.get_equipment_by_id(catalog_id)
        
        if catalog_item:
            item_cost_gold = catalog_item.get('cost_gold', 0)
            item_cost_silver = catalog_item.get('cost_silver', 0)
            item_cost_copper = catalog_item.get('cost_copper', 0)
        else:
            # Fallback to stored item value if not in catalog (e.g. custom/unique item)
            item_cost_gold = target_item.cost_gold
            item_cost_silver = target_item.cost_silver
            item_cost_copper = target_item.cost_copper
            
        # 3. Calculate Total Value in Copper
        single_val_copper = (item_cost_gold * 100) + (item_cost_silver * 10) + item_cost_copper
        if single_val_copper == 0:
             return {
                 "error": f"Item '{target_item.name}' has no value and cannot be sold.",
                 "item": target_item.name
             }

        total_value_copper = single_val_copper * qty
        
        # 4. Apply Resale Factor (50%)
        refund_copper = int(total_value_copper * 0.5)
        
        if refund_copper == 0:
             return {
                 "error": f"Resale value of {qty} x {target_item.name} is too low (0 copper).",
                 "item": target_item.name
             }
             
        # Convert refund back to G/S/C
        refund_gold = refund_copper // 100
        rem = refund_copper % 100
        refund_silver = rem // 10
        refund_copper_final = rem % 10
        
        # 5. Execute Transaction
        # Remove item first (to ensure we have enough quantity)
        # remove_item handles the "not enough quantity" case?
        # Actually equipment_service.remove_item logically just decreases. 
        # But we should check quantity before transaction to be safe? 
        # target_item.quantity vs qty
        if target_item.quantity < qty:
             return {"error": f"Not enough items to sell. You have {target_item.quantity}, tried to sell {qty}."}

        # Remove
        await ctx.deps.equipment_service.remove_item(
            character,
            item_id=target_item.id, # Use UUID for precise removal
            quantity=qty
        )
        
        # Add Money
        await ctx.deps.character_service.add_currency(refund_gold, refund_silver, refund_copper_final)
        
        # Get updated inventory for display
        inventory_items = ctx.deps.equipment_service.get_equipment_list(character)
        
        formatted_refund = []
        if refund_gold > 0: formatted_refund.append(f"{refund_gold}G")
        if refund_silver > 0: formatted_refund.append(f"{refund_silver}S")
        if refund_copper_final > 0: formatted_refund.append(f"{refund_copper_final}C")
        refund_str = " ".join(formatted_refund) or "0C"
        
        return {
            "message": f"Sold {qty} x {target_item.name} for {refund_str}",
            "item_id": target_item.id,
            "qty": qty,
            "refund": {
                "gold": refund_gold,
                "silver": refund_silver,
                "copper": refund_copper_final
            },
            "inventory": inventory_items,
            "transaction": "success"
        }
        
    except Exception as e:
        log_warning(
            "Error in inventory_sell_item",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to sell item: {str(e)}"}

async def inventory_remove_item(ctx: RunContext[GameSessionContextProtocol], item_id: str, qty: int = 1) -> dict:
    """
    Remove an item from the character's inventory.

    This tool removes an item from the character's inventory.
    It should be used when an item is consumed, lost, sold (without price logic here), or given away.
    FOR CONSUMABLES (arrows, potions): Use `inventory_decrease_quantity` instead if you just want to use one unit.
    This action persists the changes to the character's state.

    Args:
        item_id (str): The unique identifier (catalog ID or instance UUID) of the item to remove.
        qty (int): The quantity of the item to remove. Must be a positive integer. Default is 1.

    Returns:
        dict: A dictionary containing a success message and the updated inventory list.
    """

    try:
        if qty < 1:
            return {"error": "Quantity must be a positive integer."}

        log_debug(
            "Tool inventory_remove_item called", 
            tool="inventory_remove_item", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id, 
            qty=qty
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
        
        # Get current character
        character = ctx.deps.character_service.get_character()
        
        # Resolve item_id if it's a name
        target_id = item_id
        # Simple check: if it doesn't look like a UUID (len 36), try to find by name or catalog_id
        if len(item_id) != 36:
            found_item = None
            all_items = ctx.deps.equipment_service.get_equipment_details(character)
            for item in all_items:
                # Match by UUID or Catalog ID
                if item.id == item_id or item.item_id == item_id:
                    found_item = item
                    break
            
            if found_item:
                target_id = found_item.id
            else:
                return {"error": f"Item '{item_id}' not found in inventory."}

        # Remove item (this also saves the character)
        updated_character = await ctx.deps.equipment_service.remove_item(
            character,
            item_id=target_id,
            quantity=qty
        )
        
        # Get updated inventory list
        inventory_items = ctx.deps.equipment_service.get_equipment_list(updated_character)
        
        return {
            "message": f"Removed {qty} x {item_id}",
            "item_id": item_id,
            "qty": qty,
            "inventory": inventory_items
        }
        
    except Exception as e:
        log_warning(
            "Error in inventory_remove_item",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to remove item: {str(e)}"}


async def list_available_equipment(ctx: RunContext[GameSessionContextProtocol], category: str = "all") -> dict:
    """
    List available equipment items by category.

    This tool retrieves a list of equipment items available in the game, filtered by category.
    It ONLY lists items that can be BOUGHT (canBuy=True).
    It should be used to check item availability, costs, and stats before making a purchase or rewarding loot.
    This does not modify any state.
    Use "all" to list everything, or specific categories like "weapon", "armor", "consumable", "quest".

    Args:
        category (str): The category to filter by. Options: "weapons", "armor", "accessories", "consumables", "all". Default is "all".

    Returns:
        dict: A dictionary containing the list of available items with their details (id, name, cost, description, stats).
    """

    try:
        log_debug(
            "Tool list_available_equipment called",
            tool="list_available_equipment",
            player_id=str(ctx.deps.character_id),
            category=category
        )
        
        if not ctx.deps.equipment_service:
            return {"error": "Equipment service not available"}
        
        # Get equipment manager from the service
        equipment_manager = ctx.deps.equipment_service.equipment_manager
        
        # Get all equipment organized by categories
        all_equipment = equipment_manager.get_all_equipment()
        
        # Normalize category input
        category_lower = category.lower().strip()
        
        # Filter by category if specified
        if category_lower == "all":
            categories_to_show = all_equipment
        elif category_lower in all_equipment:
            categories_to_show = {category_lower: all_equipment[category_lower]}
        else:
            return {
                "error": f"Invalid category: '{category}'. Valid options: weapons, armor, accessories, consumables, all"
            }
        
        # Format the response
        result = {
            "category_filter": category,
            "items": {}
        }
        
        for cat_name, items_list in categories_to_show.items():
            formatted_items = []
            for item in items_list:
                # -- FILTER: Only show items that are buyable --
                if not item.get("can_buy", True):
                    continue
                    
                formatted_items.append({
                    "item_id": item["id"],
                    "name": item["name"],
                    "cost": {
                        "gold": item.get("cost_gold", 0),
                        "silver": item.get("cost_silver", 0),
                        "copper": item.get("cost_copper", 0)
                    },
                    "description": item.get("description", "No description available"),
                    "weight": item.get("weight", 0),
                    # Include category-specific info
                    **({"damage": item["damage"]} if "damage" in item else {}),
                    **({"protection": item["protection"]} if "protection" in item else {}),
                    **({"range": item["range"]} if "range" in item else {})
                })
            
            result["items"][cat_name] = formatted_items
        
        # Add summary
        total_items = sum(len(items) for items in result["items"].values())
        result["summary"] = f"Found {total_items} items in {len(result['items'])} categories"
        
        return result
        
    except Exception as e:
        log_warning(
            "Error in list_available_equipment",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            category=category
        )
        return {"error": f"Failed to list equipment: {str(e)}"}



async def check_inventory_quantity(ctx: RunContext[GameSessionContextProtocol], item_id: str) -> dict:
    """
    Check the quantity of an item in the character's inventory.

    Args:
        item_id (str): The ID (catalog ID, UUID, or name) of the item to check.

    Returns:
        dict: A dictionary containing the quantity of the item.
    """

    try:
        log_debug(
            "Tool check_inventory_quantity called", 
            tool="check_inventory_quantity", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
        
        character = ctx.deps.character_service.get_character()
        
        # Helper to find quantity
        qty = 0
        all_lists = [character.equipment.weapons, character.equipment.armor, 
                     character.equipment.accessories, character.equipment.consumables]
        
        item_name = "Unknown"
        found = False
        
        for lst in all_lists:
            for item in lst:
                if item.id == item_id or item.item_id == item_id or item.name.lower() == item_id.lower():
                    qty += item.quantity
                    item_name = item.name
                    found = True
                    # Continue searching? If searching by name or catalog ID, we might have multiple stacks.
                    # If UUID, it's unique.
                    if len(item_id) == 36 and item.id == item_id:
                         break
            if found and len(item_id) == 36: # Break outer loop if UUID match found
                break

        return {
            "item_id": item_id,
            "name": item_name if found else "Unknown",
            "quantity": qty,
            "message": f"Character has {qty} x {item_name if found else item_id}"
        }
        
    except Exception as e:
        log_warning(
            "Error in check_inventory_quantity",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to check quantity: {str(e)}"}


async def inventory_decrease_quantity(ctx: RunContext[GameSessionContextProtocol], item_id: str, amount: int = 1) -> dict:
    """
    Decrease the quantity of an item in the inventory.

    Use this when the player uses up a consumable (arrow, potion) or loses some amount of a stackable item.
    If the quantity reaches 0, the item is removed from the inventory.
    Use this for consuming ammo or supplies.

    Args:
        item_id (str): The ID (catalog ID, UUID, or name) of the item to decrease.
        amount (int): The amount to decrease by. Default is 1.

    Returns:
        dict: A dictionary containing the updated inventory status.
    """

    try:
        if amount < 1:
            return {"error": "Amount must be a positive integer."}

        log_debug(
            "Tool inventory_decrease_quantity called", 
            tool="inventory_decrease_quantity", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id, 
            amount=amount
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
        
        character = ctx.deps.character_service.get_character()
        
        # Decrease quantity via service
        updated_character = await ctx.deps.equipment_service.decrease_item_quantity(
            character,
            item_id=item_id,
            amount=amount
        )
        
        # Get updated inventory list
        inventory_items = ctx.deps.equipment_service.get_equipment_list(updated_character)
        
        return {
            "message": f"Decreased {item_id} by {amount}",
            "inventory": inventory_items
        }
        
    except Exception as e:
        log_warning(
            "Error in inventory_decrease_quantity",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to decrease quantity: {str(e)}"}


async def inventory_increase_quantity(ctx: RunContext[GameSessionContextProtocol], item_id: str, amount: int = 1) -> dict:
    """
    Increase the quantity of an item in the inventory.

    Use this when the player finds more of an item they already have (e.g. arrows, coins).
    If the item is not found in the inventory, this tool does nothing (idempotent behavior).
    To add a NEW item to inventory, use inventory_add_item instead.

    Args:
        item_id (str): The ID (catalog ID, UUID, or name) of the item to increase.
        amount (int): The amount to increase by. Default is 1.

    Returns:
        dict: A dictionary containing the updated inventory status.
    """

    try:
        if amount < 1:
            return {"error": "Amount must be a positive integer."}

        log_debug(
            "Tool inventory_increase_quantity called", 
            tool="inventory_increase_quantity", 
            player_id=str(ctx.deps.character_id), 
            item_id=item_id, 
            amount=amount
        )
        
        if not ctx.deps.equipment_service or not ctx.deps.character_service:
            return {"error": "Equipment or character service not available"}
        
        character = ctx.deps.character_service.get_character()
        
        # Increase quantity via service
        updated_character = await ctx.deps.equipment_service.increase_item_quantity(
            character,
            item_id=item_id,
            amount=amount
        )
        
        # Get updated inventory list
        inventory_items = ctx.deps.equipment_service.get_equipment_list(updated_character)
        
        return {
            "message": f"Increased {item_id} by {amount}",
            "inventory": inventory_items
        }
        
    except Exception as e:
        log_warning(
            "Error in inventory_increase_quantity",
            error=str(e),
            character_id=str(ctx.deps.character_id),
            item_id=item_id
        )
        return {"error": f"Failed to increase quantity: {str(e)}"}


async def create_weapon(
    ctx: RunContext[GameSessionContextProtocol], 
    name: str, 
    damage: str,
    range: int = 0,
    description: str = "",
    cost_gold: int = 0,
    cost_silver: int = 0,
    cost_copper: int = 0,
    weight: float = 0.0,
    properties: str = None,
    quantity: int = 1,
    is_unique: bool = False
) -> dict:
    """
    Create a NEW custom WEAPON definition in the game database.
    
    This tool ONLY creates the item definition. It does NOT add it to the inventory.
    You MUST use `inventory_add_item` with the returned `item_id` to give it to the character.
    
    Use `is_unique=True` ONLY for truly unique, named, or legendary items (e.g., "Excalibur", "Amulet of Kings").
    Use `is_unique=False` for generic items, even if they are created for a specific scenario (e.g., "Rusty Key", "Healing Herb", "Iron Sword").
    
    Args:
        name (str): The display name (e.g., "Sword of Ancestors"). MUST be in ENGLISH.
        damage (str): Damage formula (e.g., "1d8+2", "2d6"). REQUIRED.
        range (int): Range in meters. 0 for melee. Default 0.
        description (str): Description text of item. MUST be in ENGLISH and must be at least 10 tokens long
        cost_gold (int): Gold cost.
        cost_silver (int): Silver cost.
        cost_copper (int): Copper cost.
        weight (float): Weight in kg.
        properties (str, optional): Special properties (e.g., "magical", "two-handed").
        quantity (int): Number to add (used for default stack size). Default 1.
        is_unique (bool): If True, the item is saved to unique_items.yaml and NOT the global catalog. Default False.

    Returns:
        dict: Success message and item_id.
    """

    try:
        log_debug("Tool create_weapon called", tool="create_weapon", player_id=str(ctx.deps.character_id), item_name=name, is_unique=is_unique)
        
        item_data = {
            "name": name,
            "damage": damage,
            "range": range,
            "description": description,
            "cost_gold": cost_gold,
            "cost_silver": cost_silver,
            "cost_copper": cost_copper,
            "weight": weight,
            "quantity": quantity
        }
        if properties: item_data["properties"] = properties

        # Created items are NOT buyable by default (they are quest items or loot)
        item_id = ctx.deps.equipment_service.create_item_definition(
            "weapon",
            item_data,
            is_unique=is_unique,
            can_buy=False
        )

        # Trigger background translation
        if ctx.deps.translation_agent:
            asyncio.create_task(ctx.deps.translation_agent.translate_item(item_id, name, description))
        
        return {
            "message": f"Weapon definition created. ID: {item_id}. Use inventory_add_item to add it to the inventory.",
            "item_id": item_id,
            "item_details": item_data
        }
    except Exception as e:
        log_warning("Error in create_weapon", error=str(e), character_id=str(ctx.deps.character_id), item_name=name)
        return {"error": f"Failed to create weapon: {str(e)}"}


async def create_armor(
    ctx: RunContext[GameSessionContextProtocol], 
    name: str, 
    protection: int,
    description: str = "",
    cost_gold: int = 0,
    cost_silver: int = 0,
    cost_copper: int = 0,
    weight: float = 0.0,
    properties: str = None,
    quantity: int = 1,
    is_unique: bool = False
) -> dict:
    """
    Create a NEW custom ARMOR definition in the game database.
    """


    """
    Create a NEW custom ARMOR definition in the game database.
    
    This tool ONLY creates the item definition. It does NOT add it to the inventory.
    You MUST use `inventory_add_item` with the returned `item_id` to give it to the character.
    
    Use `is_unique=True` ONLY for truly unique, named, or legendary items (e.g., "Dragon Scale Armor").
    Use `is_unique=False` for generic items, even if they are created for a specific scenario (e.g., "Guard Uniform", "Rusted Chainmail").

    Args:
        name (str): The display name. MUST be in ENGLISH.
        protection (int): Armor Class (AC) bonus or protection value. REQUIRED.
        description (str): Description text of item. MUST be in ENGLISH and must be at least 10 tokens long
        cost_gold (int): Gold cost.
        cost_silver (int): Silver cost.
        cost_copper (int): Copper cost.
        weight (float): Weight in kg.
        properties (str, optional): Special properties (e.g., "stealthy", "heavy").
        quantity (int): Number to add (used for default stack size). Default 1.
        is_unique (bool): If True, the item is saved to unique_items.yaml and NOT the global catalog. Default False.

    Returns:
        dict: Success message and item_id.
    """
    try:
        log_debug("Tool create_armor called", tool="create_armor", player_id=str(ctx.deps.character_id), item_name=name, is_unique=is_unique)
        
        item_data = {
            "name": name,
            "protection": protection,
            "description": description,
            "cost_gold": cost_gold,
            "cost_silver": cost_silver,
            "cost_copper": cost_copper,
            "weight": weight,
            "quantity": quantity
        }
        if properties: item_data["properties"] = properties

        # Created items are NOT buyable by default
        item_id = ctx.deps.equipment_service.create_item_definition(
            "armor",
            item_data,
            is_unique=is_unique,
            can_buy=False
        )

        # Trigger background translation
        if ctx.deps.translation_agent:
            asyncio.create_task(ctx.deps.translation_agent.translate_item(item_id, name, description))
        
        return {
            "message": f"Armor definition created. ID: {item_id}. Use inventory_add_item to add it to the inventory.",
            "item_id": item_id,
            "item_details": item_data
        }
    except Exception as e:
        log_warning("Error in create_armor", error=str(e), character_id=str(ctx.deps.character_id), item_name=name)
        return {"error": f"Failed to create armor: {str(e)}"}


async def create_item(
    ctx: RunContext[GameSessionContextProtocol], 
    name: str, 
    category: str, 
    description: str = "",
    cost_gold: int = 0,
    cost_silver: int = 0,
    cost_copper: int = 0,
    weight: float = 0.0,
    properties: str = None,
    quantity: int = 1,
    is_unique: bool = False
) -> dict:
    """
    Create a NEW custom ITEM definition (Consumable or Accessory) in the game database.
    
    This tool ONLY creates the item definition. It does NOT add it to the inventory.
    You MUST use `inventory_add_item` with the returned `item_id` to give it to the character.
    
    Use `is_unique=True` ONLY for truly unique, named, or legendary items (e.g., "Ring of Power").
    Use `is_unique=False` for generic items, even if they are created for a specific scenario (e.g., "Healing Potion", "Rope", "Torch").

    Args:
        name (str): The display name. MUST be in ENGLISH.
        category (str): MUST be 'consumable' or 'accessory'.
        description (str): Description text of item. MUST be in ENGLISH and must be at least 10 tokens long
        cost_gold (int): Gold cost.
        cost_silver (int): Silver cost.
        cost_copper (int): Copper cost.
        weight (float): Weight in kg.
        properties (str, optional): Special properties.
        quantity (int): Number to add (used for default stack size). Default 1.
        is_unique (bool): If True, the item is saved to unique_items.yaml and NOT the global catalog. Default False.

    Returns:
        dict: Success message and item_id.
    """

    try:
        log_debug("Tool create_item called", tool="create_item", player_id=str(ctx.deps.character_id), item_name=name, category=category, is_unique=is_unique)
        
        valid_categories = ['consumable', 'accessory']
        if category.lower() not in valid_categories:
            return {"error": f"Invalid category '{category}'. For weapons use create_weapon, for armor use create_armor. This tool only supports: {', '.join(valid_categories)}"}

        item_data = {
            "name": name,
            "description": description,
            "cost_gold": cost_gold,
            "cost_silver": cost_silver,
            "cost_copper": cost_copper,
            "weight": weight,
            "quantity": quantity
        }
        if properties: item_data["properties"] = properties

        # Created items are NOT buyable by default
        item_id = ctx.deps.equipment_service.create_item_definition(
            category.lower(),
            item_data,
            is_unique=is_unique,
            can_buy=False
        )

        # Trigger background translation
        if ctx.deps.translation_agent:
            asyncio.create_task(ctx.deps.translation_agent.translate_item(item_id, name, description))
        
        return {
            "message": f"Item definition created. ID: {item_id}. Use inventory_add_item to add it to the inventory.",
            "item_id": item_id,
            "item_details": item_data
        }
    except Exception as e:
        log_warning("Error in create_item", error=str(e), character_id=str(ctx.deps.character_id), item_name=name)
        return {"error": f"Failed to create item: {str(e)}"}

async def find_or_create_item_tool(
    ctx: RunContext[GameSessionContextProtocol],
    name: str,
    description: str,
    acquisition_type: Literal['GIVE', 'PURCHASE'] = 'GIVE'
) -> dict:
    """
    Finds an item by name and either gives it to the player or attempts a purchase.
    
    This tool is a high-level helper for the Oracle to handle item acquisition.
    It attempts to resolve the item name to a valid Catalog ID.
    
    Logic:
    1. Search for item by name (Exact -> Fuzzy).
    2. If NOT found, perform Semantic Search (LLM) to map generic terms (e.g., "Basic Sword") to Catalog IDs.
    3. If ID found -> Calls inventory_add_item or inventory_buy_item.
    4. If STILL NOT found:
       - If acquisition_type == 'GIVE': Creates a new "Quest Item" (Accessory) with the given name, then adds it.
       - If acquisition_type == 'PURCHASE': Returns failure (Cannot buy undefined items).

    Args:
        name (str): The name of the item to find or create (e.g., "Rusty Key", "Health Potion").
        description (str): A description for the item. MANDATORY. Use a concise, descriptive sentence.
        acquisition_type (Literal['GIVE', 'PURCHASE']): Whether the item is being given for free or purchased. Default 'GIVE'.

    Returns:
        dict: Result of the operation (success message, inventory update, or error).
    """

    try:
        log_debug(
            "Tool find_or_create_item_tool called", 
            tool="find_or_create_item_tool", 
            player_id=str(ctx.deps.character_id), 
            name=name,
            acquisition_type=acquisition_type,
            description=description
        )

        if not ctx.deps.equipment_service:
            return {"error": "Equipment service not available"}

        # 1. Try to find the item ID
        item_id = None
        
        # Simple search in all equipment
        all_equipment = ctx.deps.equipment_service.equipment_manager.get_all_equipment()
        candidates = []
        
        # Exact match on ID or Name
        for category in all_equipment.values():
            for item in category:
                if item['id'] == name or item['name'].lower() == name.lower():
                    item_id = item['id']
                    break
                # Collect for fuzzy
                candidates.append((item['id'], item['name']))
            if item_id: break
            
        # Fuzzy match if strict failed
        if not item_id:
            names = [c[1] for c in candidates]
            matches = difflib.get_close_matches(name, names, n=1, cutoff=0.7)
            if matches:
                # Find the ID for this name
                for c in candidates:
                    if c[1] == matches[0]:
                        item_id = c[0]
                        break
        
        # 3. Semantic Search Fallback (LLM)
        # If still not found, ask the LLM to map generic terms (e.g., "arme de base") to catalog IDs
        if not item_id:
            try:
                from back.agents.generic_agent import build_simple_gm_agent

                # Build catalog context (ID + Name)
                catalog_str = ", ".join([f"{i['id']} ({i['name']})" for cat in all_equipment.values() for i in cat])
                
                agent = build_simple_gm_agent()
                prompt = (
                    f"The user requested item '{name}' which does not exist in the exact catalog. "
                    f"Here is the valid catalog: {catalog_str}. "
                    f"Find the single BEST match ID for '{name}' based on functionality or concept. "
                    f"Example: 'arme de base' -> 'weapon_longsword' or 'weapon_dagger'. "
                    f"Return ONLY the ID, nothing else. If no reasonable match exists, return 'None'."
                )
                
                # Run generic agent
                result_msg = await agent.run(prompt)
                best_match = result_msg.data.strip()
                
                # Verify the prediction
                valid_ids = [c[0] for c in candidates]
                if best_match and best_match != 'None' and best_match in valid_ids:
                    log_debug(f"Semantic Search mapped '{name}' -> '{best_match}'", tool="find_or_create_item_tool")
                    item_id = best_match
            except Exception as e:
                log_warning(f"Semantic search failed in find_or_create_item_tool: {e}")
        
        # 2. Handle Found vs Not Found
        if item_id:
            if acquisition_type == 'PURCHASE':
                return await inventory_buy_item(ctx, item_id=item_id, qty=1)
            else:
                return await inventory_add_item(ctx, item_id=item_id, qty=1)
        else:
            # Item NOT found
            if acquisition_type == 'PURCHASE':
                return {
                    "error": f"Item '{name}' not found in catalog. Cannot purchase unknown items.", 
                    "suggestion": "Try a different name or 'GIVE' if it's a unique loot."
                }
            else:
                # GIVE -> Create on the fly
                log_debug(f"Item '{name}' not found. Creating as new Quest Item.", tool="find_or_create_item_tool")
                
                # Create generic accessory/quest item
                creation_result = await create_item(
                    ctx, 
                    name=name, 
                    category="accessory", 
                    description=description, 
                    weight=0.1, 
                    is_unique=False # Generic scenario item
                )
                
                if "error" in creation_result:
                    return creation_result
                    
                new_item_id = creation_result["item_id"]
                return await inventory_add_item(ctx, item_id=new_item_id, qty=1)

    except Exception as e:
        log_warning("Error in find_or_create_item_tool", error=str(e))
        return {"error": f"Operation failed: {str(e)}"}
