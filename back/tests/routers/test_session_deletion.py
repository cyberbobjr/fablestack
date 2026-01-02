import pathlib
import shutil
from uuid import uuid4

import pytest
from httpx import AsyncClient

from back.config import get_data_dir
from back.main import app
from back.models.enums import CharacterSex, CharacterStatus
from back.services.character_service import CharacterService
from back.services.game_session_service import GameSessionService


@pytest.mark.asyncio
async def test_delete_session_success(async_client: AsyncClient, clean_test_data_dir):
    """
    Test successful deletion of a session and character status reset.
    """
    # 1. Create a dummy session and character
    session_id = str(uuid4())
    character_id = str(uuid4())
    scenario_id = "test_scenario.md"

    # Create session directory manually to simulate existing session
    session_dir = pathlib.Path(get_data_dir()) / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    with open(session_dir / "character.txt", "w") as f:
        f.write(character_id)
    with open(session_dir / "scenario.txt", "w") as f:
        f.write(scenario_id)

    # Create dummy character data
    from back.models.domain.character import (Character, CombatStats,
                                              Equipment, Skills, Spells, Stats)
    from back.services.character_data_service import CharacterDataService

    data_service = CharacterDataService()
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000",
        id=character_id,
        name="TestChar",
        race="human",
        sex=CharacterSex.MALE,
        culture="gondor",
        stats=Stats(strength=10, agility=10, constitution=10, intelligence=10, wisdom=10, charisma=10),
        skills=Skills(),
        combat_stats=CombatStats(max_hit_points=10, current_hit_points=10),
        equipment=Equipment(),
        spells=Spells(),
        status=CharacterStatus.IN_GAME
    )
    await data_service.save_character(character)

    # Initialize service to verify state
    # char_service = CharacterService(character_id, data_service) # CharacterService might be sync/legacy
    loaded_char = await data_service.load_character(character_id)

    # Verify initial state
    assert session_dir.exists()
    assert loaded_char.status == CharacterStatus.IN_GAME

    # 2. Call DELETE endpoint
    # Ensure Router uses our data_service (or one that accesses same files)
    injector = app.state.injector
    injector.binder.bind(CharacterDataService, to=data_service)
    
    response = await async_client.delete(f"/api/gamesession/{session_id}")
    assert response.status_code == 204

    # 3. Verify session directory is gone
    assert not session_dir.exists()

    # 4. Verify character status is reset to ACTIVE
    # 4. Verify character status is reset to ACTIVE
    # Reload character data
    loaded_char = await data_service.load_character(character_id)
    assert loaded_char.status == CharacterStatus.ACTIVE

@pytest.mark.asyncio
async def test_delete_session_not_found(async_client: AsyncClient):
    """
    Test deletion of a non-existent session returns 404.
    """
    non_existent_id = str(uuid4())
    response = await async_client.delete(f"/api/gamesession/{non_existent_id}")
    assert response.status_code == 404
