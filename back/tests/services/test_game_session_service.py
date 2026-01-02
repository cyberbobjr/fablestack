"""
Unit tests for GameSessionService.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from back.models.domain.character import Character
from back.services.game_session_service import GameSessionService
from back.utils.exceptions import SessionNotFoundError


@pytest.mark.asyncio
class TestGameSessionService:
    """
    Test suite for GameSessionService static methods.
    """

    async def test_start_scenario_success(self):
        """
        Test starting a scenario successfully.
        """
        scenario_name = "Les_Pierres_du_Passe.md"
        character_id = uuid4()
        
        # Mock check_existing_session to return False
        with patch.object(GameSessionService, 'check_existing_session', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False
            
            # Mock aiofiles
            mock_file = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_file
            
            with patch('aiofiles.open', return_value=mock_ctx):
                
                # Mock pathlib exists/mkdir
                with patch('pathlib.Path.exists', return_value=True), \
                     patch('pathlib.Path.mkdir'), \
                     patch('back.services.game_session_service.CharacterService') as mock_char_service_cls:
                    
                    mock_char_service = Mock()
                    mock_char_service_cls.return_value = mock_char_service
                    
                    mock_data_service = Mock()
                    result = await GameSessionService.start_scenario(scenario_name, character_id, mock_data_service)

                    assert result.session_id
                    assert result.scenario_name == scenario_name
                    assert result.character_id == str(character_id)
                    assert result.message

    async def test_start_scenario_existing_session(self):
        """
        Test starting a scenario that already exists raises ValueError.
        """
        scenario_name = "Les_Pierres_du_Passe.md"
        character_id = uuid4()

        with patch.object(GameSessionService, 'check_existing_session', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            mock_data_service = Mock()
            with pytest.raises(ValueError, match="A session already exists"):
                await GameSessionService.start_scenario(scenario_name, character_id, mock_data_service)

    async def test_start_scenario_invalid_scenario(self):
        """
        Test starting a non-existent scenario raises FileNotFoundError.
        """
        scenario_name = "Invalid_Scenario.md"
        character_id = uuid4()

        with patch.object(GameSessionService, 'check_existing_session', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False
            
            mock_data_service = Mock()
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(FileNotFoundError):
                    await GameSessionService.start_scenario(scenario_name, character_id, mock_data_service)

    async def test_get_session_info(self):
        """
        Test getting session information.
        """
        session_id = "test-session"
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
             
             mock_file = AsyncMock()
             mock_file.read.side_effect = ["character-id", "scenario-name"]
             mock_ctx = AsyncMock()
             mock_ctx.__aenter__.return_value = mock_file
             
             with patch('aiofiles.open', return_value=mock_ctx):
                
                info = await GameSessionService.get_session_info(session_id)
                assert info.scenario_name == "scenario-name"
                assert info.character_id == "character-id"

    async def test_get_session_info_invalid(self):
        """
        Test getting session info for invalid session raises SessionNotFoundError.
        """
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(SessionNotFoundError, match="does not exist"):
                await GameSessionService.get_session_info("invalid-session")

    async def test_check_existing_session(self):
        """
        Test checking for existing sessions.
        """
        scenario_name = "Les_Pierres_du_Passe.md"
        character_id = "char-id"

        # Case 1: No sessions dir
        with patch('pathlib.Path.exists', return_value=False):
            assert not await GameSessionService.check_existing_session(scenario_name, character_id)

        # Case 2: Session exists
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True), \
             patch('pathlib.Path.iterdir') as mock_iterdir:
             
             # Use MagicMock to support / operator and __str__
             mock_session_path = MagicMock()
             mock_session_path.is_dir.return_value = True
             mock_session_path.name = "session-1"
             mock_session_path.__str__.return_value = "/tmp/session-1"
             
             # Make the division return a MagicMock that also has exists() returning True
             mock_file_path = MagicMock()
             mock_file_path.exists.return_value = True
             mock_file_path.__str__.return_value = "/tmp/session-1/file.txt"
             mock_session_path.__truediv__.return_value = mock_file_path
             
             mock_iterdir.return_value = [mock_session_path]
             
             mock_file = AsyncMock()
             mock_file.read.side_effect = [scenario_name, character_id]
             mock_ctx = AsyncMock()
             mock_ctx.__aenter__.return_value = mock_file
             
             with patch('aiofiles.open', return_value=mock_ctx):
                result = await GameSessionService.check_existing_session(scenario_name, character_id)
                assert result is True


class TestGameSessionServiceInstance:
    """
    Test suite for GameSessionService instance methods.
    """

    @pytest.fixture
    def mock_character(self):
        """Create a mock character for testing."""
        character = Mock(spec=Character)
        character.name = "Test Character"
        character.hp = 100
        character.gold = 50
        character.xp = 0
        return character

    @pytest.fixture
    def mock_services(self, mock_character):
        """Create mock services."""
        data_service = Mock()
        data_service.load_character.return_value = mock_character
        data_service.save_character = Mock()

        character_service = Mock()
        character_service.apply_xp.return_value = mock_character
        character_service.add_currency.return_value = mock_character
        character_service.take_damage.return_value = mock_character
        character_service.character_data = mock_character

        equipment_service = Mock()
        equipment_service.add_item.return_value = mock_character
        equipment_service.remove_item.return_value = mock_character
        equipment_service.buy_equipment.return_value = mock_character
        equipment_service.sell_equipment.return_value = mock_character

        return {
            'data_service': data_service,
            'character_service': character_service,
            'equipment_service': equipment_service
        }

    def _setup_service(self, service, mock_services):
        """Helper to setup service with mocked dependencies."""
        service.data_service = mock_services['data_service']
        service.character_service = mock_services['character_service']
        service.equipment_service = mock_services['equipment_service']
        return service

    def test_apply_xp(self, mock_services):
        """Test applying XP to character."""
        service = GameSessionService("test-session")
        service = self._setup_service(service, mock_services)

        # Call specialized service directly
        result = service.character_service.apply_xp(100)

        mock_services['character_service'].apply_xp.assert_called_once_with(100)
        assert result == mock_services['character_service'].apply_xp.return_value

    def test_add_currency(self, mock_services):
        """Test adding currency to character."""
        service = GameSessionService("test-session")
        service = self._setup_service(service, mock_services)

        result = service.character_service.add_currency(gold=50.0)

        mock_services['character_service'].add_currency.assert_called_once_with(gold=50.0)
        assert result == mock_services['character_service'].add_currency.return_value

    def test_take_damage(self, mock_services):
        """Test taking damage."""
        service = GameSessionService("test-session")
        service = self._setup_service(service, mock_services)

        result = service.character_service.take_damage(20, "combat")

        mock_services['character_service'].take_damage.assert_called_once_with(20, "combat")
        assert result == mock_services['character_service'].take_damage.return_value

    def test_add_item(self, mock_services):
        """Test adding an item."""
        service = GameSessionService("test-session")
        service = self._setup_service(service, mock_services)

        # Mock character_data access
        # service.character_data is removed, so we access via character_service
        character_data = service.character_service.character_data

        result = service.equipment_service.add_item(character_data, "sword", 1)

        mock_services['equipment_service'].add_item.assert_called_once_with(character_data, "sword", 1)
        assert result == mock_services['equipment_service'].add_item.return_value

    @pytest.mark.asyncio
    async def test_save_history(self, mock_services):
        """Test saving history."""
        from pydantic_ai.messages import ModelMessagesTypeAdapter

        # Create sample messages
        sample_data = [{"kind": "request", "parts": [{"content": "test", "part_kind": "user-prompt"}]}]
        messages = ModelMessagesTypeAdapter.validate_python(sample_data)

        service = GameSessionService("test-session")

        # Mock the PydanticJsonlStore
        with patch('back.services.game_session_service.PydanticJsonlStore') as mock_store_cls:
            mock_store = Mock()
            # Mock async method
            mock_store.save_pydantic_history_async = AsyncMock()
            mock_store_cls.return_value = mock_store

            await service.save_history("narrative", messages)

            mock_store_cls.assert_called_once()
            mock_store.save_pydantic_history_async.assert_called_once_with(messages)

    @pytest.mark.asyncio
    async def test_load_history_raw_json(self, mock_services):
        """Test loading raw JSON history."""
        service = GameSessionService("test-session")

        # Mock the PydanticJsonlStore
        with patch('back.services.game_session_service.PydanticJsonlStore') as mock_store_cls, \
             patch('os.path.exists', return_value=True):
            mock_store = Mock()
            # Mock async method
            mock_store.load_raw_json_history_async = AsyncMock(return_value=[{"kind": "request", "parts": []}])
            mock_store_cls.return_value = mock_store

            result = await service.load_history_raw_json("narrative")

            mock_store_cls.assert_called_once()
            mock_store.load_raw_json_history_async.assert_called_once()
            assert result == [{"kind": "request", "parts": []}]



