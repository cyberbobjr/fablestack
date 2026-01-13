"""
Game Session router for managing game sessions with LLM gameplay.
Handles session creation, listing, playing, and history management.
"""

import traceback
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi_injector import Injected
from pydantic_ai.messages import ModelMessagesTypeAdapter

from back.agents.translation_agent import TranslationAgent
from back.auth_dependencies import get_current_active_user
from back.models.api.game import (ActiveSessionsResponse,PlayScenarioRequest,
                                    RestoreRequest,
                                  ScenarioHistoryResponse, SessionInfo,
                                  StartScenarioRequest, StartScenarioResponse)
from back.models.domain.character import Character
from back.models.domain.game_state import GameState
from back.models.domain.user import User
from back.models.enums import CharacterStatus
from back.models.service.dtos import SessionStartResult, SessionSummary
from back.services.agent_runner_service import AgentRunnerService
from back.services.character_data_service import CharacterDataService
from back.services.equipment_service import EquipmentService
from back.services.game_session_service import (HISTORY_NARRATIVE,
                                                GameSessionService)
from back.services.races_data_service import RacesDataService
from back.services.scenario_service import ScenarioService
from back.services.settings_service import SettingsService
from back.utils.exceptions import (CharacterNotFoundError,
                                   ServiceNotInitializedError,
                                   SessionNotFoundError)
from back.utils.logger import log_debug, log_error

router = APIRouter(tags=["gamesession"])

