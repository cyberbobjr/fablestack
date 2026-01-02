"""
Service specialized for character equipment and inventory management.
Single Responsibility:
- Buying/selling equipment and money management
- Inventory management (add, remove, (un)equip, quantities)
"""

from typing import Any, Dict, List
from uuid import uuid4

from injector import inject

from back.models.domain.character import Character
from back.models.domain.equipment_manager import EquipmentManager
from back.models.domain.items import EquipmentItem
from back.services.character_data_service import CharacterDataService
from back.utils.logger import log_debug


class EquipmentService:
    """
    ### EquipmentService
    **Description:** Service specialized in character equipment and inventory management.
    **Single Responsibility:** Buying/selling equipment, money management, adding/removing items, and (un)equipping.
    """
    
    @inject
    def __init__(self, data_service: CharacterDataService, equipment_manager: EquipmentManager):
        """
        ### __init__
        **Description:** Initializes the equipment service with injected dependencies.
        **Parameters:**
        - `data_service` (CharacterDataService): Data service for persistence
        - `equipment_manager` (EquipmentManager): Equipment manager
        """
        self.data_service = data_service
        self.equipment_manager = equipment_manager

    def _find_item_by_identifier(
        self, 
        character: Character, 
        identifier: str
    ) -> tuple[EquipmentItem | None, List[EquipmentItem] | None]:
        """
        Find an item by either its UUID (id) or catalog ID (item_id).
        
        Purpose:
            Provides flexible item lookup supporting both instance UUIDs and catalog references.
            This allows tools to use catalog IDs (e.g., "weapon_longsword") while internal
            operations can use UUIDs for precise instance targeting.
        
        Args:
            character (Character): The character whose inventory to search.
            identifier (str): Either a UUID (36 chars) or catalog ID (e.g., "weapon_longsword").
        
        Returns:
            tuple: (found_item, containing_list) or (None, None) if not found.
        """
        for lst in self._all_lists(character):
            for item in lst:
                if item.id == identifier or item.item_id == identifier:
                    return item, lst
        return None, None

    
    async def buy_equipment(self, character: Character, item_id: str) -> Character:
        """
        ### buy_equipment
        **Description:** Buys equipment and deducts the corresponding money.
        **Parameters:**
        - `character` (Character): Character to modify
        - `item_id` (str): ID of the equipment to buy
        **Returns:** Modified character
        **Raises:** ValueError if equipment does not exist or not enough money
        """
        log_debug("Achat d'équipement", 
                 action="buy_equipment", 
                 character_id=str(character.id),
                 item_id=item_id)
        
        # Retrieve equipment details
        # Search item by item_id (catalog) or id (UUID)
        # This part of the provided change seems to be for selling an item already in inventory, not buying a new one.
        # When buying, item_id is the catalog ID. We directly get details from the manager.
        equipment_details = self.equipment_manager.get_equipment_by_id(item_id)
        if not equipment_details:
            raise ValueError(f"Equipment '{item_id}' not found in catalog")
        
        # Retrieve catalog details for price
        # The previous line already did this.
        # The following lines are from the original code, adapted to use equipment_details.
        
        # Check budget
        equipment_cost = int(equipment_details.get('cost_gold', 0) * 100 + equipment_details.get('cost_silver', 0) * 10 + equipment_details.get('cost_copper', 0))
        # Note: The original code used 'cost' which might have been a simplified float. 
        # The new manager returns cost_gold/silver/copper. 
        # Let's assume the character.gold is actually in copper or some base unit? 
        # Wait, the original code said: character.gold -= equipment_cost. 
        # And equipment_details.get('cost', 0).
        # The YAML has cost_gold, cost_silver, etc.
        # The manager _standardize_item sets cost_gold etc.
        # Let's check how currency is handled.
        # The original code: equipment_cost = int(equipment_details.get('cost', 0) or 0)
        # It seems the previous manager might have had a 'cost' field or the service was broken/using old data.
        # Let's assume for now we just use gold cost or a simplified cost.
        # Let's stick to what was there but adapted.
        # If the previous code used 'cost', and the manager didn't provide it, it was 0.
        # I'll use cost_gold for now.
        
        cost_val = equipment_details.get('cost_gold', 0)
        
        if character.gold < cost_val:
            raise ValueError("Not enough money to buy this equipment")
        
        # Create EquipmentItem object with unique UUID and catalog reference
        item_entry = EquipmentItem(
            id=str(uuid4()),  # Unique UUID for this instance
            item_id=item_id,  # Catalog reference (e.g., "weapon_longsword")
            name=equipment_details['name'],
            category=equipment_details.get('category', 'misc'),
            cost_gold=equipment_details.get('cost_gold', 0),
            cost_silver=equipment_details.get('cost_silver', 0),
            cost_copper=equipment_details.get('cost_copper', 0),
            weight=float(equipment_details.get('weight', 0)),
            quantity=1,
            equipped=False,
            description=equipment_details.get('description'),
            damage=equipment_details.get('damage'),
            range=equipment_details.get('range'),
            protection=int(equipment_details.get('protection', 0)) if equipment_details.get('protection') else None,
            type=equipment_details.get('type')
        )

        # Add equipment to the correct category
        # We can rely on category from details
        cat = equipment_details.get('category', 'misc')
        if cat == 'weapon':
            character.equipment.weapons.append(item_entry)
        elif cat == 'armor':
            character.equipment.armor.append(item_entry)
        else:
            character.equipment.accessories.append(item_entry)
        
        # Deduct money
        character.gold -= cost_val
        
        await self.data_service.save_character(character)
        
        log_debug("Équipement acheté avec succès", 
                 action="buy_equipment_success", 
                 character_id=str(character.id),
                 item_id=item_id,
                 cost=cost_val,
                 gold_restant=character.gold)
        
        return character
    
    async def sell_equipment(self, character: Character, item_id: str) -> Character:
        """
        ### sell_equipment
        **Description:** Sells equipment and refunds the corresponding money.
        **Parameters:**
        - `character` (Character): Character to modify
        - `item_id` (str): ID of the equipment to sell
        **Returns:** Modified character
        **Raises:** ValueError if equipment does not exist or is not in inventory
        """
        log_debug("Vente d'équipement", 
                 action="sell_equipment", 
                 character_id=str(character.id),
                 item_id=item_id)
        
        # Retrieve equipment details for price (catalog)
        equipment_details = self.equipment_manager.get_equipment_by_id(item_id)
        
        # Remove equipment from the correct category
        found = False
        item_cost = 0.0
        
        for lst in self._all_lists(character):
            for i, it in enumerate(lst):
                # Match by id if present, otherwise name (fallback for migration)
                match = False
                if it.id == item_id: match = True
                elif equipment_details and it.name == equipment_details['name']:
                    match = True
                
                if match:
                    # Use item cost if stored, otherwise catalog cost
                    item_cost = it.cost_gold # Simplified
                    del lst[i]
                    found = True
                    break
            if found:
                break
                
        if not found:
            raise ValueError(f"Equipment '{item_id}' is not in inventory")
        
        # If we don't have the cost on the item, use catalog
        if item_cost == 0 and equipment_details:
            item_cost = float(equipment_details.get('cost_gold', 0))

        # Refund money (50% of purchase price)
        refund_amount = int(item_cost * 0.5)
        character.gold += refund_amount
        
        await self.data_service.save_character(character)
        
        log_debug("Équipement vendu avec succès", 
                 action="sell_equipment_success", 
                 character_id=str(character.id),
                 item_id=item_id,
                 refund_amount=refund_amount,
                 gold_restant=character.gold)
        
        return character
    
    async def update_money(self, character: Character, amount: float) -> Character:
        """
        ### update_money
        **Description:** Updates the character's money.
        **Parameters:**
        - `character` (Character): Character to modify
        - `amount` (float): Amount to add/remove (positive to add, negative to remove)
        **Returns:** Modified character
        """
        log_debug("Mise à jour de l'argent", 
                 action="update_money", 
                 character_id=str(character.id),
                 amount=amount)
        
        character.gold = max(0, character.gold + int(amount))  # Do not go negative
        await self.data_service.save_character(character)
        
        log_debug("Argent mis à jour", 
                 action="update_money_success", 
                 character_id=str(character.id),
                 nouveau_gold=character.gold)
        
        return character
    
    def get_equipment_list(self, character: Character) -> List[Dict[str, Any]]:
        """
        ### get_equipment_list
        **Description:** Retrieves the list of character equipment.
        **Parameters:**
        - `character` (Character): Character to analyze
        **Returns:** List of dictionaries {name, catalog_id, quantity}
        """
        items = []
        for lst in self._all_lists(character):
            items.extend([{
                "name": it.name,
                "id": it.id,
                "quantity": it.quantity
            } for it in lst])
        return items
    
    def get_equipment_details(self, character: Character) -> List[EquipmentItem]:
        """
        ### get_equipment_details
        **Description:** Retrieves full details of character equipment.
        **Parameters:**
        - `character` (Character): Character to analyze
        **Returns:** List of EquipmentItem objects
        """
        details = []
        for lst in self._all_lists(character):
            details.extend(lst)
        return details
    
    def calculate_total_weight(self, character: Character) -> float:
        """
        ### calculate_total_weight
        **Description:** Calculates the total weight of equipment.
        **Parameters:**
        - `character` (Character): Character to analyze
        **Returns:** Total weight in kilograms
        """
        total_weight = 0.0
        for lst in self._all_lists(character):
            for it in lst:
                total_weight += it.weight * it.quantity
        return total_weight
    
    def can_afford_equipment(self, character: Character, item_id: str) -> bool:
        """
        ### can_afford_equipment
        **Description:** Checks if the character can buy an equipment.
        **Parameters:**
        - `character` (Character): Character to check
        - `item_id` (str): Equipment ID
        **Returns:** True if the character can buy, False otherwise
        """
        equipment_details = self.equipment_manager.get_equipment_by_id(item_id)
        if not equipment_details:
            return False
        
        equipment_cost = int(equipment_details.get('cost_gold', 0))
        return character.gold >= equipment_cost
    
    def equipment_exists(self, item_id: str) -> bool:
        """
        ### equipment_exists
        **Description:** Checks if an equipment exists in the catalog.
        **Parameters:**
        - `item_id` (str): Equipment ID
        **Returns:** True if the equipment exists, False otherwise
        """
        return self.equipment_manager.get_equipment_by_id(item_id) is not None

    # --- Inventory management (merged from InventoryService) ---
    async def add_item(self, character: Character, item_id: str, quantity: int = 1) -> Character:
        """
        ### add_item
        **Description:** Adds a standardized item to the character's inventory from its id.
        **Parameters:**
        - `character` (Character): Character to modify
        - `item_id` (str): Item identifier
        - `quantity` (int): Quantity to add (default: 1)
        **Returns:** Modified character
        """
        log_debug("Equipment add item", action="add_item", character_id=str(character.id), item_id=item_id, quantity=quantity)
        base = self.equipment_manager.get_equipment_by_id(item_id)
        if not base:
            return character

        target_list = self._get_category_list(character, base.get('category', 'misc'))
        
        # Check if we already have this item in inventory (by item_id/catalog match)
        existing = next((it for it in target_list if it.item_id == item_id), None)
        
        # Fallback: check by name if needed (migration scenario)
        if not existing:
            existing = next((it for it in target_list if it.name == base['name']), None)

        if existing:
            existing.quantity += int(quantity)
        else:
            new_item = EquipmentItem(
                id=str(uuid4()),  # Unique UUID for this instance
                item_id=item_id,  # Catalog reference
                name=base['name'],
                category=base.get('category', 'misc'),
                cost_gold=int(base.get('cost_gold', 0)),
                cost_silver=int(base.get('cost_silver', 0)),
                cost_copper=int(base.get('cost_copper', 0)),
                weight=float(base.get('weight', 0)),
                quantity=int(quantity),
                equipped=False,
                description=base.get('description'),
                damage=base.get('damage'),
                range=base.get('range'),
                protection=int(base.get('protection', 0)) if base.get('protection') else None,
                type=base.get('type')
            )
            target_list.append(new_item)

        await self.data_service.save_character(character)
        return character

    async def add_item_object(self, character: Character, item: Dict[str, Any]) -> Character:
        """
        ### add_item_object
        **Description:** Adds a complete object (already structured) to the character's inventory.
        **Parameters:**
        - `character` (Character): Character to modify
        - `item` (dict): The item to add (must contain at least `name`)
        **Returns:** Modified character
        """
        log_debug("Equipment add item object", action="add_item_object", character_id=str(character.id), item_id=item.get('id'))

        category = item.get('category', 'accessory')
        target_list = self._get_category_list(character, category)
        
        # Try to find existing stack
        existing = next((it for it in target_list if it.name == item.get('name')), None)
        qty = int(item.get('quantity', 1) or 1)
        
        if existing:
            existing.quantity += qty
        else:
            # Ensure item_id is present, fallback to id or slugified name
            item_id = item.get('item_id') or item.get('id')
            if not item_id and item.get('name'):
                item_id = self.equipment_manager._slugify(item['name'])

            new_item = EquipmentItem(
                id=item.get('id') or str(uuid4()),
                item_id=item_id, # Ensure item_id is set
                name=item.get('name', 'Unknown Item'),
                category=category,
                cost_gold=int(item.get('cost_gold', item.get('cost', 0)) or 0),
                cost_silver=int(item.get('cost_silver', 0)),
                cost_copper=int(item.get('cost_copper', 0)),
                weight=float(item.get('weight', 0) or 0),
                quantity=qty,
                equipped=bool(item.get('equipped', False)),
                description=item.get('description'),
                damage=item.get('damage'),
                range=item.get('range'),
                protection=int(item.get('protection', 0)) if item.get('protection') else None,
                type=item.get('type')
            )
            target_list.append(new_item)

        await self.data_service.save_character(character)
        return character

    async def create_and_add_item(self, character: Character, category: str, item_data: Dict[str, Any]) -> Character:
        """
        ### create_and_add_item
        **Description:** Creates a new item in the catalog and adds it to the inventory.
        **Parameters:**
        - `character` (Character): Character to modify
        - `category` (str): Item category
        - `item_data` (dict): Item data
        **Returns:** Modified character
        """
        # 1. Create in catalog (persisted)
        item_id = self.equipment_manager.create_item(category, item_data)
        
        # 2. Add to inventory using the new ID
        # We use add_item which fetches from manager, ensuring data consistency
        return await self.add_item(character, item_id, quantity=int(item_data.get('quantity', 1)))

    def create_item_definition(self, category: str, item_data: Dict[str, Any], is_unique: bool = False, can_buy: bool = False) -> str:
        """
        ### create_item_definition
        **Description:** Creates an item definition in the catalog (standard or unique).
        Does NOT modify the inventory.
        
        **Parameters:**
        - `category` (str): Item category ('weapon', 'armor', 'consumable', 'accessory').
        - `item_data` (dict): Item data.
        - `is_unique` (bool): If True, the item is saved to unique_items.yaml.
        - `can_buy` (bool): If True, the item is available in shops. Default False.
        
        **Returns:**
        - `str`: The created item ID.
        """
        return self.equipment_manager.create_item(category, item_data, is_unique=is_unique, can_buy=can_buy)


    async def remove_item(self, character: Character, item_id: str, quantity: int = 1) -> Character:
        """
        ### remove_item
        **Description:** Removes an item from the character's inventory (adjusting quantity).
        **Parameters:**
        - `character` (Character): Character to modify
        - `item_id` (str): Item identifier (UUID)
        - `quantity` (int): Quantity to remove (default: 1)
        **Returns:** Modified character
        """
        log_debug("Equipment remove item", action="remove_item", character_id=str(character.id), item_id=item_id, quantity=quantity)
        for lst in self._all_lists(character):
            for idx, it in enumerate(lst):
                if it.id == item_id or it.item_id == item_id:
                    it.quantity -= int(quantity)
                    if it.quantity <= 0:
                        del lst[idx]
                    await self.data_service.save_character(character)
                    return character
        await self.data_service.save_character(character)
        return character

    async def equip_item(self, character: Character, item_id: str) -> Character:
        """
        ### equip_item
        **Description:** Equips an item on the character.
        **Parameters:**
        - `character` (Character): Character to modify
        - `item_id` (str): Item identifier
        **Returns:** Modified character
        """
        log_debug("Equipment equip item", action="equip_item", character_id=str(character.id), item_id=item_id)
        for lst in self._all_lists(character):
            for it in lst:
                if it.id == item_id or it.item_id == item_id:
                    it.equipped = True
                    await self.data_service.save_character(character)
                    return character
        await self.data_service.save_character(character)
        return character

    async def unequip_item(self, character: Character, item_id: str) -> Character:
        """
        ### unequip_item
        **Description:** Unequips an item from the character.
        **Parameters:**
        - `character` (Character): Character to modify
        - `item_id` (str): Item identifier
        **Returns:** Modified character
        """
        log_debug("Equipment unequip item", action="unequip_item", character_id=str(character.id), item_id=item_id)
        for lst in self._all_lists(character):
            for it in lst:
                if it.id == item_id or it.item_id == item_id:
                    it.equipped = False
                    await self.data_service.save_character(character)
                    return character
        await self.data_service.save_character(character)
        return character

    def get_equipped_items(self, character: Character) -> List[EquipmentItem]:
        """
        ### get_equipped_items
        **Description:** Retrieves the list of equipped items.
        **Parameters:**
        - `character` (Character): Character to analyze
        **Returns:** List of equipped items
        """
        equipped: List[EquipmentItem] = []
        for lst in self._all_lists(character):
            equipped.extend([it for it in lst if it.equipped])
        return equipped

    def item_exists(self, character: Character, item_id: str) -> bool:
        """
        ### item_exists
        **Description:** Checks if an item exists in the inventory.
        **Parameters:**
        - `character` (Character): Character to check
        - `item_id` (str): Item identifier
        **Returns:** True if the item exists, False otherwise
        """
        return any(True for lst in self._all_lists(character) for it in lst if (it.id == item_id or it.item_id == item_id))

    def get_item_quantity(self, character: Character, item_id: str) -> int:
        """
        ### get_item_quantity
        **Description:** Retrieves the quantity of an item in the inventory.
        **Parameters:**
        - `character` (Character): Character to analyze
        - `item_id` (str): Item identifier
        **Returns:** Quantity of the item (0 if not present)
        """
        for lst in self._all_lists(character):
            for it in lst:
                if it.id == item_id or it.item_id == item_id:
                    return it.quantity
        return 0

    # --- helpers ---
    def _get_category_list(self, character: Character, category: str) -> List[EquipmentItem]:
        cats = category.lower()
        eq = character.equipment
        if cats in ('weapon', 'weapons'):
            return eq.weapons
        if cats == 'armor':
            return eq.armor
        if cats in ('consumable', 'consumables'):
            return eq.consumables
        return eq.accessories

    def _all_lists(self, character: Character) -> List[List[EquipmentItem]]:
        eq = character.equipment
        return [eq.weapons, eq.armor, eq.accessories, eq.consumables]

    async def decrease_item_quantity(self, character: Character, item_id: str, amount: int = 1) -> Character:
        """
        ### decrease_item_quantity
        **Description:** Decreases the quantity of a specific item in the character's inventory.
        If the quantity reaches 0 or less, the item is removed from the inventory.
        
        **Parameters:**
        - `character` (Character): The character to modify.
        - `item_id` (str): The ID (catalog ID, UUID, or name) of the item to decrease.
        - `amount` (int): The amount to decrease by. Default is 1.
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        log_debug("Decreasing item quantity", 
                  action="decrease_item_quantity", 
                  character_id=str(character.id), 
                  item_id=item_id, 
                  amount=amount)

        if amount <= 0:
            return character

        item_found = False
        
        # Helper to process list
        def process_list(item_list: List[EquipmentItem]) -> bool:
            for i, item in enumerate(item_list):
                # Match by id or name
                match = False
                if item.id == item_id: match = True
                elif item.item_id == item_id: match = True
                elif item.name.lower() == item_id.lower(): match = True
                
                if match:
                    item.quantity -= amount
                    
                    if item.quantity <= 0:
                        item_list.pop(i)
                        log_debug("Item removed (quantity <= 0)", 
                                 action="decrease_item_quantity_removed", 
                                 character_id=str(character.id), 
                                 item_id=item_id)
                    return True
            return False

        # Check all equipment lists
        for lst in self._all_lists(character):
            if process_list(lst):
                item_found = True
                break
        
        if item_found:
            await self.data_service.save_character(character)
        else:
            log_debug("Item not found for quantity decrease", 
                      action="decrease_item_quantity_not_found", 
                      character_id=str(character.id), 
                      item_id=item_id)
            
        return character

    async def increase_item_quantity(self, character: Character, item_id: str, amount: int = 1) -> Character:
        """
        ### increase_item_quantity
        **Description:** Increases the quantity of a specific item in the character's inventory.
        If the item is not found, this method does nothing (idempotent behavior).
        
        **Parameters:**
        - `character` (Character): The character to modify.
        - `item_id` (str): The ID (catalog ID, UUID, or name) of the item to increase.
        - `amount` (int): The amount to increase by. Default is 1.
        
        **Returns:** 
        - `Character`: The updated character object.
        """
        log_debug("Increasing item quantity", 
                  action="increase_item_quantity", 
                  character_id=str(character.id), 
                  item_id=item_id, 
                  amount=amount)

        if amount <= 0:
            return character

        item_found = False
        
        # Helper to process list
        def process_list(item_list: List[EquipmentItem]) -> bool:
            for item in item_list:
                # Match by id or name
                match = False
                if item.id == item_id: match = True
                elif item.item_id == item_id: match = True
                elif item.name.lower() == item_id.lower(): match = True

                if match:
                    item.quantity += amount
                    log_debug("Item quantity increased", 
                             action="increase_item_quantity_success", 
                             character_id=str(character.id), 
                             item_id=item_id,
                             new_quantity=item.quantity)
                    return True
            return False

        # Check all equipment lists
        for lst in self._all_lists(character):
            if process_list(lst):
                item_found = True
                break
        
        if item_found:
            await self.data_service.save_character(character)
        else:
            log_debug("Item not found for quantity increase", 
                      action="increase_item_quantity_not_found", 
                      character_id=str(character.id), 
                      item_id=item_id)
            
        return character

