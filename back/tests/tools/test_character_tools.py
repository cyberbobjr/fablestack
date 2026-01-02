from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import Character
from back.services.game_session_service import GameSessionService
from back.tools.character_tools import (character_apply_xp,
                                        character_take_damage)


@pytest.fixture
def mock_session_service():
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    service.character_service = MagicMock()
    service.character_service.apply_xp = AsyncMock()
    service.character_service.take_damage = AsyncMock()
    service.character_service.heal = AsyncMock()
    service.character_service.add_currency = AsyncMock()
    service.character_service.remove_currency = AsyncMock()
    
    service.data_service = MagicMock()
    service.races_service = MagicMock()
    service.translation_agent = MagicMock()
    return service

@pytest.fixture
def mock_run_context(mock_session_service):
    mock_model = MagicMock()
    usage = RunUsage(requests=1)
    return RunContext(deps=mock_session_service, retry=0, tool_name="test_tool", model=mock_model, usage=usage)

@pytest.mark.asyncio
async def test_character_apply_xp(mock_run_context):
    mock_updated_character = MagicMock(spec=Character)
    mock_updated_character.experience_points = 150
    mock_updated_character.level = 2
    
    mock_run_context.deps.character_service.apply_xp.return_value = mock_updated_character
    
    result = await character_apply_xp(mock_run_context, 50)
    
    mock_run_context.deps.character_service.apply_xp.assert_awaited_once_with(50)
    assert result["total_xp"] == 150
    assert result["level"] == 2
    assert "Gained 50 XP" in result["message"]



@pytest.mark.asyncio
async def test_character_take_damage(mock_run_context):
    mock_updated_character = MagicMock()
    mock_updated_character.combat_stats.current_hit_points = 10
    mock_updated_character.combat_stats.max_hit_points = 20
    mock_updated_character.combat_stats.is_alive.return_value = True
    
    mock_run_context.deps.character_service.take_damage.return_value = mock_updated_character
    
    result = await character_take_damage(mock_run_context, 5)
    
    mock_run_context.deps.character_service.take_damage.assert_awaited_once_with(5, "unknown")
    assert result["current_hp"] == 10
    assert result["is_alive"] is True
    assert "Took 5 damage" in result["message"]