@router.get(
    "/sessions", 
    response_model=ActiveSessionsResponse,
    summary="List Active Sessions",
    description="Retrieve the list of all active game sessions with scenario name and character name.",
    responses={
        200: {
            "description": "Active Sessions",
            "content": {"application/json": {"example": {
                "sessions": [{
                    "session_id": "12345678-1234-5678-9012-123456789abc",
                    "scenario_name": "The Dark Tower",
                    "scenario_id": "the_dark_tower",
                    "character_id": "87654321-4321-8765-2109-987654321def",
                    "character_name": "Galadhwen"
                }]
            }}}
        }
    }
)
async def list_active_sessions(
    current_user: User = Depends(get_current_active_user),
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> ActiveSessionsResponse:
    """
    Retrieve the list of all active game sessions with scenario name and character name.

    **Response:**
    ```json
    {
        "sessions": [
            {
                "session_id": "12345678-1234-5678-9012-123456789abc",
                "scenario_name": "Les_Pierres_du_Passe.md",
                "character_id": "87654321-4321-8765-2109-987654321def",
                "character_name": "Galadhwen"
            }
        ]
    }
    ```
    """
    log_debug("Endpoint call: gamesession/list_active_sessions")
    try:
        sessions: List[SessionSummary] = await GameSessionService.list_all_sessions()
        enriched_sessions: List[SessionInfo] = []
        # data_service injected
        for session in sessions:
            try:
                character: Optional[Character] = await data_service.load_character(str(session.character_id))
                character_name: str = character.name if character else "Unknown"
            except FileNotFoundError:
                character_name = "Unknown"
            except Exception as e:
                log_debug("Error loading character name", error=str(e), character_id=session.character_id)
                character_name = "Unknown"

            enriched_sessions.append(SessionInfo(
                session_id=str(session.session_id),
                scenario_id=await ScenarioService.get_scenario_id(session.scenario_id or "Unknown"),
                scenario_name=await ScenarioService.get_scenario_title(session.scenario_id or "Unknown"),
                character_id=str(session.character_id),
                character_name=character_name
            ))

        log_debug("Active sessions retrieved", count=len(enriched_sessions))
        return ActiveSessionsResponse(sessions=enriched_sessions)

    except Exception as e:
        log_error("Error listing active sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def _initialize_session(session_id: Optional[UUID], request: PlayScenarioRequest) -> Tuple[UUID, str]:
    """
    Initialize the session context.
    
    If session_id is None, starts a new session using the scenario and character provided in the request.
    If session_id is provided, validates that a message is present for continuation.
    
    Returns:
        Tuple[UUID, str]: The active session_id and the message to process.
    """
    if session_id is None:
        if not request.scenario_name or not request.character_id:
            raise HTTPException(status_code=400, detail="scenario_name and character_id are required to start a new session.")
        
        try:
            data_service = CharacterDataService()
            character_data = data_service.load_character(request.character_id)
            if character_data.status == CharacterStatus.DRAFT:
                raise HTTPException(status_code=400, detail="Cannot start a scenario with a character in creation.")
            
            session_info: SessionStartResult = await GameSessionService.start_scenario(request.scenario_name, UUID(request.character_id))
            new_session_id = UUID(session_info.session_id)
            message = "Start the scenario and present the initial situation."  # Message de démarrage fixe
            return new_session_id, message
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
    else:
        if not request.message:
            raise HTTPException(status_code=400, detail="message is required for continuing a session.")
        return session_id, request.message

@router.post(
    "/start", 
    response_model=StartScenarioResponse,
    summary="Start a Scenario",
    description="Initialize a new game session with a specific scenario and character.",
    responses={
        200: {
            "description": "Session Started",
            "content": {"application/json": {
                "example": {
                    "session_id": "123e4567-e89b-12d3-a456-426614174000",
                    "scenario_name": "The Dark Tower",
                    "character_id": "98765432-10ab-cdef-1234-567890abcdef",
                    "message": "Session started",
                    "llm_response": "Welcome to the adventure..."
                }
            }}
        },
        400: {"description": "Invalid character status"},
        403: {"description": "Character ownership error"},
        404: {"description": "Character not found"}
    }
)
async def start_scenario(
    request: StartScenarioRequest,
    current_user: User = Depends(get_current_active_user),
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> StartScenarioResponse:
    """
    Start a new game session with a scenario and character.
    """
    log_debug("Endpoint call: gamesession/start", scenario_name=request.scenario_name, character_id=request.character_id)
    try:
        # data_service injected
        character_data = await data_service.load_character(request.character_id)
        if character_data.status == CharacterStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Cannot start a scenario with a character in creation.")
        
        if character_data.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this character")

        session_info: SessionStartResult = await GameSessionService.start_scenario(
            request.scenario_name, 
            UUID(request.character_id), 
            character_data_service=data_service,
            user_id=str(current_user.id),
            # Note: start_scenario static method might need update if it uses creaate internally?
            # Ideally start_scenario calls create(). 
            # Check GameSessionService.start_scenario implementation.
        )
        new_session_id = session_info.session_id
        
        return StartScenarioResponse(
            session_id=new_session_id,
            scenario_name=request.scenario_name,
            character_id=request.character_id,
            message="Session started",
            llm_response="Session initialized. Redirecting..."
        )

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error("Error starting scenario", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/play-stream",
    summary="Play Scenario (Stream)",
    description="Send player input to the game engine and receive a streaming response (Server-Sent Events).",
    responses={
        200: {
            "description": "Stream of events",
            "content": {"text/event-stream": {}}
        },
        404: {"description": "Session not found"}
    }
)
async def play_stream(
    request: PlayScenarioRequest,
    data_service: CharacterDataService = Injected(CharacterDataService),
    equipment_service: EquipmentService = Injected(EquipmentService),
    settings_service: SettingsService = Injected(SettingsService),
    races_service: RacesDataService = Injected(RacesDataService),
    translation_agent: TranslationAgent = Injected(TranslationAgent),
    agent_runner: AgentRunnerService = Injected(AgentRunnerService)
):
    """
    Send a message to the GM (LLM) and stream the response using Server-Sent Events.
    Uses AgentRunnerService for true token-by-token streaming.

    **Parameters:**
    - `request` (PlayScenarioRequest): Request body containing session_id and player input.

    **Response (Stream):**
    Server-Sent Events (token, system_log, choices).
    """
    # log_debug("Endpoint call: gamesession/play_stream", session_id=request.session_id)

    try:
        session_id_str = request.session_id
        session_id = UUID(session_id_str)
        
        # Get session service
        session_service = await GameSessionService.load(
            session_id_str,
            character_data_service=data_service,
            equipment_service=equipment_service,
            settings_service=settings_service,
            races_service=races_service,
            translation_agent=translation_agent
        )
        
        # agent_runner injected
        
        # Ensure game state exists (Initialize if new session)
        game_state = await session_service.load_game_state()
        if game_state is None:
            log_debug(f"Initializing new game state for session {session_id}")
            game_state = GameState(
                session_mode="narrative",
                narrative_history_id="default",
                combat_history_id="default"
            )
            await session_service.update_game_state(game_state)
        
        return StreamingResponse(
            agent_runner.run_agent_stream(session_id, request.input, session_service),
            media_type="text/event-stream",
        )

    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CharacterNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceNotInitializedError as e:
        raise HTTPException(status_code=500, detail=f"Service initialization error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        log_error("Error preparing stream", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/history/{session_id}", 
    response_model=ScenarioHistoryResponse,
    summary="Get Session History",
    description="Retrieve the complete message history of the specified game session in raw JSON format.",
    responses={
        200: {"description": "History retrieved"},
        404: {"description": "Session not found"}
    }
)
async def get_scenario_history(
    session_id: UUID,
    data_service: CharacterDataService = Injected(CharacterDataService),
    equipment_service: EquipmentService = Injected(EquipmentService),
    settings_service: SettingsService = Injected(SettingsService),
    races_service: RacesDataService = Injected(RacesDataService),
    translation_agent: TranslationAgent = Injected(TranslationAgent)
) -> ScenarioHistoryResponse:
    """
    Retrieve the complete message history of the specified game session in raw JSON format.

    **Parameters:**
    - `session_id` (UUID): Game session identifier.

    **Response:**
    ```json
    {
        "history": [
            {
                "parts": [
                    {
                        "content": "Start the scenario and present the initial situation.",
                        "timestamp": "2025-06-21T12:00:00.000000Z",
                        "part_kind": "user-prompt"
                    }
                ],
                "kind": "request",
                "timestamp": "2025-06-21T12:00:00.000000Z"
            },
            {
                "parts": [
                    {
                        "content": "**Esgalbar, central square of the village**...",
                        "timestamp": "2025-06-21T12:00:05.123456Z",
                        "part_kind": "text"
                    }
                ],
                "kind": "response",
                "usage": {
                    "requests": 1,
                    "request_tokens": 1250,
                    "response_tokens": 567,
                    "total_tokens": 1817
                },
                "model_name": "deepseek-chat",
                "timestamp": "2025-06-21T12:00:05.123456Z"
            }
        ]
    }
    ```

    **Raises:**
    - HTTPException 404: If the session does not exist.
    - HTTPException 500: Error retrieving the history.

    **Note:** This route returns raw JSON without Pydantic validation to ensure format consistency with `/gamesession/play`.
    """
    log_debug("Endpoint call: gamesession/get_scenario_history", session_id=str(session_id))
    try:
        session = await GameSessionService.load(
            str(session_id),
            character_data_service=data_service,
            equipment_service=equipment_service,
            settings_service=settings_service,
            races_service=races_service,
            translation_agent=translation_agent
        )
        # Use new TimelineEvent history
        history = await session.load_timeline_events()
        return ScenarioHistoryResponse(history=history)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error("Error retrieving session history", error=str(e), session_id=str(session_id))
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


def _extract_timestamp(message: Dict[str, Any]) -> Optional[str]:
    """Helper to extract timestamp from a message dict."""
    if "timestamp" in message:
        return message["timestamp"]
    if "parts" in message:
        for part in message["parts"]:
            if "timestamp" in part:
                return part["timestamp"]
    return None

@router.post(
    "/history/{session_id}/restore",
    status_code=204,
    summary="Restore History",
    description="Restore history to a specific timestamp, deleting all subsequent events.",
    responses={
        204: {"description": "History restored"},
        404: {"description": "Session not found"}
    }
)
async def restore_history(
    session_id: UUID, 
    request: RestoreRequest,
    data_service: CharacterDataService = Injected(CharacterDataService),
    equipment_service: EquipmentService = Injected(EquipmentService),
    settings_service: SettingsService = Injected(SettingsService),
    races_service: RacesDataService = Injected(RacesDataService),
    translation_agent: TranslationAgent = Injected(TranslationAgent)
) -> None:
    """
    Restore request: truncate history from a given timestamp (inclusive).
    Deletes all events/messages with timestamp >= request.timestamp.
    """
    log_debug("Endpoint call: restore_history", session_id=str(session_id), timestamp=request.timestamp)
    try:
        session = await GameSessionService.load(
            str(session_id),
            character_data_service=data_service,
            equipment_service=equipment_service,
            settings_service=settings_service,
            races_service=races_service,
            translation_agent=translation_agent
        )
        target_timestamp = request.timestamp

        # 1. Load Timeline (Frontend)
        timeline = await session.load_timeline_events()
        # Filter: keep only events STRICTLY BEFORE the target timestamp
        new_timeline = [e for e in timeline if e.timestamp < target_timestamp]
        
        # 2. Load LLM History (Backend)
        # LLM history is raw JSON (list of dicts)
        llm_history = await session.load_history_raw_json(f"{HISTORY_NARRATIVE}_llm")
        new_llm_history = []
        for msg in llm_history:
            ts = _extract_timestamp(msg)
            if ts is None or ts < target_timestamp:
                new_llm_history.append(msg)
        
        await session.save_timeline_events(new_timeline, overwrite=True)
        
        pydantic_llm = ModelMessagesTypeAdapter.validate_python(new_llm_history)
        await session.save_history_llm(HISTORY_NARRATIVE, pydantic_llm)
        
        log_debug("Restoration complete", 
                  removed_timeline=len(timeline)-len(new_timeline),
                  removed_llm=len(llm_history)-len(new_llm_history))

    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error("Error restoring history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))




@router.delete(
    "/{session_id}", 
    status_code=204,
    summary="Delete Session",
    description="Delete a game session and reset the associated character status to ACTIVE.",
    responses={
        204: {"description": "Session deleted"},
        404: {"description": "Session not found"}
    }
)
async def delete_session(
    session_id: UUID,
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> None:
    """
    Delete a game session and reset the associated character status to ACTIVE.

    **Parameters:**
    - `session_id` (UUID): Game session identifier.

    **Response:**
    204 No Content

    **Raises:**
    - HTTPException 404: If the session does not exist.
    - HTTPException 500: Error during deletion.
    """
    log_debug("Endpoint call: gamesession/delete_session", session_id=str(session_id))
    try:
        await GameSessionService.delete_session(str(session_id), character_data_service=data_service)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error("Error deleting session", error=str(e), session_id=str(session_id))
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")