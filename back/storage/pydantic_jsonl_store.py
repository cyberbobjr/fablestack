"""
JSONL store adapted for PydanticAI.
Compatible with PydanticAI message formats while maintaining the JsonlChatMessageStore interface.
"""

from __future__ import annotations

import os
from typing import List, Any, Dict

from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelMessage

from back.utils.logger import log_debug


class PydanticJsonlStore:
    """
    ### PydanticJsonlStore
    **Description:** JSONL store adapted for PydanticAI, compatible with PydanticAI message formats.
    **Parameters:**
    - `filepath` (str): Path to the JSONL storage file.
    **Methods:**
    - `save_pydantic_history(messages)`: Serializes and saves a list of PydanticAI messages to the JSONL file.
    - `load_pydantic_history()`: Reloads the complete PydanticAI history from the JSONL file.
    """
    
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        log_debug("Initializing PydanticJsonlStore", action="init_store", filepath=os.path.abspath(filepath))
        self._ensure_file()

    def _ensure_file(self) -> None:
        """
        ### _ensure_file
        **Description:** Creates the directory and storage file if they do not exist.
        """
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8"): 
                pass
            log_debug("Creating PydanticAI session file", action="create_session_file", filepath=os.path.abspath(self.filepath))
        else:
            log_debug("Existing PydanticAI session file", action="existing_session_file", filepath=os.path.abspath(self.filepath))

    def save_pydantic_history(self, messages: List[ModelMessage]) -> None:
        """
        ### save_pydantic_history
        **Description:** Serializes and saves a list of PydanticAI messages to the JSONL file, using ModelMessagesTypeAdapter.dump_json as recommended in the official documentation.
        **Parameters:**
        - `messages` (List[ModelMessage]): List of PydanticAI messages to save.
        """
        import json

        # Use dump_json for consistent serialization with PydanticAI
        json_bytes: bytes = ModelMessagesTypeAdapter.dump_json(messages, indent=2)
        json_str: str = json_bytes.decode('utf-8')

        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
        log_debug("PydanticAI history saved (ModelMessagesTypeAdapter.dump_json)", action="save_pydantic_history", filepath=os.path.abspath(self.filepath), count=len(messages))

    def load_pydantic_history(self) -> List[ModelMessage]:
        """
        ### load_pydantic_history
        **Description:** Reloads the complete PydanticAI history from the JSONL file, using ModelMessagesTypeAdapter.validate_python as in the official documentation.
        **Returns:** List of deserialized PydanticAI messages (List[ModelMessage]).
        """
        import json
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content: str = f.read().strip()
                if not content:  # Empty file
                    return []
                data: Any = json.loads(content)

            history: List[ModelMessage] = ModelMessagesTypeAdapter.validate_python(data)
            log_debug("PydanticAI history reloaded (validate_python)", action="load_pydantic_history", filepath=os.path.abspath(self.filepath), count=len(history))
            return history
        except Exception as e:
            log_debug("Error reloading PydanticAI history", error=str(e), filepath=os.path.abspath(self.filepath))
            return []

    def load_raw_json_history(self) -> List[Dict[str, Any]]:
        """
        ### load_raw_json_history
        **Description:** Reloads the complete PydanticAI history from the JSONL file as raw JSON data, without validation.
        **Returns:** List of raw JSON message dictionaries.
        """
        import json
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content: str = f.read().strip()
                if not content:  # Empty file
                    return []
                data: Any = json.loads(content)

            log_debug("Raw JSON history reloaded", action="load_raw_json_history", filepath=os.path.abspath(self.filepath), count=len(data) if isinstance(data, list) else 0)
            return data if isinstance(data, list) else []
        except Exception as e:
            log_debug("Error reloading raw JSON history", error=str(e), filepath=os.path.abspath(self.filepath))
            return []

    # Only modern PydanticAI methods are retained.

    async def save_pydantic_history_async(self, messages: List[ModelMessage]) -> None:
        """
        ### save_pydantic_history_async
        **Description:** Asynchronously serializes and saves a list of PydanticAI messages to the JSONL file.
        **Parameters:**
        - `messages` (List[ModelMessage]): List of PydanticAI messages to save.
        """
        import json
        import aiofiles

        # Use dump_json for consistent serialization with PydanticAI
        json_bytes: bytes = ModelMessagesTypeAdapter.dump_json(messages, indent=2)
        json_str: str = json_bytes.decode('utf-8')

        async with aiofiles.open(self.filepath, "w", encoding="utf-8") as f:
            await f.write(json_str)
        log_debug("PydanticAI history saved async", action="save_pydantic_history_async", filepath=os.path.abspath(self.filepath), count=len(messages))

    async def load_pydantic_history_async(self) -> List[ModelMessage]:
        """
        ### load_pydantic_history_async
        **Description:** Asynchronously reloads the complete PydanticAI history from the JSONL file.
        **Returns:** List of deserialized PydanticAI messages (List[ModelMessage]).
        """
        import json
        import aiofiles
        
        if not os.path.exists(self.filepath):
            return []
        try:
            async with aiofiles.open(self.filepath, "r", encoding="utf-8") as f:
                content: str = (await f.read()).strip()
                if not content:  # Empty file
                    return []
                data: Any = json.loads(content)

            history: List[ModelMessage] = ModelMessagesTypeAdapter.validate_python(data)
            log_debug("PydanticAI history reloaded async", action="load_pydantic_history_async", filepath=os.path.abspath(self.filepath), count=len(history))
            return history
        except Exception as e:
            log_debug("Error reloading PydanticAI history async", error=str(e), filepath=os.path.abspath(self.filepath))
            return []

    async def load_raw_json_history_async(self) -> List[Dict[str, Any]]:
        """
        ### load_raw_json_history_async
        **Description:** Asynchronously reloads the complete PydanticAI history as raw JSON data.
        **Returns:** List of raw JSON message dictionaries.
        """
        import json
        import aiofiles
        
        if not os.path.exists(self.filepath):
            return []
        try:
            async with aiofiles.open(self.filepath, "r", encoding="utf-8") as f:
                content: str = (await f.read()).strip()
                if not content:  # Empty file
                    return []
                data: Any = json.loads(content)

            log_debug("Raw JSON history reloaded async", action="load_raw_json_history_async", filepath=os.path.abspath(self.filepath), count=len(data) if isinstance(data, list) else 0)
            return data if isinstance(data, list) else []
        except Exception as e:
            log_debug("Error reloading raw JSON history async", error=str(e), filepath=os.path.abspath(self.filepath))
            return []
