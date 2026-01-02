"""
Translation Agent for asynchronous localization of game content.
"""

import asyncio
import json
import pathlib
from typing import Any, Dict, Optional

import aiofiles
from pydantic import BaseModel
from pydantic_ai import Agent

from back.config import get_data_dir, get_llm_config
from back.utils.logger import log_debug, log_error, log_info


class TranslationData(BaseModel):
    name: str
    description: str

class TranslationAgent:
    """
    ### TranslationAgent
    **Description:** Agent responsible for translating game content (specifically equipment) 
    from English to French asynchronously.
    It ensures that the tone matches the world lore setting.
    """

    def __init__(self) -> None:
        """
        Initialize the translation agent.
        """
        from back.config import config
        self.llm_config = get_llm_config()
        self._lock = asyncio.Lock()
        world_lore = config.world.lore

        # specialized system prompt
        self.system_prompt = f"""
You are an expert translator and lore-master for a Role-Playing Game.
Your task is to translate equipment names and descriptions from English to French.
World Lore: {world_lore}
GUIDELINES:
1. **Accuracy**: Preserve the meaning and mechanical implication of the description.
"""
        
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        
        provider = OpenAIProvider(
            base_url=self.llm_config.api_endpoint,
            api_key=self.llm_config.api_key
        )
        model = OpenAIChatModel(
            model_name=self.llm_config.model,
            provider=provider
        )
        
        self.agent = Agent(
            model=model,
            system_prompt=self.system_prompt
        )

    async def translate_item(self, item_id: str, name_en: str, description_en: str) -> None:
        """
        ### translate_item
        **Description:** Translates an item's details and updates the translation file.
        This method is intended to be fire-and-forget (run in background).

        **Parameters:**
        - `item_id` (str): The unique ID of the item.
        - `name_en` (str): The English name.
        - `description_en` (str): The English description.
        """
        log_info(f"Starting translation for item {item_id}...", item_id=item_id)
        
        user_prompt = f"""
Translate this item:
ID: {item_id}
Name: {name_en}
Description: {description_en}
"""
        try:
            # Call LLM
            result = await self.agent.run(user_prompt, output_type=list[TranslationData])
            translations = result.output
            
            if not translations:
                log_error(f"No translation returned for {item_id}")
                return

            translation_data = translations[0]
            name_fr = translation_data.name
            description_fr = translation_data.description
            
            # Update file
            await self._update_translation_file(item_id, name_fr, description_fr)
            log_info(f"Translation completed for {item_id}", name_fr=name_fr)
            
        except Exception as e:
            log_error(f"Error during translation of {item_id}: {e}")

    async def _update_translation_file(self, item_id: str, name_fr: str, description_fr: str) -> None:
        """
        ### _update_translation_file
        **Description:** Safely updates the `fr.json` file with the new translation.
        """
        file_path = pathlib.Path(get_data_dir()) / "translations" / "fr.json"
        
        async with self._lock:
            try:
                # Read existing data
                data = {}
                if file_path.exists():
                    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                        content = await f.read()
                        if content:
                            data = json.loads(content)
                
                # Ensure structure exists
                if "equipment_details" not in data:
                    data["equipment_details"] = {}
                
                # Update data
                data["equipment_details"][item_id] = {
                    "name": name_fr,
                    "description": description_fr
                }
                
                # Write back
                async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=4))
                    
            except Exception as e:
                log_error(f"Failed to write translation file: {e}")
