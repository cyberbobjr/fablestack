from uuid import uuid4

import pytest

from back.models.domain.combat_state import CombatantType
from back.models.domain.payloads import CombatIntentPayload
from back.models.domain.payloads import EnemyIntent as CombatEnemyIntent
from back.services.character_service import CharacterService
from back.services.combat_service import CombatService
from back.services.game_session_service import GameSessionService


@pytest.mark.asyncio
async def test_combat_persistence_hp_and_inventory():
    """
    Verify that changes to player HP and inventory during combat are persisted
    to the character storage.
    """
    # 0. Dependencies Setup
    from back.models.domain.equipment_manager import EquipmentManager
    from back.models.domain.races_manager import RacesManager
    from back.services.character_data_service import CharacterDataService
    from back.services.equipment_service import EquipmentService
    from back.services.races_data_service import RacesDataService
    from back.services.settings_service import SettingsService
    
    equipment_manager = EquipmentManager()
    races_manager = RacesManager()
    
    settings_service = SettingsService()
    character_data_service = CharacterDataService()
    races_data_service = RacesDataService(races_manager)
    equipment_service = EquipmentService(character_data_service, equipment_manager)

    # 1. Setup Session and Character
    session_id = str(uuid4())
    scenario_id = "test_scenario"
    # 1. Setup Character FIRST
    from back.models.domain.character import (Character, CombatStats, Skills,
                                              Stats)
    from back.models.enums import CharacterStatus

    # Create Character object manually
    stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    skills = Skills()
    combat_stats = Character.calculate_combat_stats(stats, level=1)
    combat_stats.max_hit_points = 20
    combat_stats.current_hit_points = 20
    
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        id=uuid4(), # We will use the ID from the variable
        name="Test Hero",
        race="Human",
        culture="Warrior",
        level=1,
        stats=stats,
        skills=skills,
        combat_stats=combat_stats,
        status=CharacterStatus.ACTIVE,
        description="Test character"
    )
    character_id = str(character.id)
    
    # Save via DataService
    await character_data_service.save_character(character)
    
    # Now initialize CharacterService
    char_service = CharacterService(character_id, data_service=character_data_service)
    await char_service.load()
    
    # Mock TranslationAgent to avoid LLM setup
    from unittest.mock import MagicMock
    translation_agent = MagicMock()

    # 2. Setup Session
    # Create a session (this creates the directory structure)
    # We need to manually inject services into GameSessionService.create
    session_service = await GameSessionService.create(
        session_id, 
        character_id, 
        scenario_id,
        character_data_service=character_data_service,
        equipment_service=equipment_service,
        settings_service=settings_service,
        races_service=races_data_service,
        translation_agent=translation_agent
    )
    # Manually inject missing services into the session instance (since we aren't using the container)
    session_service.character_service = char_service
    session_service.equipment_service = equipment_service
    session_service.data_service = character_data_service

    # Add an item to inventory
    await equipment_service.add_item(char_service.character_data, "item_rope", quantity=5)
    
    # Reload to confirm initial state
    char_service = CharacterService(character_id, data_service=character_data_service)
    await char_service.load()
    assert char_service.character_data.combat_stats.current_hit_points == 20
    assert equipment_service.get_item_quantity(char_service.character_data, "item_rope") == 5
    
    # 2. Start Combat
    combat_service = CombatService(races_data_service=races_data_service, character_data_service=character_data_service)
    intent = CombatIntentPayload(
        location="Test Arena",
        description="Testing persistence",
        enemies_detected=[
            CombatEnemyIntent(name="Goblin", archetype_id="goblin", level=1, role="enemy")
        ],
        message="Fight!"
    )
    
    # Inject session service into combat start (it needs it to get the player)
    # We need to mock the session_service.character_service property to return our char_service
    # OR just ensure session_service has it initialized.
    # GameSessionService._initialize_services does this.
    # But we created it manually. Let's force it.
    
    combat_state = combat_service.start_combat(intent, session_service)
    assert combat_state is not None
    
    # Find player combatant
    player_combatant = next(p for p in combat_state.participants if p.type == CombatantType.PLAYER)
    assert player_combatant.current_hit_points == 20
    
    # 3. Apply Damage via CombatService
    # This should trigger _sync_player_hp
    damage_amount = 5
    await combat_service.apply_direct_damage(combat_state, str(player_combatant.id), damage_amount)
    
    # Check combat state
    assert player_combatant.current_hit_points == 15
    
    # Check PERSISTENCE (Load a fresh CharacterService)
    fresh_char_service = CharacterService(character_id, data_service=character_data_service)
    await fresh_char_service.load()
    assert fresh_char_service.character_data.combat_stats.current_hit_points == 15, "HP should be synced to persistent storage"
    
    # 4. Modify Inventory via EquipmentService (simulating tool usage)
    # Note: Tools use equipment_service directly, so we do too.
    # We use the character reference from the fresh service to be sure.
    await equipment_service.decrease_item_quantity(fresh_char_service.character_data, "item_rope", amount=2)
    
    # Check PERSISTENCE again
    new_char_service = CharacterService(character_id, data_service=character_data_service)
    await new_char_service.load()
    qty = equipment_service.get_item_quantity(new_char_service.character_data, "item_rope")
    assert qty == 3, "Inventory change should be synced to persistent storage"
    
    # 5. End Combat
    await combat_service.end_combat(combat_state, "Victory")
    
    # Final check
    final_char_service = CharacterService(character_id, data_service=character_data_service)
    await final_char_service.load()
    assert final_char_service.character_data.combat_stats.current_hit_points == 15

