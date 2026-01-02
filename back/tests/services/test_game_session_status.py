
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from back.models.enums import CharacterStatus
from back.services.game_session_service import GameSessionService


@pytest.fixture
def mock_character_service():
    with patch('back.services.game_session_service.CharacterService') as MockCharService:
        yield MockCharService

@pytest.fixture
def mock_session_setup():
    with patch('back.services.game_session_service.pathlib.Path') as MockPath, \
         patch('back.services.game_session_service.get_data_dir', return_value="/tmp/data"):
        
        # Setup mock paths
        mock_scenarios_dir = MockPath.return_value / "scenarios"
        mock_sessions_dir = MockPath.return_value / "sessions"
        
        # Setup scenario existence check
        mock_scenario_path = mock_scenarios_dir / "test_scenario.md"
        mock_scenario_path.exists.return_value = True
        
        yield mock_sessions_dir

@pytest.mark.asyncio
async def test_start_scenario_sets_in_game_status(mock_character_service, mock_session_setup):
    # Arrange
    scenario_name = "test_scenario.md"
    character_id = uuid4()
    
    # Mock CharacterService instance
    mock_char_service_instance = mock_character_service.return_value
    mock_char_service_instance.character_data = MagicMock()
    mock_char_service_instance.load = AsyncMock()
    mock_char_service_instance.save = AsyncMock()
    
    # Mock aiofiles.open with proper async context manager
    with patch('aiofiles.open') as mock_aiofiles:
        # Create async context manager
        async_file_mock = AsyncMock()
        async_file_mock.write = AsyncMock()
        
        # Make aiofiles.open return an async context manager
        mock_aiofiles.return_value.__aenter__ = AsyncMock(return_value=async_file_mock)
        mock_aiofiles.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock check_existing_session to return False
        with patch.object(GameSessionService, 'check_existing_session', return_value=False):
            # Act
            mock_data_service = Mock()
            await GameSessionService.start_scenario(scenario_name, character_id, mock_data_service)
            
            # Assert
            # Verify CharacterService was initialized with correct ID
            mock_character_service.assert_called_with(str(character_id), data_service=ANY)
            
            # Verify status was updated to IN_GAME
            assert mock_char_service_instance.character_data.status == CharacterStatus.IN_GAME
            
            # Verify save was called
            mock_char_service_instance.save.assert_awaited_once()
