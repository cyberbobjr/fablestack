from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_injector import Injected
from pydantic import BaseModel

from back.auth_dependencies import get_current_active_user
from back.config import get_image_generation_config
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.character import Character
from back.models.domain.user import User
from back.services.character_data_service import CharacterDataService
from back.services.localization_service import LocalizationService
from back.utils.exceptions import InternalServerError
from back.utils.logger import log_debug, log_error


class CharacterResponse(BaseModel):
    """Response model for character data"""
    character: Character
    status: str

router = APIRouter(tags=["characters"])

@router.get(
    "/", 
    response_model=List[Character],
    summary="List Characters",
    description="Retrieve the list of all available characters (complete or draft).",
    responses={
        200: {
            "description": "List of characters",
            "content": {"application/json": {"example": [{
                "id": "d7763165-4c03-4c8d-9bc6-6a2568b79eb3",
                "name": "Aragorn",
                "race": "Human",
                "culture": "Gondor",
                "level": 5,
                "status": "active"
            }]}}
        }
    }
)
async def list_characters(
    data_service: CharacterDataService = Injected(CharacterDataService)
):
    """
    Retrieve the list of all available characters in the system.
    """
    
    try:
        characters = await data_service.get_all_characters()
        return characters
        
    except Exception as e:
        log_error("Error during fetch characters list", 
                 action="list_characters_error", 
                 error=str(e))
        raise InternalServerError(f"Error during fetch characters list: {str(e)}")


@router.get(
    "/{character_id}",
    response_model=CharacterResponse,
    summary="Get Character Details",
    description="Retrieves full details of a character by ID.",
    responses={
        200: {"description": "Character details"},
        404: {"description": "Character not found"}
    }
)
async def get_character_detail(
    character_id: str,
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> CharacterResponse:
    try:
        
        character = await data_service.load_character(character_id)
        if character is None:
            raise HTTPException(status_code=404, detail=f"Character with id '{character_id}' not found")

        return CharacterResponse(
            character=character,
            status="loaded"
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_error("Character retrieval failed", error=str(e), character_id=character_id)
        raise HTTPException(status_code=500, detail=f"Character retrieval failed: {str(e)}")


@router.delete(
    "/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Character",
    description="Permanently deletes a character by ID.",
    responses={
        204: {"description": "Character deleted"},
        404: {"description": "Character not found"}
    }
)
async def delete_character(
    character_id: str,
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> None:
    try:
        
        # Verify exists
        try:
            await data_service.load_character(character_id)
        except FileNotFoundError:
             raise HTTPException(status_code=404, detail=f"Character with id '{character_id}' not found")

        await data_service.delete_character(character_id)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Character with id '{character_id}' not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Character deletion failed", error=str(e), character_id=character_id)
        raise HTTPException(status_code=500, detail=f"Character deletion failed: {str(e)}")


@router.post(
    "/{character_id}/portrait",
    response_model=CharacterResponse,
    summary="Regenerate Portrait",
    description="Triggers image generation to create a new portrait for the character.",
    responses={
        200: {"description": "Portrait updated"},
        404: {"description": "Character not found"}
    }
)
async def regenerate_portrait(
    character_id: str,
    data_service: CharacterDataService = Injected(CharacterDataService),
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol),
    current_user: User = Depends(get_current_active_user)
) -> CharacterResponse:
    """
    Regenerates the character portrait.
    """
    try:
        from back.services.image_generation_service import \
            ImageGenerationService

        img_config = get_image_generation_config()
        daily_limit = img_config.get("daily_limit", 5)  # Default to 5 if not in config
        
        if daily_limit > 0:
            now = datetime.now(timezone.utc)
            today = now.date()
            
            last_date = current_user.last_portrait_date.date() if current_user.last_portrait_date else None
            
            # Reset counter if new day
            if last_date != today:
                current_user.daily_portrait_count = 0
                # Don't update date yet, only on usage, but we need to reset count in memory
            
            if current_user.daily_portrait_count >= daily_limit:
                 # Get localized error message
                 lang: str = current_user.preferences.language
                 msg: str = LocalizationService.get_message(
                     "portrait_rate_limit",
                     lang,
                     limit=daily_limit
                 )

                 raise HTTPException(
                     status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
                     detail=msg
                 )

        character = await data_service.load_character(character_id)
        
        if not character:
            raise HTTPException(status_code=404, detail=f"Character with id '{character_id}' not found")
            
        image_service = ImageGenerationService()
        # Convert character model to dict for service
        char_data = character.model_dump()
        # Ensure ID is present as string
        char_data["id"] = str(character.id)
        
        portrait_url = await image_service.generate_character_portrait(char_data)
        
        if portrait_url:
            character.portrait_url = portrait_url
            character.update_timestamp()
            await data_service.save_character(character, character_id)
            
            # Update User Usage
            current_user.daily_portrait_count += 1
            current_user.last_portrait_date = datetime.now(timezone.utc)
            await user_manager.update(current_user)
            
        return CharacterResponse(
            character=character,
            status="updated"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Portrait regeneration failed", error=str(e), character_id=character_id)
        raise HTTPException(status_code=500, detail=f"Portrait regeneration failed: {str(e)}")
