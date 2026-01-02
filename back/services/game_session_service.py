"""
Service for managing role-playing game sessions.
Handles loading and saving of history, as well as character and scenario data.
Refactored to use specialized services (Phase 3).
"""

import os
import pathlib
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic_ai import ModelMessage

from back.agents.translation_agent import TranslationAgent
from back.config import get_data_dir
from back.models.api.game import TimelineEvent
from back.models.domain.combat_state import CombatState
from back.models.domain.game_state import GameState
from back.models.enums import CharacterStatus
from back.models.service.dtos import (SessionMetadata, SessionStartResult,
                                      SessionSummary)
from back.services.character_data_service import CharacterDataService
from back.services.character_service import CharacterService
from back.services.equipment_service import EquipmentService
from back.services.races_data_service import RacesDataService
from back.services.settings_service import SettingsService
from back.storage.pydantic_jsonl_store import PydanticJsonlStore
from back.utils.exceptions import (CharacterNotFoundError,
                                   ScenarioNotFoundError, SessionNotFoundError)
from back.utils.logger import log_debug, log_warning

# History types constants
HISTORY_NARRATIVE = "narrative"
HISTORY_COMBAT = "combat"


class GameSessionService:
    """
    ### GameSessionService
    **Description:** Service responsible for managing game sessions.
    It handles the lifecycle of a session, including:
    - Loading and saving session metadata (character ID, scenario ID).
    - Managing message history for narrative and combat modes.
    - Initializing and providing access to specialized services (`CharacterService`, `EquipmentService`).
    - Building system prompts for agents.

    **Attributes:**
    - `session_id` (str): Unique identifier for the session.
    - `character_id` (Optional[str]): ID of the character associated with the session.
    - `scenario_id` (str): ID of the scenario associated with the session.
    - `data_service` (Optional[CharacterDataService]): Service for character data persistence.
    - `character_service` (Optional[CharacterService]): Service for character business logic.
    - `equipment_service` (Optional[EquipmentService]): Service for equipment management.
    """

    def __init__(self, session_id: str) -> None:
        """
        ### __init__
        **Description:** Initializes the session service with a session identifier.
        **Note:** Does NOT load data automatically. Use `create` or `load` factory methods.

        **Parameters:**
        - `session_id` (str): Unique session identifier.
        """
        self.session_id = session_id
        self.character_id: Optional[str] = None
        self.scenario_id: str = ""

        # Specialized services
        self.data_service: Optional[CharacterDataService] = None
        self.character_service: Optional[CharacterService] = None
        self.equipment_service: Optional[EquipmentService] = None
        self.settings_service : Optional[SettingsService]= None # Injected by DependencyContainer
        self.races_service: Optional[RacesDataService] = None
        self.translation_agent: Optional[TranslationAgent] = None

    @classmethod
    async def create(
        cls, 
        session_id: str, 
        character_id: str, 
        scenario_id: str,
        character_data_service: CharacterDataService,
        equipment_service: EquipmentService,
        settings_service: SettingsService,
        races_service: RacesDataService,
        translation_agent: TranslationAgent
    ) -> 'GameSessionService':
        """
        ### create
        **Description:** Async factory to create a new session.
        
        **Parameters:**
        - `session_id` (str): Unique session identifier.
        - `character_id` (str): Character ID.
        - `scenario_id` (str): Scenario ID.
        - `character_data_service`: Injected CharacterDataService.
        - `equipment_service`: Injected EquipmentService.
        - `settings_service`: Injected SettingsService.
        - `races_service`: Injected RacesDataService.
        - `translation_agent`: Injected TranslationAgent.
        
        **Returns:**
        - `GameSessionService`: Initialized service instance.
        """
        instance = cls(session_id)
        instance.data_service = character_data_service
        instance.equipment_service = equipment_service
        instance.settings_service = settings_service
        instance.races_service = races_service
        instance.translation_agent = translation_agent
        
        await instance._create_session(character_id, scenario_id)
        return instance

    @classmethod
    async def load(
        cls, 
        session_id: str,
        character_data_service: CharacterDataService,
        equipment_service: EquipmentService,
        settings_service: SettingsService,
        races_service: RacesDataService,
        translation_agent: TranslationAgent
    ) -> 'GameSessionService':
        """
        ### load
        **Description:** Async factory to load an existing session.
        
        **Parameters:**
        - `session_id` (str): Unique session identifier.
        - `character_data_service`: Injected service.
        - `equipment_service`: Injected service.
        - `settings_service`: Injected service.
        - `races_service`: Injected service.
        - `translation_agent`: Injected service.
        
        **Returns:**
        - `GameSessionService`: Initialized service with loaded data.
        
        **Raises:**
        - `SessionNotFoundError`: If session does not exist.
        """
        instance = cls(session_id)
        instance.data_service = character_data_service
        instance.equipment_service = equipment_service
        instance.settings_service = settings_service
        instance.races_service = races_service
        instance.translation_agent = translation_agent
        
        if not await instance._load_session_data():
             raise SessionNotFoundError(f"Session {session_id} does not exist")
        return instance

    async def _load_session_data(self) -> bool:
        """
        ### _load_session_data
        **Description:** Asynchronously loads session metadata.
        """
        import aiofiles
        session_dir = pathlib.Path(get_data_dir()) / "sessions" / self.session_id
        if session_dir.exists() and session_dir.is_dir():
            # Load character ID
            character_file = session_dir / "character.txt"
            if character_file.exists():
                async with aiofiles.open(character_file, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    self.character_id = content.strip()

                # Initialize specialized services for this character
                try:
                    await self._initialize_services()
                except FileNotFoundError:
                    raise CharacterNotFoundError(f"Character {self.character_id} not found")

            # Load scenario ID
            scenario_file = session_dir / "scenario.txt"
            if scenario_file.exists():
                async with aiofiles.open(scenario_file, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    self.scenario_id = content.strip()
            else:
                raise ValueError(f"Missing scenario.txt file for session '{self.session_id}'.")

            return True

        return False

    async def _create_session(self, character_id: str, scenario_id: str) -> None:
        """
        ### _create_session
        **Description:** Asynchronously creates a new session directory and saves metadata.
        """
        import aiofiles
        session_dir = pathlib.Path(get_data_dir()) / "sessions" / self.session_id

        # Create session directory (sync operation, but fast/rare)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save character ID
        character_file = session_dir / "character.txt"
        async with aiofiles.open(character_file, mode='w', encoding='utf-8') as f:
            await f.write(character_id)

        # Save scenario ID
        scenario_file = session_dir / "scenario.txt"
        async with aiofiles.open(scenario_file, mode='w', encoding='utf-8') as f:
            await f.write(scenario_id)

        # Set character_id attribute
        self.character_id = character_id

        # Initialize specialized services for this character
        try:
            await self._initialize_services()
        except FileNotFoundError:
            raise CharacterNotFoundError(f"Character {character_id} not found")

        self.scenario_id = scenario_id

    async def _initialize_services(self) -> None:
        """
        ### _initialize_services
        **Description:** Initializes internal services using provided dependencies.
        """
        # CharacterService (Stateful - per session)
        try:
            if not self.character_id:
                raise ValueError("Cannot initialize CharacterService without character_id")
            
            if not self.data_service:
                 # Should rely on caller to provide data_service in load/create
                 # But if logic allows deferred loading?
                 pass 
                
            self.character_service = CharacterService(
                str(self.character_id), 
                data_service=self.data_service
            )
            # Must await load
            await self.character_service.load()
            
        except Exception as e:
            log_warning(f"Failed to initialize CharacterService: {e}", session_id=self.session_id)
            self.character_service = None

    @staticmethod
    async def list_all_sessions() -> List[SessionSummary]:
        """
        ### list_all_sessions
        **Description:** Asynchronously retrieves a list of all available game sessions with their metadata.

        **Returns:** 
        - `List[SessionSummary]`: A list of session summaries.
        """
        import aiofiles
        sessions_dir = pathlib.Path(get_data_dir()) / "sessions"
        
        all_sessions = []

        if sessions_dir.exists() and sessions_dir.is_dir():
            # iterdir is sync, but directory listing is usually fast. 
            # For strict async, we could use run_in_executor, but it might be overkill here.
            # We will make the file reading async.
            for session_path in sessions_dir.iterdir():
                if session_path.is_dir():
                    # Load character ID
                    character_file = session_path / "character.txt"
                    if character_file.exists():
                        async with aiofiles.open(character_file, mode='r', encoding='utf-8') as f:
                            content = await f.read()
                            character_id = content.strip()
                    else:
                        character_id = "Unknown"

                    # Load scenario ID
                    scenario_file = session_path / "scenario.txt"
                    if scenario_file.exists():
                        async with aiofiles.open(scenario_file, mode='r', encoding='utf-8') as f:
                            content = await f.read()
                            scenario_id = content.strip()
                    else:
                        scenario_id = "Unknown"

                    all_sessions.append(SessionSummary(
                        session_id=session_path.name,
                        character_id=character_id,
                        scenario_id=scenario_id
                    ))

        return all_sessions

    @staticmethod
    async def start_scenario(
        scenario_name: str, 
        character_id: UUID, 
        character_data_service: CharacterDataService,
        user_id: Optional[str] = None
    ) -> SessionStartResult:
        """
        ### start_scenario
        **Description:** Starts a new scenario with a specific character by creating a unique session.

        **Parameters:**
        - `scenario_name` (str): The name of the scenario to start.
        - `character_id` (UUID): The unique identifier of the character.
        - `character_data_service`: Injected service.

        **Returns:**
        - `SessionStartResult`: Result containing the session details.

        **Raises:**
        - `ValueError`: If a session already exists for this scenario and character.
        - `FileNotFoundError`: If the scenario definition does not exist.
        """
        import aiofiles

        # Check if a session already exists with the same scenario and character
        if await GameSessionService.check_existing_session(scenario_name, str(character_id)):
            raise ValueError(f"A session already exists for scenario '{scenario_name}' with character {character_id}.")

        scenarios_dir = pathlib.Path(get_data_dir()) / "scenarios"
        sessions_dir = pathlib.Path(get_data_dir()) / "sessions"

        # Check if the scenario exists
        scenario_path = scenarios_dir / scenario_name
        if not scenario_path.exists():
            raise FileNotFoundError(f"The scenario '{scenario_name}' does not exist.")

        # Create a session for the scenario
        session_id = str(uuid4())
        session_dir = sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Associate the character with the session
        character_file = session_dir / "character.txt"
        async with aiofiles.open(character_file, mode='w', encoding='utf-8') as f:
            await f.write(str(character_id))

        # Store the scenario name in the session
        scenario_file = session_dir / "scenario.txt"
        async with aiofiles.open(scenario_file, mode='w', encoding='utf-8') as f:
            await f.write(scenario_name)

        # Initialize GameState with user_id
        game_state = GameState(
            character_uuid=str(character_id),
            user_id=user_id,
            scenario_status="active"
        )
        game_state_file = session_dir / "game_state.json"
        async with aiofiles.open(game_state_file, mode='w', encoding='utf-8') as f:
             await f.write(game_state.model_dump_json(indent=2))

        # Update character status to IN_GAME
        try:
            char_service = CharacterService(str(character_id), data_service=character_data_service)
            await char_service.load()
            char_service.character_data.status = CharacterStatus.IN_GAME
            await char_service.save()
            log_debug(f"Character {character_id} status updated to IN_GAME")
        except Exception as e:
            log_debug(f"Failed to update character status to IN_GAME: {e}")
            # Non-blocking error, we continue


        log_debug("Scenario started", action="start_scenario", session_id=session_id, character_id=str(character_id), scenario_name=scenario_name)
        return SessionStartResult(
            session_id=session_id,
            scenario_name=scenario_name,
            character_id=str(character_id),
            message=f"Scenario '{scenario_name}' successfully started for character {character_id}."
        )

    @staticmethod
    async def delete_session(session_id: str, character_data_service: CharacterDataService) -> None:
        """
        ### delete_session
        **Description:** Deletes a game session and resets the associated character status to ACTIVE.

        **Parameters:**
        - `session_id` (str): The unique session identifier.
        - `character_data_service`: Injected service.

        **Raises:**
        - `SessionNotFoundError`: If the session does not exist.
        """
        import shutil

        import aiofiles
        
        session_dir = pathlib.Path(get_data_dir()) / "sessions" / session_id

        if not session_dir.exists() or not session_dir.is_dir():
            raise SessionNotFoundError(f"Session {session_id} does not exist")

        # 1. Retrieve character ID to reset status
        character_file = session_dir / "character.txt"
        character_id = None
        if character_file.exists():
            async with aiofiles.open(character_file, mode='r', encoding='utf-8') as f:
                content = await f.read()
                character_id = content.strip()

        # 2. Delete session directory
        try:
            shutil.rmtree(session_dir)
            log_debug(f"Session directory {session_id} deleted")
        except Exception as e:
            log_warning(f"Error deleting session directory {session_id}: {e}")
            # Continue to try resetting character status even if file deletion failed partially

        # 3. Reset character status to ACTIVE
        if character_id and character_id != "Unknown":
            try:
                # We use a fresh service instance to avoid side effects
                char_service = CharacterService(character_id, data_service=character_data_service)
                await char_service.load()
                # Force load to ensure we have the latest data
                if char_service.character_data:
                    char_service.character_data.status = CharacterStatus.ACTIVE
                    await char_service.save()
                    log_debug(f"Character {character_id} status reset to ACTIVE")
            except Exception as e:
                log_warning(f"Failed to reset character {character_id} status: {e}")



    @staticmethod
    async def get_session_info(session_id: str) -> SessionMetadata:
        """
        ### get_session_info
        **Description:** Asynchronously retrieves metadata (character ID and scenario name) for a given session ID.

        **Parameters:**
        - `session_id` (str): The unique session identifier.

        **Returns:**
        - `SessionMetadata`: Object containing `character_id` and `scenario_name`.

        **Raises:**
        - `SessionNotFoundError`: If the session directory does not exist.
        - `FileNotFoundError`: If metadata files are missing within the session directory.
        """
        import aiofiles
        session_dir = pathlib.Path(get_data_dir()) / "sessions" / session_id

        if not session_dir.exists() or not session_dir.is_dir():
            raise SessionNotFoundError(f"The session '{session_id}' does not exist.")

        # Retrieve the character ID
        character_file = session_dir / "character.txt"
        if not character_file.exists():
            raise FileNotFoundError(f"Missing character.txt file for session '{session_id}'.")

        async with aiofiles.open(character_file, mode='r', encoding='utf-8') as f:
            content = await f.read()
            character_id = content.strip()

        # Retrieve the scenario name
        scenario_file = session_dir / "scenario.txt"
        if not scenario_file.exists():
            raise FileNotFoundError(f"Missing scenario.txt file for session '{session_id}'.")

        async with aiofiles.open(scenario_file, mode='r', encoding='utf-8') as f:
            content = await f.read()
            scenario_name = content.strip()

        log_debug("Session information retrieved", action="get_session_info", session_id=session_id, character_id=character_id, scenario_name=scenario_name)
        return SessionMetadata(
            character_id=character_id,
            scenario_name=scenario_name
        )

    @staticmethod
    async def check_existing_session(scenario_name: str, character_id: str) -> bool:
        """
        ### check_existing_session
        **Description:** Asynchronously checks if a session already exists for a specific combination of scenario and character.

        **Parameters:**
        - `scenario_name` (str): The name of the scenario.
        - `character_id` (str): The character identifier.

        **Returns:**
        - `bool`: True if a matching session exists, False otherwise.
        """
        import aiofiles
        sessions_dir = pathlib.Path(get_data_dir()) / "sessions"
        
        if not sessions_dir.exists() or not sessions_dir.is_dir():
            return False

        # Browse all session folders
        for session_folder in sessions_dir.iterdir():
            if session_folder.is_dir():
                try:
                    # Check for scenario.txt and character.txt files
                    scenario_file = session_folder / "scenario.txt"
                    character_file = session_folder / "character.txt"

                    if scenario_file.exists() and character_file.exists():
                        async with aiofiles.open(scenario_file, mode='r', encoding='utf-8') as f:
                            content = await f.read()
                            existing_scenario = content.strip()
                        
                        async with aiofiles.open(character_file, mode='r', encoding='utf-8') as f:
                            content = await f.read()
                            existing_character = content.strip()

                        # Compare with provided parameters
                        if existing_scenario == scenario_name and existing_character == character_id:
                            log_debug("Existing session found", 
                                      action="check_existing_session", 
                                      session_id=session_folder.name, 
                                      scenario_name=scenario_name, 
                                      character_id=character_id)
                            return True

                except Exception:
                    # Ignore invalid folders or read errors
                    continue

        return False

    async def load_current_scenario_content(self) -> str:
        """
        Loads the text content of the current scenario for the Oracle.
        """
        if not self.scenario_id:
            await self._load_session_data()
            
        # Get scenario definition from ScenarioService
        from back.services.scenario_service import ScenarioService
        
        try:
            # We assume self.scenario_id is the filename
            scenario_content = await ScenarioService.get_scenario_details(self.scenario_id)
            return scenario_content
        except FileNotFoundError:
            raise ScenarioNotFoundError(f"Scenario {self.scenario_id} not found") from None

    async def save_timeline_events(self, events: List[TimelineEvent], overwrite: bool = False) -> None:
        """
        Saves a list of TimelineEvent objects to `history_timeline.jsonl`.
        
        :param events: List of events to save.
        :param overwrite: If True, overwrites the file. If False (default), appends.
        """
        import json

        import aiofiles
        history_path = os.path.join(get_data_dir(), "sessions", self.session_id, "history_timeline.jsonl")
        
        mode = 'w' if overwrite else 'a'
        async with aiofiles.open(history_path, mode, encoding='utf-8') as f:
            for event in events:
                # model_dump_json() is Pydantic V2
                await f.write(event.model_dump_json() + "\n")

    async def load_timeline_events(self) -> List[TimelineEvent]:
        """
        Loads TimelineEvent objects from `history_timeline.jsonl`.
        """
        import json

        import aiofiles

        from back.models.api.game import TimelineEvent

        history_path = os.path.join(get_data_dir(), "sessions", self.session_id, "history_timeline.jsonl")
        if not os.path.exists(history_path):
            return []
            
        events = []
        async with aiofiles.open(history_path, 'r', encoding='utf-8') as f:
            async for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        events.append(TimelineEvent(**data))
                    except Exception as e:
                        log_debug(f"Error skipping invalid timeline line: {e}")
        return events

    async def save_history(self, kind: str, messages: list) -> None:
        """
        ### save_history
        **Description:** Saves the message history for a specific mode (narrative or combat) to a JSONL file.
        **Parameters:**
        - `kind` (str): The type of history ("narrative" or "combat").
        - `messages` (list): A list of `ModelMessage` objects to save.
        
        **Returns:** None.
        """
        history_path = os.path.join(get_data_dir(), "sessions", self.session_id, f"history_{kind}.jsonl")
        store = PydanticJsonlStore(history_path)
        await store.save_pydantic_history_async(messages)



    async def load_history_raw_json(self, kind: str) -> List[Dict[str, Any]]:
        """
        ### load_history_raw_json
        **Description:** Loads the message history for a specific mode as raw JSON dictionaries.
        Useful for API responses or debugging.

        **Parameters:**
        - `kind` (str): The type of history ("narrative" or "combat").

        **Returns:**
        - `List[Dict[str, Any]]`: A list of message dictionaries. Returns an empty list if the file does not exist.
        """
        history_path = os.path.join(get_data_dir(), "sessions", self.session_id, f"history_{kind}.jsonl")
        if os.path.exists(history_path):
            store = PydanticJsonlStore(history_path)
            return await store.load_raw_json_history_async()
        return []

    async def save_history_llm(self, kind: str, messages: List[ModelMessage]) -> None:
        """
        ### save_history_llm
        **Description:** Saves the summarized message history for LLM context.
        This history is separate from the full UI history.

        **Parameters:**
        - `kind` (str): The type of history ("narrative" or "combat").
        - `messages` (list): A list of `ModelMessage` objects to save.
        """
        history_path = os.path.join(get_data_dir(), "sessions", self.session_id, f"history_{kind}_llm.jsonl")
        store = PydanticJsonlStore(history_path)
        await store.save_pydantic_history_async(messages)

    async def load_history_llm(self, kind: str) -> List[ModelMessage]:
        """
        ### load_history_llm
        **Description:** Loads the summarized message history for LLM context.

        **Parameters:**
        - `kind` (str): The type of history ("narrative" or "combat").

        **Returns:**
        - `List[ModelMessage]`: A list of loaded `ModelMessage` objects.
        """
        history_path = os.path.join(get_data_dir(), "sessions", self.session_id, f"history_{kind}_llm.jsonl")
        if os.path.exists(history_path):
            store = PydanticJsonlStore(history_path)
            return await store.load_pydantic_history_async()
        return []

    async def get_last_n_messages(self, kind: str, n: int) -> List[ModelMessage]:
        """
        ### get_last_n_messages
        **Description:** Retrieves the last n messages from the LLM history.

        **Parameters:**
        - `kind` (str): The type of history ("narrative" or "combat").
        - `n` (int): The number of messages to retrieve.

        **Returns:**
        - `List[ModelMessage]`: A list of the last n `ModelMessage` objects.
        """
        history = await self.load_history_llm(kind)
        return history[-n:] if history else []

    async def update_game_state(self, game_state: GameState) -> None:
        """
        ### update_game_state
        **Description:** Saves the current game state object to `game_state.json`.

        **Parameters:**
        - `game_state` (GameState): The GameState object to save.
        
        **Returns:** None.
        """
        import json

        import aiofiles
        state_path = os.path.join(get_data_dir(), "sessions", self.session_id, "game_state.json")
        async with aiofiles.open(state_path, 'w', encoding='utf-8') as f:
            # Use mode='json' to handle UUID serialization automatically
            await f.write(json.dumps(game_state.model_dump(mode='json'), ensure_ascii=False, indent=2))

    async def load_game_state(self) -> Optional[Any]:
        """
        ### load_game_state
        **Description:** Loads the game state from `game_state.json`.

        **Returns:**
        - `Optional[GameState]`: The loaded GameState object, or None if the file does not exist.
        """
        import json

        import aiofiles

        from back.models.domain.game_state import GameState
        state_path = os.path.join(get_data_dir(), "sessions", self.session_id, "game_state.json")
        if os.path.exists(state_path):
            async with aiofiles.open(state_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            return GameState(**data)
        return None

