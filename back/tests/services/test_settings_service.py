import pytest
import os
import json
from pathlib import Path
from back.services.settings_service import SettingsService
from back.models.domain.preferences import UserPreferences

class TestSettingsService:
    """
    Test suite for SettingsService.
    """

    def test_get_preferences_default(self):
        """
        Test retrieving preferences when file does not exist (should return default).
        """
        service = SettingsService()
        # Ensure file does not exist
        if service.preferences_file.exists():
            service.preferences_file.unlink()
            
        prefs = service.get_preferences()
        assert isinstance(prefs, UserPreferences)
        assert prefs.language == "English"  # Default value

    def test_update_preferences(self):
        """
        Test updating and saving preferences.
        """
        service = SettingsService()
        new_prefs = UserPreferences(language="French")
        
        saved_prefs = service.update_preferences(new_prefs)
        assert saved_prefs.language == "French"
        
        # Verify file content
        assert service.preferences_file.exists()
        content = json.loads(service.preferences_file.read_text())
        assert content["language"] == "French"

    def test_get_preferences_existing(self):
        """
        Test retrieving preferences from an existing file.
        """
        service = SettingsService()
        # Create file manually
        data = {"language": "Spanish"}
        service.preferences_file.write_text(json.dumps(data))
        
        prefs = service.get_preferences()
        assert prefs.language == "Spanish"
