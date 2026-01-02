
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from back.models.domain.character import (CombatStats, Equipment, Skills,
                                          Spells, Stats)
from back.models.domain.combat_state import (AttackResult, Combatant,
                                             CombatantType, CombatState)
from back.models.domain.items import EquipmentItem

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

from back.models.domain.equipment_manager import EquipmentManager
from back.models.domain.npc import NPC
from back.models.domain.payloads import CombatIntentPayload
from back.models.service.dtos import CombatSummary, ParticipantSummary
from back.services.character_data_service import CharacterDataService
from back.services.character_service import CharacterService
from back.services.races_data_service import RacesDataService
from back.utils.dice import roll_dice
from back.utils.logger import log_debug, log_error


class CombatService:
    def __init__(self, races_data_service: RacesDataService, character_data_service: CharacterDataService):
        """
        Initializes the CombatService.

        Purpose:
            Prepares the combat service for managing combat encounters.
            This service handles all combat-related operations including participant
            management, attack resolution, damage application, and turn progression.
        """
        self.equipment_manager = EquipmentManager()
        self.races_data_service = races_data_service
        self.character_data_service = character_data_service


    def start_combat(self, intent: CombatIntentPayload, session_service: 'GameSessionService') -> CombatState:
        """
        Initializes a new combat state with the given intent.

        Purpose:
            Creates a new combat session, generates participants (including NPCs with default equipment),
            and rolls initial initiative.

        Args:
            intent (CombatIntentPayload): The intent payload containing combat details and enemies.
            session_service (GameSessionService): The GameSessionService instance to access player character data.

        Returns:
            CombatState: The newly created and initialized combat state.
        """
        participants = []
        
        # 1. Add Enemies from Intent
        for enemy_intent in intent.enemies_detected:
            # Generate NPC with equipment based on metadata (name, archetype, etc.)
            npc_ref = self._create_npc_with_equipment(
                enemy_intent.name, 
                enemy_intent.model_dump()
            )
            
            combatant = Combatant(
                id=uuid4(),
                name=enemy_intent.name,
                type=CombatantType.NPC,
                current_hit_points=npc_ref.combat_stats.current_hit_points,
                max_hit_points=npc_ref.combat_stats.max_hit_points,
                armor_class=npc_ref.combat_stats.armor_class,
                initiative_roll=0, # Rolled later
                npc_ref=npc_ref
            )
            participants.append(combatant)

        # 2. Add Player (Mandatory)
        character = session_service.character_service.get_character()
        if character:
            player_combatant = Combatant(
                id=uuid4(),
                name=character.name,
                type=CombatantType.PLAYER,
                current_hit_points=character.combat_stats.current_hit_points,
                max_hit_points=character.combat_stats.max_hit_points,
                armor_class=character.combat_stats.armor_class,
                initiative_roll=0,
                character_ref=character
            )
            participants.append(player_combatant)

        state = CombatState(
            participants=participants,
            is_active=True,
            log=["Combat started."]
        )
        
        # Auto-roll initiative
        state = self.roll_initiative(state)
        
        return state

    def _create_npc_with_equipment(self, name: str, data: Dict[str, Any]) -> NPC:
        """
        Creates an NPC and assigns default equipment based on archetype/data.

        Purpose:
            Generates a fully populated NPC object with stats and equipment suitable for combat,
            handling cases where explicit NPC data is missing.

        Args:
            name (str): The name of the NPC.
            data (Dict[str, Any]): The raw data dictionary for the NPC.

        Returns:
            NPC: The constructed NPC object with equipment.
        """
        archetype = data.get('archetype', 'Generic Enemy')
        
        # Default stats
        stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
        
        # Default equipment generation logic
        equipment = Equipment()
        
        # Logic to assign weapons based on race configuration
        # We try to find a matching race by name or ID in the archetype string
        # This is a heuristic, but it works for now
        
        # Get all combatant races to check against
        # We use injected RacesDataService
        races_service = self.races_data_service
        
        found_race = None
        # Try to find race in name or archetype
        search_term = (name + " " + archetype).lower()
        
        for race in races_service.get_all_races():
            if race.id.lower() in search_term or race.name.lower() in search_term:
                found_race = race
                break
        
        equipment_assigned = False
        if found_race and found_race.default_equipment:
            for item_entry in found_race.default_equipment:
                item_id = item_entry
                if isinstance(item_entry, list):
                    item_id = random.choice(item_entry)
                
                # Determine category based on item_id prefix (heuristic)
                category = "weapons"
                if "armor" in item_id:
                    category = "armor"
                elif "shield" in item_id:
                    category = "armor"
                
                self._add_item_to_equipment(equipment, item_id, category)
            equipment_assigned = True
            
        if not equipment_assigned:
            # Fallback weapon if no specific configuration found
            self._add_item_to_equipment(equipment, "weapon_natural", "weapons")

        return NPC(
            name=name,
            archetype=archetype,
            stats=stats,
            skills=Skills(),
            equipment=equipment,
            combat_stats=CombatStats(
                max_hit_points=data.get('max_hp', 10), 
                current_hit_points=data.get('hp', 10), 
                armor_class=data.get('ac', 10), 
                attack_bonus=data.get('attack_bonus', 2)
            ),
            spells=Spells()
        )

    def _add_item_to_equipment(self, equipment: Equipment, item_id: str, category_list: str):
        item_data = self.equipment_manager.get_equipment_by_id(item_id)
        if item_data:
            item = self._dict_to_equipment_item(item_data)
            if category_list == "weapons":
                equipment.weapons.append(item)
            elif category_list == "armor":
                equipment.armor.append(item)

    def _dict_to_equipment_item(self, data: Dict[str, Any]) -> EquipmentItem:
         return EquipmentItem(
            id=str(uuid4()),  # UUID unique pour cette instance
            item_id=data.get('id', data['name'].lower().replace(' ', '_')),  # Référence catalogue ou fallback
            name=data['name'],
            category=data.get('category', 'misc'),
            cost_gold=data.get('cost_gold', 0),
            cost_silver=data.get('cost_silver', 0),
            cost_copper=data.get('cost_copper', 0),
            weight=float(data.get('weight', 0)),
            quantity=1,
            equipped=True,
            damage=data.get('damage'),
            range=data.get('range'),
            protection=int(data.get('protection', 0)) if data.get('protection') else None,
            type=data.get('type')
        )

    def roll_initiative(self, state: CombatState) -> CombatState:
        """
        Rolls initiative for all participants and sets the turn order.

        Purpose:
            Calculates initiative for every participant based on their stats and a d20 roll,
            then sorts them to determine the turn order.

        Args:
            state (CombatState): The current combat state.

        Returns:
            CombatState: The updated combat state with assigned initiative rolls and turn order.
        """
        for p in state.participants:
            # Get initiative bonus
            bonus = 0
            if p.character_ref:
                bonus = p.character_ref.calculate_initiative()
            elif p.npc_ref:
                # Simplified NPC initiative (usually just Dex mod, here 0 or from data)
                bonus = 0 
            
            roll = random.randint(1, 20)
            total = roll + bonus
            p.initiative_roll = total
            state.add_log_entry(f"{p.name} rolled {total} ({roll}+{bonus}) for initiative.")

        # Sort participants by initiative (descending)
        sorted_participants = sorted(state.participants, key=lambda p: p.initiative_roll, reverse=True)
        state.turn_order = [p.id for p in sorted_participants]
        
        if state.turn_order:
            state.current_turn_combatant_id = state.turn_order[0]
            
        return state

    async def execute_attack(self, state: CombatState, attacker_id: str, target_id: str, attack_modifier: int = 0, advantage: bool = False) -> AttackResult:
        """
        Executes a full attack sequence between two combatants.

        Purpose:
            Handles the mechanics of an attack: validating participants, calculating attack rolls,
            determining hits/misses/crits, rolling damage, and applying it to the target.

        Args:
            state (CombatState): The current combat state.
            attacker_id (str): The UUID string of the attacking combatant.
            target_id (str): The UUID string of the target combatant.
            attack_modifier (int): Bonus/penalty to the attack roll (default 0).
            advantage (bool): If True, roll twice and take the higher value (default False).

        Returns:
            AttackResult: Detailed outcome of the attack.
        """
        # Default error result wrapper
        def error_result(msg: str) -> AttackResult:
            return AttackResult(
                attacker_name="Unknown", target_name="Unknown", weapon_name="None",
                attack_roll=0, attack_bonus=0, target_ac=0, is_hit=False, is_crit=False,
                damage=0, is_fatal=False, message=msg
            )

        try:
            attacker_uuid = UUID(attacker_id)
            target_uuid = UUID(target_id)
        except ValueError:
            return error_result("Invalid ID format.")

        attacker = state.get_combatant(attacker_uuid)
        target = state.get_combatant(target_uuid)

        if not attacker or not target:
            return error_result("Attacker or Target not found.")

        if not attacker.is_alive():
            return error_result(f"{attacker.name} is unconscious and cannot attack.")

        # 1. Get Weapon and Bonuses
        weapon = self._get_equipped_weapon(attacker)
        attack_bonus = self._get_attack_bonus(attacker)
        
        weapon_name = weapon.get("item_id", "unarmed_strike")
        damage_dice = weapon.get("damage", "1")

        # 2. Attack Roll (Advantage Logic)
        roll_1 = random.randint(1, 20)
        if advantage:
            roll_2 = random.randint(1, 20)
            d20 = max(roll_1, roll_2)
            log_debug(f"Advantage Roll: {roll_1}, {roll_2} -> Keeping {d20}")
        else:
            d20 = roll_1

        # Apply specific modifier
        total_attack = d20 + attack_bonus + attack_modifier
        
        is_crit = d20 == 20
        is_auto_miss = d20 == 1
        
        # 3. Resolve Hit
        hits = (total_attack >= target.armor_class and not is_auto_miss) or is_crit
        
        total_damage = 0
        is_fatal = False
        result_msg = ""

        if hits:
            # 4. Roll Damage
            damage = roll_dice(damage_dice)
            if is_crit:
                damage += roll_dice(damage_dice) # Simple crit: roll twice
            
            # Add ability mod to damage (simplified: same as attack bonus for now, or 0)
            damage_mod = attack_bonus # Often Str/Dex mod is added
            total_damage = max(1, damage + damage_mod)
            
            # 5. Apply Damage
            await self.apply_direct_damage(state, target_id, total_damage, is_attack=True)
            
            prefix = "Critical Hit! " if is_crit else "Hit! "
            
            if not target.is_alive():
                is_fatal = True
                result_msg = f"{prefix}{attacker.name} deals {total_damage} damage to {target.name} using {weapon_name}. Target defeated!"
            else:
                result_msg = f"{prefix}{attacker.name} deals {total_damage} damage to {target.name} using {weapon_name}."
        else:
            result_msg = f"Miss! {attacker.name} missed {target.name}."
            state.add_log_entry(f"{attacker.name} missed {target.name} with {weapon_name} (Roll: {total_attack} vs AC {target.armor_class}).")

        return AttackResult(
            attacker_name=attacker.name,
            target_name=target.name,
            weapon_name=weapon_name,
            attack_roll=d20,
            attack_bonus=attack_bonus,
            target_ac=target.armor_class,
            is_hit=hits,
            is_crit=is_crit,
            damage=total_damage,
            is_fatal=is_fatal,
            message=result_msg
        )

    def _get_equipped_weapon(self, combatant: Combatant) -> Dict[str, Any]:
        """
        Retrieves the equipped weapon for a combatant.

        Purpose:
            Helper method to find the active weapon for a combatant, falling back to an unarmed strike
            if no weapon is equipped.

        Args:
            combatant (Combatant): The combatant to check.

        Returns:
            Dict[str, Any]: A dictionary representing the weapon (name, damage, type).
        """
        equipment = None
        if combatant.character_ref:
            equipment = combatant.character_ref.equipment
        elif combatant.npc_ref:
            equipment = combatant.npc_ref.equipment
            
        if equipment and equipment.weapons:
            # TODO: Check for 'equipped' flag. For now, take the first one.
            # In a real implementation, we would filter by w.get('equipped', True)
            weapon = equipment.weapons[0]
            if isinstance(weapon, EquipmentItem):
                return weapon.model_dump()
            return weapon
            
        return {"item_id": "unarmed_strike", "name": "Unarmed Strike", "damage": "1", "type": "melee"}

    def _get_attack_bonus(self, combatant: Combatant) -> int:
        """
        Calculates the attack bonus for a combatant.

        Purpose:
            Helper method to retrieve the attack bonus from the underlying character or NPC reference.

        Args:
            combatant (Combatant): The combatant to check.

        Returns:
            int: The calculated attack bonus.
        """
        if combatant.character_ref:
            return combatant.character_ref.combat_stats.attack_bonus
        elif combatant.npc_ref:
            return combatant.npc_ref.combat_stats.attack_bonus
        return 0

    async def apply_direct_damage(self, state: CombatState, target_id: str, amount: int, is_attack: bool = False) -> CombatState:
        """
        Applies damage directly to a target and syncs with CharacterService if applicable.

        Purpose:
            Reduces a combatant's HP, logs the event, checks for death, and ensures player HP
            is synchronized with persistent storage.

        Args:
            state (CombatState): The current combat state.
            target_id (str): The UUID string of the target combatant.
            amount (int): The amount of damage to apply.
            is_attack (bool, optional): Whether the damage is from an attack (affects logging). Defaults to False.

        Returns:
            CombatState: The updated combat state.
        """
        try:
            target_uuid = UUID(target_id)
            combatant = state.get_combatant(target_uuid)
            if combatant:
                actual_damage = combatant.take_damage(amount)
                source_str = "Attack" if is_attack else "Effect"
                state.add_log_entry(f"{combatant.name} took {actual_damage} damage ({source_str}). HP: {combatant.current_hit_points}/{combatant.max_hit_points}")
                
                if not combatant.is_alive():
                    state.add_log_entry(f"{combatant.name} has been defeated!")

                # IMMEDIATE SYNC FOR PLAYERS
                if combatant.type == CombatantType.PLAYER and combatant.character_ref:
                    await self._sync_player_hp(combatant)
                
                # TODO: Implement Status Effects (e.g., Poison, Stun) here.
                # Future improvement: Add a 'status_effects' list to Combatant and process them.

        except ValueError:
            log_debug(f"Invalid UUID for target_id: {target_id}")
        return state

    async def _sync_player_hp(self, combatant: Combatant) -> None:
        """
        Synchronizes the combatant's HP back to the persistent Character storage.

        Purpose:
            Ensures that damage taken during combat is immediately reflected in the player's
            persistent character record to prevent data loss.

        Args:
            combatant (Combatant): The combatant (must be a player) to sync.

        Returns:
            None
        """
        try:
            if not combatant.character_ref:
                return

            # Persist via CharacterService
            # We instantiate a fresh service to ensure clean state handling
            char_service = CharacterService(
                str(combatant.character_ref.id), 
                data_service=self.character_data_service
            )
            await char_service.load()
            
            # Update the loaded character data with the current combat HP
            # We trust the combat state as the source of truth for HP during combat
            # Ensure we don't exceed max HP (though combat logic should handle this, safety first)
            new_hp = combatant.current_hit_points
            if char_service.character_data:
                char_service.character_data.combat_stats.current_hit_points = new_hp
            
                # Save the updated character
                await char_service.save()
            
                # Update the local reference to keep it in sync with the "real" character
                combatant.character_ref = char_service.character_data
            
            log_debug(f"Synced HP for player {combatant.name} to {combatant.current_hit_points}")
            
        except Exception as e:
            log_error(f"Failed to sync player HP for {combatant.name}: {e}")

    async def end_combat(self, state: CombatState, reason: str) -> CombatState:
        """
        Ends the combat session.

        Purpose:
            Marks the combat as inactive, logs the reason, and performs a final HP sync for all players.

        Args:
            state (CombatState): The current combat state.
            reason (str): The reason for ending the combat (e.g., "Victory", "Fled").

        Returns:
            CombatState: The updated (inactive) combat state.
        """
        state.is_active = False
        state.add_log_entry(f"Combat ended: {reason}")
        
        # Final sync for all players
        for p in state.participants:
            if p.type == CombatantType.PLAYER:
                await self._sync_player_hp(p)
                
        return state

    def get_combat_summary(self, state: CombatState) -> CombatSummary:
        """
        Generates a summary of the current combat state.

        Purpose:
            Provides a simplified view of the combat for UI display or AI context, including
            participants, turn order, and recent logs.

        Args:
            state (CombatState): The current combat state.

        Returns:
            CombatSummary: A DTO containing the combat summary.
        """
        participants_summary = [
            ParticipantSummary(
                id=str(p.id),
                name=p.name,
                hp=p.current_hit_points,
                max_hp=p.max_hit_points,
                camp="player" if p.type == CombatantType.PLAYER else "enemy"
            ) for p in state.participants
        ]

        return CombatSummary(
            combat_id=str(state.id),
            round=state.round_number,
            participants=participants_summary,
            turn_order=[str(uid) for uid in state.turn_order],
            current_turn=str(state.current_turn_combatant_id) if state.current_turn_combatant_id else None,
            status="ongoing" if state.is_active else "ended",
            log=state.log[-5:] # Last 5 entries
        )

    def end_turn(self, state: CombatState) -> CombatState:
        """
        Advances the combat to the next turn.

        Purpose:
            Updates the current turn holder, increments the round counter if necessary, and logs the transition.

        Args:
            state (CombatState): The current combat state.

        Returns:
            CombatState: The updated combat state with the new turn holder.
        """
        if not state.turn_order:
            return state
            
        try:
            if state.current_turn_combatant_id is None:
                raise ValueError("Current turn combatant ID is None")

            current_idx = state.turn_order.index(state.current_turn_combatant_id)
            next_idx = (current_idx + 1) % len(state.turn_order)
            state.current_turn_combatant_id = state.turn_order[next_idx]
            
            if next_idx == 0:
                state.round_number += 1
                state.add_log_entry(f"Round {state.round_number} started.")
                
            next_combatant = state.get_combatant(state.current_turn_combatant_id)
            if next_combatant:
                state.add_log_entry(f"It is now {next_combatant.name}'s turn.")
                
        except ValueError:
            # Current combatant not in turn order (maybe died/removed?)
            if state.turn_order:
                state.current_turn_combatant_id = state.turn_order[0]
        
        return state

    def check_combat_end(self, state: CombatState) -> bool:
        """
        Checks if the combat should end.

        Purpose:
            Determines if one side has been completely defeated (no living members).

        Args:
            state (CombatState): The current combat state.

        Returns:
            bool: True if the combat should end, False otherwise.
        """
        players_alive = any(p.type == CombatantType.PLAYER and p.is_alive() for p in state.participants)
        enemies_alive = any(p.type == CombatantType.NPC and p.is_alive() for p in state.participants)
        return not players_alive or not enemies_alive

