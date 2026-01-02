"""
Service specialized for loading and saving character data.
SRP Compliance - Single Responsibility: persistent data management.
"""

import json
import os
from typing import List, Optional

import aiofiles

from back.config import get_data_dir
from back.models.domain.character import Character
from back.utils.logger import log_debug


class CharacterDataService:
    """
    ### CharacterDataService
    **Description:** Service specialized in loading and saving character data.
    **Single Responsibility:** Management of Character data persistence operations.
    """
    
    def __init__(self):
        """
        ### __init__
        **Description:** Initializes the character data service.
        """
        pass

    def _get_characters_dir(self) -> str:
        return os.path.join(get_data_dir(), "characters")

    def _get_character_file_path(self, character_id: str) -> str:
        if not character_id or not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("Character ID must be a non-empty string")
        return os.path.join(self._get_characters_dir(), f"{character_id}.json")
    
    async def load_character(self, character_id: str) -> Character:
        """
        ### load_character
        **Description:** Loads a character from its identifier.
        **Parameters:**
        - `character_id` (str): Character identifier
        **Returns:** Loaded Character object
        **Raises:** FileNotFoundError if the character does not exist
        """
        if not character_id:
            raise ValueError("No character_id provided")

        filepath = self._get_character_file_path(character_id)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Character {character_id} does not exist.")

        try:
            async with aiofiles.open(filepath, "r", encoding="utf-8") as file:
                content = await file.read()
                character_data = json.loads(content)

            log_debug("Character loaded successfully", action="load_character", character_id=character_id)
            return Character(**character_data)

        except json.JSONDecodeError as e:
            log_debug("JSON decoding error",
                     action="load_character_error",
                     character_id=character_id,
                     error=str(e))
            raise ValueError(f"Corrupted JSON file for character {character_id}: {str(e)}")
        except Exception as e:
            log_debug("Error during loading",
                     action="load_character_error",
                     character_id=character_id,
                     error=str(e))
            raise
    
    async def save_character(self, character: Character, character_id: Optional[str] = None) -> Character:
        """
        ### save_character
        **Description:** Saves a character to persistent storage.
        **Parameters:**
        - `character` (Character): Character object to save
        - `character_id` (Optional[str]): Character identifier (optional if present in character object)
        **Returns:** The saved character (with potential merge)
        """
        # If character_id is not provided, try to retrieve it from the character object
        target_id = character_id
        if not target_id and hasattr(character, 'id'):
            target_id = str(character.id)
            
        if not target_id:
            raise ValueError("No character_id provided and impossible to retrieve it from Character object")
        
        filepath = self._get_character_file_path(target_id)

        try:
            # Load existing data if file exists for merging
            existing_data: dict = {}
            if os.path.exists(filepath):
                try:
                    async with aiofiles.open(filepath, "r", encoding="utf-8") as file:
                        content = await file.read()
                        existing_data = json.loads(content)
                except (json.JSONDecodeError, Exception) as e:
                    log_debug("Error reading existing file, recreating",
                             action="save_character_warning",
                             character_id=target_id,
                             error=str(e))
                    existing_data = {}

            # Convert Character to dict with mode='json' for JSON serialization
            character_dict: dict = character.model_dump(mode='json')

            # Merge data (new data has priority)
            merged_data: dict = {**existing_data, **character_dict}

            # Create directory if necessary
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            async with aiofiles.open(filepath, "w", encoding="utf-8") as file:
                await file.write(json.dumps(merged_data, ensure_ascii=False, indent=2))

            log_debug("Character saved", action="save_character", character_id=target_id)
            
            return Character(**merged_data)

        except Exception as e:
            log_debug("Error during save",
                     action="save_character_error",
                     character_id=target_id,
                     error=str(e))
            raise
    
    async def get_all_characters(self) -> List[Character]:
        """
        ### get_all_characters
        **Description:** Retrieves the list of all available characters.
        **Returns:** List of Character objects
        """
        characters = []
        characters_dir = self._get_characters_dir()
        
        if not os.path.exists(characters_dir):
            log_debug("Characters directory does not exist", action="get_all_characters")
            return characters
        
        # os.listdir is sync, but acceptable for directory listing for now? 
        # Ideally use aiofiles.os but aiofiles doesn't wrap listdir directly in a convenient way for 3.12 without loop issues sometimes.
        # But 'scandir' is better. For now keeping os.listdir but loading individual files async.
        
        for filename in os.listdir(characters_dir):
            if filename.endswith(".json"):
                character_id = filename[:-5]  # Remove .json extension
                try:
                    character = await self.load_character(character_id)
                    characters.append(character)
                except (FileNotFoundError, ValueError) as e:
                    log_debug("Error loading character", 
                             action="get_all_characters_error", 
                             file_name=filename, 
                             error=str(e))
                    continue
        
        log_debug("Loading all characters", action="get_all_characters", count=len(characters))
        return characters
    
    async def get_character_by_id(self, character_id: str) -> Character:
        """
        ### get_character_by_id
        **Description:** Retrieves a character from its identifier.
        **Parameters:**
        - `character_id` (str): Character identifier
        **Returns:** Character object
        **Raises:** FileNotFoundError if the character does not exist
        """
        return await self.load_character(character_id)
    
    # character_exists can remain sync as it only checks file existence? 
    # Or should it be async for consistency? 
    # Checking file existence is fast, but better to be consistent if aiming for "Strictly Async".
    # os.path.exists is sync. aiofiles.os.path.exists wraps it.
    
    async def character_exists(self, character_id: str) -> bool:
        """
        ### character_exists
        **Description:** Checks if a character exists.
        **Parameters:**
        - `character_id` (str): Character identifier
        **Returns:** True if the character exists, False otherwise
        """
        try:
            filepath = self._get_character_file_path(character_id)
            # aiofiles.os.path does exist
            return os.path.exists(filepath) 
        except ValueError:
            return False

    async def delete_character(self, character_id: str) -> None:
        """
        ### delete_character
        **Description:** Deletes a character's file.
        **Parameters:**
        - `character_id` (str): Character identifier
        **Returns:** None
        """
        filepath = self._get_character_file_path(character_id)
        if os.path.exists(filepath):
            os.remove(filepath) # TODO: Use async os wrapper if strict strictness required, but remove is fast.
            log_debug("Character deleted", action="delete_character", character_id=character_id)
        else:
            log_debug("Deletion ignored: character not found", action="delete_character", character_id=character_id)
