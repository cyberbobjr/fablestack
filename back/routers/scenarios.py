"""
Scenario router using PydanticAI GM agent.
Final version after complete migration from Haystack to PydanticAI.
"""

from typing import Annotated, Dict, List

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException

from back.auth_dependencies import get_current_admin_user
from back.models.api.game import (ScenarioGenerationRequest, ScenarioList,
                                  ScenarioStatus)
from back.models.domain.user import User
from back.services.scenario_service import ScenarioService
from back.utils.logger import log_debug

router = APIRouter(tags=["scenario"])

@router.get(
    "/", 
    response_model=ScenarioList,
    summary="List Scenarios",
    description="List all available scenarios files.",
    responses={
        200: {
            "description": "List of scenarios",
            "content": {"application/json": {"example": {
                "scenarios": [{
                    "id": "scen_pierres_passe",
                    "title": "Les Pierres du Passé",
                    "name": "Les_Pierres_du_Passe.md",
                    "status": "available"
                }]
            }}}
        }
    }
)
async def list_scenarios() -> ScenarioList:
    """
    List available scenarios.

    **Response:**
    ```json
    {
        "scenarios": [
            {
                "id": "scen_pierres_passe",
                "title": "Les Pierres du Passé",
                "name": "Les_Pierres_du_Passe.md",
                "status": "available",
                "session_id": null,
                "scenario_name": null,
                "character_name": null
            }
        ]
    }
    ```
    """
    log_debug("Endpoint call: scenarios/list_scenarios")
    scenarios: ScenarioList = await ScenarioService.list_scenarios()
    return scenarios

@router.post(
    "/",
    response_model=ScenarioStatus,
    summary="Create Scenario",
    description="Generate and create a new scenario based on a description.",
    status_code=201
)
async def create_scenario(
    request: ScenarioGenerationRequest,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_current_admin_user)
) -> ScenarioStatus:
    """
    Generate and create a new scenario using AI.
    Starts the generation in the background and returns status 'creating'.
    """
    log_debug("Endpoint call: scenarios/create_scenario (Async)")
    try:
        # Initiate creation (create placeholder file)
        status = await ScenarioService.initiate_creation(request.description)
        
        # Schedule the actual processing
        background_tasks.add_task(
            ScenarioService.process_creation, 
            request.description, 
            status.name
        )
        
        return status
        
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        import traceback
        log_debug(f"Error creating scenario: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/{scenario_file}",
    status_code=204,
    summary="Delete Scenario",
    description="Delete an existing scenario file."
)
async def delete_scenario(
    scenario_file: str,
    admin_user: User = Depends(get_current_admin_user)
) -> None:
    """
    Delete a scenario by its filename.
    """
    log_debug("Endpoint call: scenarios/delete_scenario", filename=scenario_file)
    try:
        await ScenarioService.delete_scenario(scenario_file)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        log_debug(f"Error deleting scenario: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/{scenario_file}",
    response_model=ScenarioStatus,
    summary="Update Scenario",
    description="Update the content of an existing scenario file."
)
async def update_scenario(
    scenario_file: str,
    content: str = Body(..., media_type="text/plain"),
    admin_user: User = Depends(get_current_admin_user)
) -> ScenarioStatus:
    """
    Update a scenario content.
    """
    log_debug("Endpoint call: scenarios/update_scenario", filename=scenario_file)
    try:
        return await ScenarioService.update_scenario(scenario_file, content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        log_debug(f"Error updating scenario: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get(
    "/{scenario_file}", 
    response_model=str,
    summary="Get Scenario Content",
    description="Retrieve the raw Markdown content of a scenario file.",
    responses={
        200: {
            "description": "Scenario Content",
            "content": {"text/plain": {"example": "# Scenario Title\n\n## Context\n..."}}
        },
        404: {"description": "Scenario not found"}
    }
)
async def get_scenario_details(scenario_file: str) -> str:
    """
    Retrieve the content of a scenario (Markdown file) by its filename.

    **Parameters:**
    - `scenario_file` (str): The filename of the scenario (e.g., Les_Pierres_du_Passe.md).

    **Returns:**
    The Markdown content of the scenario file as a string.

    **Raises:**
    - HTTPException 404: If the scenario file does not exist.

    **Response:**
    ```
    # Scenario: The Stones of the Past

    ## Context
    The story takes place in the year 2955 of the Third Age...

    ## 1. Locations
    ### Esgalbar Village
    - **Description**: Small wooden houses village...
    ```
    """
    log_debug("Endpoint call: scenarios/get_scenario_details", scenario_file=scenario_file)
    try:
        content: str = await ScenarioService.get_scenario_details(scenario_file)
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_file}' not found.")





