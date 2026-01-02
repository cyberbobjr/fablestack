"""
Centralized localization service for backend error messages and notifications.
"""

from typing import Dict


class LocalizationService:
    """
    ### LocalizationService
    **Description:** Provides centralized localization for backend messages.
    
    This service manages translations for error messages and other backend text
    that needs to be displayed to users in their preferred language.
    """
    
    # Supported languages
    SUPPORTED_LANGUAGES: list[str] = ["en", "fr"]
    DEFAULT_LANGUAGE: str = "en"
    
    # Translation keys
    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "portrait_rate_limit": {
            "en": "Daily portrait regeneration limit of {limit} reached. Please come back tomorrow!",
            "fr": "La limite quotidienne de {limit} régénérations est atteinte. Revenez demain !"
        }
    }
    
    @staticmethod
    def detect_language(language_preference: str) -> str:
        """
        Detect and normalize language from user preference.
        
        **Parameters:**
        - `language_preference` (str): The user's language preference string.
        
        **Returns:** Normalized language code ('en' or 'fr').
        """
        if not language_preference:
            return LocalizationService.DEFAULT_LANGUAGE
        
        lang_lower: str = language_preference.lower()
        
        # Check for French
        if "fr" in lang_lower or "french" in lang_lower or "français" in lang_lower:
            return "fr"
        
        # Default to English
        return "en"
    
    @staticmethod
    def get_message(key: str, language: str, **kwargs) -> str:
        """
        Get a localized message by key and language.
        
        **Parameters:**
        - `key` (str): The translation key.
        - `language` (str): The language code ('en' or 'fr') or preference string like "English" or "French".
        - `**kwargs`: Format parameters for the message.
        
        **Returns:** The localized message with format parameters applied.
        """
        # Normalize language
        lang: str = LocalizationService.detect_language(language)
        
        # Get translation
        if key not in LocalizationService.TRANSLATIONS:
            available_keys: list[str] = list(LocalizationService.TRANSLATIONS.keys())
            error_msg: str = f"Translation key '{key}' not found. Available keys: {', '.join(available_keys)}"
            return error_msg
        
        translations: Dict[str, str] = LocalizationService.TRANSLATIONS[key]
        if lang not in translations:
            lang = LocalizationService.DEFAULT_LANGUAGE
        
        message: str = translations[lang]
        
        # Apply format parameters if any
        if kwargs:
            message = message.format(**kwargs)
        
        return message
