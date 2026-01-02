"""
Router for managing translations.
"""

import json
import os
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["translation"])

# Path to translations directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATIONS_DIR = os.path.join(BASE_DIR, 'gamedata', 'translations')

class TranslationResponse(BaseModel):
    """Response model for translations"""
    translations: Dict[str, Any]

@router.get(
    "/{language}", 
    response_model=TranslationResponse,
    summary="Get Translations",
    description="Get all translations for a specific language.",
    responses={
        200: {
            "description": "Translations",
            "content": {"application/json": {"example": {"translations": {"stats": {"strength": "Force"}}}}}
        },
        404: {"description": "Language not found"}
    }
)
def get_translations(language: str) -> TranslationResponse:
    """
    Get all translations for a specific language.
    
    Args:
        language: The language code (e.g., 'fr', 'en')
        
    Returns:
        A dictionary containing all translation keys and values.
    """
    file_path = os.path.join(TRANSLATIONS_DIR, f"{language}.json")
    
    if not os.path.exists(file_path):
        # If language file doesn't exist, try to return empty or default?
        # For now, let's return 404
        raise HTTPException(status_code=404, detail=f"Translations for language '{language}' not found")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return TranslationResponse(translations=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading translation file: {str(e)}")

@router.put(
    "/{language}", 
    response_model=TranslationResponse,
    summary="Update Translation",
    description="Update a specific translation key.",
    responses={
        200: {"description": "Translation updated"},
        404: {"description": "Language not found"}
    }
)
def update_translation(language: str, key: str = Body(...), value: str = Body(...), category: str = Body(...)) -> TranslationResponse:
    """
    Update a specific translation key.
    
    Args:
        language: The language code
        key: The translation key (e.g., 'Strength')
        value: The new translation value (e.g., 'Force')
        category: The category (e.g., 'stats', 'skills')
        
    Returns:
        The updated translations.
    """
    file_path = os.path.join(TRANSLATIONS_DIR, f"{language}.json")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Translations for language '{language}' not found")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if category not in data:
            data[category] = {}
            
        data[category][key] = value
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        return TranslationResponse(translations=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating translation file: {str(e)}")
