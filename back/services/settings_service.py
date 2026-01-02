import json
import os
from pathlib import Path
from typing import Optional

from back.config import get_data_dir, get_logger
from back.models.domain.preferences import UserPreferences

logger = get_logger(__name__)

class SettingsService:
    """
    ### SettingsService
    **Description:** Service for managing global user settings and preferences.
    Stores data in `gamedata/settings/user_preferences.json`.
    """

    SETTINGS_DIR = "settings"
    PREFERENCES_FILE = "user_preferences.json"

    def __init__(self):
        self.data_dir = Path(get_data_dir())
        self.settings_dir = self.data_dir / self.SETTINGS_DIR
        self.preferences_file = self.settings_dir / self.PREFERENCES_FILE
        self._ensure_settings_dir()

    def _ensure_settings_dir(self) -> None:
        """Ensure the settings directory exists."""
        if not self.settings_dir.exists():
            self.settings_dir.mkdir(parents=True, exist_ok=True)

    def get_preferences(self) -> UserPreferences:
        """
        ### get_preferences
        **Description:** Retrieve the current user preferences.
        **Returns:**
        - `UserPreferences`: The current preferences object.
        """
        if not self.preferences_file.exists():
            logger.debug("Preferences file not found, returning defaults.")
            return UserPreferences()

        try:
            content = self.preferences_file.read_text(encoding='utf-8')
            data = json.loads(content)
            return UserPreferences(**data)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Error reading preferences file: {e}")
            return UserPreferences()

    def update_preferences(self, preferences: UserPreferences) -> UserPreferences:
        """
        ### update_preferences
        **Description:** Update and save user preferences.
        **Parameters:**
        - `preferences` (UserPreferences): The new preferences to save.
        **Returns:**
        - `UserPreferences`: The saved preferences object.
        """
        try:
            content = preferences.model_dump_json(indent=4)
            self.preferences_file.write_text(content, encoding='utf-8')
            logger.info("User preferences updated.")
            return preferences
        except OSError as e:
            logger.error(f"Error saving preferences file: {e}")
            raise
