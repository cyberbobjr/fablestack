from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.combat_state import (Combatant, CombatantType,
                                             CombatState)
from back.models.domain.game_state import GameState
from back.services.game_session_service import GameSessionService
from back.tools.combat_tools import (apply_direct_damage_tool,
                                     check_combat_end_tool, end_combat_tool,
                                     end_turn_tool, execute_attack_tool,
                                     get_combat_status_tool,
                                     search_enemy_archetype_tool)


@pytest.fixture
def mock_session_service():
    service = MagicMock(spec=GameSessionService)
    service.session_id = str(uuid4())
    service.load_game_state = AsyncMock()
    service.update_game_state = AsyncMock()
    service.data_service = MagicMock()
    service.character_service = MagicMock()
    service.races_service = MagicMock()
    return service

@pytest.fixture
def mock_run_context(mock_session_service):
    mock_model = MagicMock()
    usage = RunUsage(requests=1)
    return RunContext(deps=mock_session_service, retry=0, tool_name="test_tool", model=mock_model, usage=usage)

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_execute_attack_tool(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    # ... rest of the test code stays mostly the same because mock_combat_service is now clearly defined
    # Let's redefine the test logic to be explicit about signatures
    combat_id = "combat-123"
    attacker_id = "attacker-1"
    target_id = "target-1"

    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    mock_state.is_active = True

    p1 = MagicMock(spec=Combatant)
    p1.id = attacker_id
    p1.name = "Hero"
    p1.is_alive.return_value = True

    p2 = MagicMock(spec=Combatant)
    p2.id = target_id
    p2.name = "Goblin Warrior"
    p2.is_alive.return_value = True

    mock_state.participants = [p1, p2]
    mock_state.get_current_combatant.return_value = p1

    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state

    mock_result = MagicMock()
    mock_result.message = "Hit!"
    mock_result.model_dump.return_value = {"message": "Hit!"}

    mock_combat_service.execute_attack = AsyncMock(return_value=mock_result)
    mock_combat_service.check_combat_end = MagicMock(return_value=False)
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {"status": "ongoing"}
    mock_combat_service.get_combat_summary = MagicMock(return_value=mock_summary)

    # Call with Modifiers
    result = await execute_attack_tool(mock_run_context, "Goblin", attack_modifier=2, advantage=True)

    assert result["message"] == "Hit!"
    assert result["attack_details"]["resolved_target_name"] == "Goblin Warrior"
    
    # Verify call args
    mock_combat_service.execute_attack.assert_called_once_with(
        mock_state, 
        str(attacker_id), 
        str(target_id), 
        attack_modifier=2, 
        advantage=True
    )

    # 2. Fuzzy/Partial Match Test (Reset mock calls)
    mock_combat_service.execute_attack.reset_mock()
    
    result_fuzzy = await execute_attack_tool(mock_run_context, "Goblin")
    mock_combat_service.execute_attack.assert_called_with(
        mock_state, 
        str(attacker_id), 
        str(target_id), 
        attack_modifier=0, 
        advantage=False
    )
    assert result_fuzzy["attack_details"]["resolved_target_name"] == "Goblin Warrior"

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_execute_attack_tool_ends_combat(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    combat_id = "combat-123"
    attacker_id = "attacker-1"
    target_id = "target-1"
    
    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    mock_state.is_active = True
    
    # Participants
    p1 = MagicMock(spec=Combatant)
    p1.id = attacker_id
    p1.name = "Hero"
    p1.type = CombatantType.PLAYER
    p1.is_alive.return_value = True
    
    p2 = MagicMock(spec=Combatant)
    p2.id = target_id
    p2.name = "Dragon"
    p2.type = CombatantType.NPC
    # First call: Target validation (True). Second call: End Check (False)
    p2.is_alive.side_effect = [True, False, False, False]
    
    mock_state.participants = [p1, p2]
    mock_state.get_current_combatant.return_value = p1
    
    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state
    
    mock_result = MagicMock()
    mock_result.message = "Hit! Enemy dead."
    mock_result.model_dump.return_value = {"message": "Hit! Enemy dead."}
    
    mock_combat_service.execute_attack = AsyncMock(return_value=mock_result)
    mock_combat_service.check_combat_end = MagicMock(return_value=True)
    mock_combat_service.end_combat = AsyncMock(return_value=mock_state)
    
    result = await execute_attack_tool(mock_run_context, "Dragon")
    
    mock_combat_service.end_combat.assert_called_once_with(mock_state, "victory")
    assert result["auto_ended"]["ended"] is True
    assert result["auto_ended"]["reason"] == "victory"

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_apply_direct_damage_tool(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    combat_id = "combat-123"
    target_id = "target-1"
    amount = 10
    
    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    
    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state
    
    mock_combat_service.apply_direct_damage = AsyncMock(return_value=mock_state)
    mock_combat_service.check_combat_end = MagicMock(return_value=False)
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {}
    mock_combat_service.get_combat_summary = MagicMock(return_value=mock_summary)
    
    result = await apply_direct_damage_tool(mock_run_context, target_id, amount, "Fireball")
    
    mock_combat_service.apply_direct_damage.assert_called_once_with(mock_state, target_id, amount, is_attack=False)
    mock_run_context.deps.update_game_state.assert_called_once_with(mock_game_state)
    assert "Applied 10 damage" in result["message"]

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_end_combat_tool(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    combat_id = "combat-123"
    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    
    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state
    
    mock_combat_service.end_combat = AsyncMock(return_value=mock_state)
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {"status": "ended"}
    mock_combat_service.get_combat_summary = MagicMock(return_value=mock_summary)
    
    result = await end_combat_tool(mock_run_context, "victory")
    
    mock_combat_service.end_combat.assert_called_once_with(mock_state, "victory")
    mock_run_context.deps.update_game_state.assert_called_once_with(mock_game_state)
    assert mock_game_state.combat_state is None
    assert mock_game_state.session_mode == "narrative"
    assert result["status"] == "ended"

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_end_turn_tool(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    combat_id = "combat-123"
    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    
    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state
    
    mock_combat_service.end_turn = MagicMock(return_value=mock_state)
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {}
    mock_combat_service.get_combat_summary = MagicMock(return_value=mock_summary)
    
    current_p = MagicMock()
    current_p.name = "Player"
    mock_state.get_current_combatant.return_value = current_p
    
    result = await end_turn_tool(mock_run_context)
    
    mock_combat_service.end_turn.assert_called_once()
    mock_run_context.deps.update_game_state.assert_called_once_with(mock_game_state)
    assert "Turn ended" in result["message"]

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_check_combat_end_tool_ongoing(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    combat_id = "combat-123"
    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    
    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state
    
    mock_combat_service.check_combat_end = MagicMock(return_value=False)
    
    result = await check_combat_end_tool(mock_run_context)
    
    assert result["combat_ended"] is False
    assert result["status"] == "ongoing"

@patch('back.tools.combat_tools.CombatService')
@pytest.mark.asyncio
async def test_get_combat_status_tool(mock_CombatService, mock_run_context):
    mock_combat_service = mock_CombatService.return_value
    combat_id = "combat-123"
    mock_state = MagicMock(spec=CombatState)
    mock_state.id = combat_id
    
    mock_game_state = MagicMock(spec=GameState)
    mock_game_state.combat_state = mock_state
    mock_run_context.deps.load_game_state.return_value = mock_game_state
    
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {"alive_participants": []}
    mock_combat_service.get_combat_summary = MagicMock(return_value=mock_summary)
    
    result = await get_combat_status_tool(mock_run_context)
    
    mock_combat_service.get_combat_summary.assert_called_once()
    assert "alive_participants" in result

    mock_combat_service.get_combat_summary.assert_called_once()
    assert "alive_participants" in result

def test_search_enemy_archetype_tool(mock_run_context):
    mock_races_service = MagicMock()
    mock_run_context.deps.races_service = mock_races_service
    
    mock_races_service.search_archetypes.return_value = [
        {"id": "goblin_warrior", "name": "Goblin Warrior", "description": "A nasty goblin.", "level": 1}
    ]
    
    result = search_enemy_archetype_tool(mock_run_context, "goblin")
    
    mock_races_service.search_archetypes.assert_called_once_with("goblin")
    assert result["count"] == 1
    assert result["results"][0]["id"] == "goblin_warrior"
    assert result["results"][0]["level"] == 1
    assert "Found 1 archetypes" in result["message"]

def test_search_enemy_archetype_tool_empty(mock_run_context):
    mock_races_service = MagicMock()
    mock_run_context.deps.races_service = mock_races_service
    
    mock_races_service.search_archetypes.return_value = []
    
    result = search_enemy_archetype_tool(mock_run_context, "xenomorphe")
    
    mock_races_service.search_archetypes.assert_called_once_with("xenomorphe")
    assert result["count"] == 0
    assert result["results"] == []
    assert "Found 0 archetypes" in result["message"]

def test_search_enemy_archetype_tool_error(mock_run_context):
    mock_races_service = MagicMock()
    mock_run_context.deps.races_service = mock_races_service
    
    mock_races_service.search_archetypes.side_effect = Exception("Database error")
    
    result = search_enemy_archetype_tool(mock_run_context, "dragon")
    
    assert "error" in result
    assert "Database error" in result["error"]
