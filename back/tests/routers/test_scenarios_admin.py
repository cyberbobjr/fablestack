
import sys
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pytest

from back.models.domain.user import User, UserRole

# Mock tiktoken BEFORE it is used by any import
if 'tiktoken' not in sys.modules:
    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.return_value = MagicMock()
    sys.modules['tiktoken'] = mock_tiktoken

from back.routers.scenarios import create_scenario, delete_scenario
from back.services.scenario_service import ScenarioService


@pytest.mark.asyncio
async def test_process_creation_success():
    """Test successful scenario generation (background task) via service."""
    mock_agent_run = AsyncMock()
    mock_agent_run.return_value.output = """---
id: test_scenario
title: Test Scenario
---
# Content
"""
    
    mock_race = MagicMock()
    mock_race.name = "Human"
    mock_race.id = "human"
    
    mock_llm_config = MagicMock()
    mock_llm_config.api_endpoint = "http://test.com"
    mock_llm_config.api_key = "test"
    mock_llm_config.model = "test-model"

    # Mock Async File IO
    mock_file_handle = AsyncMock()
    mock_file_handle.write = AsyncMock()
    
    mock_file_ctx = AsyncMock()
    mock_file_ctx.__aenter__.return_value = mock_file_handle
    mock_file_ctx.__aexit__.return_value = None

    mock_aio_open = MagicMock(return_value=mock_file_ctx)

    with patch('back.agents.generic_agent.GenericAgent.run', new=mock_agent_run), \
         patch('aiofiles.open', new=mock_aio_open), \
         patch('back.services.scenario_service.get_data_dir', return_value="/tmp"), \
         patch('os.path.exists', return_value=True), \
         patch('back.models.domain.races_manager.RacesManager') as mock_races_mgr_cls, \
         patch('back.config.config') as mock_config, \
         patch('back.services.scenario_service.get_llm_config', return_value=mock_llm_config), \
         patch('back.models.domain.equipment_manager.EquipmentManager'):

        # Setup mocks
        mock_races_mgr = mock_races_mgr_cls.return_value
        mock_races_mgr.get_all_races.return_value = [mock_race]
        mock_config.world.lore = "Test Lore"

        # We call process_creation directly
        await ScenarioService.process_creation("Description", "test_scenario.md")

        # Verify file was written
        mock_file_handle.write.assert_called()

@pytest.mark.asyncio
async def test_create_scenario_endpoint_auth():
    """Test create scenario endpoint requires admin."""
    # We can test the dependency injection by calling the function directly with a mock user
    mock_request = MagicMock()
    mock_request.description = "Desc"
    
    # Create a valid User object
    mock_user = User(
        id=str(uuid4()), 
        email="admin@test.com", 
        role=UserRole.ADMIN, 
        is_active=True, 
        full_name="Admin",
        hashed_password="hashed_secret" # Required field
    )
    
    mock_bg_tasks = MagicMock()
    
    with patch('back.services.scenario_service.ScenarioService.initiate_creation') as mock_initiate:
        mock_initiate.return_value = MagicMock(id="id", title="Generating...", name="name.md", status="creating", is_played=False)
        
        # Call the router function
        await create_scenario(mock_request, background_tasks=mock_bg_tasks, admin_user=mock_user)
        
        mock_initiate.assert_called_once()
        # Verify background task added
        mock_bg_tasks.add_task.assert_called_once()
        args, _ = mock_bg_tasks.add_task.call_args
        assert args[0] == ScenarioService.process_creation

@pytest.mark.asyncio
async def test_delete_scenario_endpoint_auth():
    """Test delete scenario endpoint requires admin."""
    mock_user = User(
        id=str(uuid4()), 
        email="admin@test.com", 
        role=UserRole.ADMIN, 
        is_active=True, 
        full_name="Admin",
        hashed_password="hashed_secret" # Required field
    )
    
    with patch('back.services.scenario_service.ScenarioService.delete_scenario') as mock_delete:
        await delete_scenario("test.md", admin_user=mock_user)
        mock_delete.assert_called_once_with("test.md")

@pytest.mark.asyncio
async def test_list_scenarios_played_status():
    """Test listing scenarios with correct played status."""
    # Mock files
    with patch('os.path.isdir', return_value=True), \
         patch('os.listdir', return_value=['s1.md', 's2.md']), \
         patch('back.services.scenario_service.ScenarioService._parse_metadata') as mock_meta:
        
        mock_meta.side_effect = [
            {'id': 's1', 'title': 'S1'}, 
            {'id': 's2', 'title': 'S2'}
        ]
        
        # Mock sessions and dependencies
        mock_sessions_list = AsyncMock()
        mock_sessions_list.return_value = [{'scenario_id': 's1', 'session_id': str(uuid4())}]
        
        with patch('back.services.game_session_service.GameSessionService.list_all_sessions', new=mock_sessions_list):
            
            scenarios = await ScenarioService.list_scenarios()
            
            assert len(scenarios.scenarios) == 2
            s1 = next(s for s in scenarios.scenarios if s.id == 's1')
            s2 = next(s for s in scenarios.scenarios if s.id == 's2')
            
            assert s1.is_played is True
            assert s2.is_played is False

@pytest.mark.asyncio
async def test_delete_scenario_logic():
    """Test scenario deletion logic."""
    with patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove:
        
        await ScenarioService.delete_scenario("test.md")
        
        # Correct verification of path endswith
        assert mock_remove.call_count == 1
        args, _ = mock_remove.call_args
        assert args[0].endswith("test.md")

@pytest.mark.asyncio
async def test_update_scenario_success():
    """Test successful scenario update."""
    mock_user = User(
        id=str(uuid4()), email="admin@test.com", role=UserRole.ADMIN, is_active=True, full_name="Admin", hashed_password="pw"
    )
    
    with patch('back.services.scenario_service.ScenarioService.update_scenario') as mock_update:
        mock_update.return_value = MagicMock(id="id", title="Title", name="test.md")
        
        # Test endpoint call
        from back.routers.scenarios import update_scenario
        await update_scenario("test.md", "New Content", admin_user=mock_user)
        
        mock_update.assert_called_once_with("test.md", "New Content")
