"""
FastAPI router for character creation.
Exposes the necessary routes for the new simplified character system using Character models.
"""

import random
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi_injector import Injected

from back.agents.generic_agent import build_simple_gm_agent
from back.auth_dependencies import get_current_active_user
from back.models.api.equipment import EquipmentResponse
from back.models.api.game import RaceData
from back.models.api.skills import SkillsResponse, StatsResponse
from back.models.domain.character import Character, Skills, Stats
from back.models.domain.equipment_manager import EquipmentManager
from back.models.domain.items import EquipmentItem
from back.models.domain.rules_manager import RulesManager
from back.models.domain.stats_manager import StatsManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager
from back.models.domain.user import User
from back.models.enums import CharacterSex, CharacterStatus
from back.services.character_data_service import CharacterDataService
from back.services.image_generation_service import ImageGenerationService
from back.services.races_data_service import RacesDataService
from back.services.settings_service import SettingsService
from back.services.skill_allocation_service import SkillAllocationService
from back.utils.logger import log_warning

router = APIRouter(tags=["creation"])

# Pydantic models for requests/responses
from pydantic import BaseModel, Field


class CreateCharacterRequest(BaseModel):
    """Request model for creating a new character"""
    name: str = Field(..., description="Character name")
    sex: str = Field(..., description="Character sex (male/female)")
    race_id: str = Field(..., description="Race ID")
    culture_id: str = Field(..., description="Culture ID")
    stats: Dict[str, int] = Field(default={}, description="Character stats")
    skills: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Character skills by group")
    background: str = Field(default="", description="Character background")
    background_localized: str | None = Field(default=None, description="Localized character background")
    physical_description: str | None = Field(default=None, description="Physical appearance description")
    physical_description_localized: str | None = Field(default=None, description="Localized physical appearance description")

class CreateCharacterResponse(BaseModel):
    """Response model for character creation"""
    character_id: str = Field(..., description="Unique character identifier")
    status: str = Field(..., description="Creation status")
    created_at: str = Field(..., description="Creation timestamp")

class UpdateCharacterRequest(BaseModel):
    """Request model for updating a character"""
    character_id: str = Field(..., description="Character ID")
    name: str = Field(default="", description="Character name")
    stats: Dict[str, int] = Field(default_factory=dict, description="Character stats")
    skills: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Character skills by group")
    background: str = Field(default="", description="Character background")
    background_localized: str | None = Field(default=None, description="Localized character background")
    physical_description: str | None = Field(default=None, description="Physical appearance description")
    physical_description_localized: str | None = Field(default=None, description="Localized physical appearance description")

class UpdateCharacterResponse(BaseModel):
    """Response model for character update"""
    character: Dict[str, Any] = Field(..., description="Updated character data")
    status: str = Field(..., description="Update status")

class CharacterResponse(BaseModel):
    """Response model for character data"""
    character: Character = Field(..., description="Character data")
    status: str = Field(..., description="Operation status")

class ValidateCharacterRequest(BaseModel):
    """Request model for character validation"""
    id: str = Field(..., description="Character ID")
    user_id: str | None = Field(default=None, description="User ID")
    name: str = Field(..., description="Character name")
    sex: str = Field(..., description="Character sex")
    race: str = Field(..., description="Race ID")
    culture: str = Field(..., description="Culture ID")
    stats: Dict[str, int] = Field(..., description="Character stats")
    skills: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Character skills by group")
    combat_stats: Dict[str, Any] = Field(..., description="Combat statistics")
    equipment: Dict[str, Any] = Field(..., description="Equipment data")
    spells: Dict[str, Any] = Field(..., description="Spell data")
    level: int = Field(..., description="Character level")
    status: str = Field(..., description="Character status")
    experience_points: int = Field(..., description="Experience points")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    description: str | None = Field(default=None, description="Character description")
    description_localized: str | None = Field(default=None, description="Localized character description")
    physical_description: str | None = Field(default=None, description="Physical description")
    physical_description_localized: str | None = Field(default=None, description="Localized physical description")

class ValidateCharacterResponse(BaseModel):
    """Response model for character validation"""
    valid: bool = Field(..., description="Whether the character is valid")
    character: Dict[str, Any] = Field(default_factory=dict, description="Validated character data (if valid)")
    errors: List[str] = Field(default_factory=list, description="Validation errors (if invalid)")
    message: str = Field(..., description="Validation message")

class GenerateDetailsRequest(BaseModel):
    """Request model for generating character details"""
    race_id: str = Field(..., description="Race ID")
    sex: str = Field(..., description="Character sex")
    culture_id: str = Field(..., description="Culture ID")

class GenerateDetailsResponse(BaseModel):
    """Response model for generated details"""
    name: str = Field(..., description="Generated name")
    background: str = Field(..., description="Generated background")
    physical_description: str = Field(..., description="Generated physical description")
    background_localized: str | None = Field(default=None, description="Generated localized background")
    physical_description_localized: str | None = Field(default=None, description="Generated localized physical description")


class TranslationResult(BaseModel):
    """Internal model for structured translation output"""
    background_english: str | None = Field(default=None, description="Translated background in English")
    physical_description_english: str | None = Field(default=None, description="Translated physical description in English")


async def _validate_character_payload(
    character_payload: Dict[str, Any], 
    character_id: str | None = None,
    data_service: CharacterDataService | None = None
) -> ValidateCharacterResponse:
    """Run Character validation and build a standardized response.
    
    If character_id is provided, persists any status changes after validation.
    """
    try:
        validated_character = Character(**character_payload)
        validated_character.sync_status_from_completion()
        
        # Persist status change if character_id is provided
        if character_id and data_service:
            await data_service.save_character(validated_character, character_id)
        
        return ValidateCharacterResponse(
            valid=True,
            character=validated_character.model_dump(),
            message="Character is valid",
        )
    except ValueError as validation_error:
        return ValidateCharacterResponse(
            valid=False,
            errors=[str(validation_error)],
            message=f"Validation failed: {str(validation_error)}",
        )


class ValidateCharacterByIdRequest(BaseModel):
    """Request model for validating a character stored on disk."""
    character_id: str = Field(..., description="Identifier of the character to validate")

@router.post(
    "/random",
    response_model=CharacterResponse,
    summary="Create Random Character",
    description="Creates a new random character using the simplified system, including LLM-generated name, background and description.",
    responses={
        200: {
            "description": "Random character created",
            "content": {"application/json": {"example": {
                "character": {
                    "id": "123", "name": "Random Elf", "race": "elves", "stats": {"strength": 10}, "status": "draft"
                },
                "status": "created"
            }}}
        }
    }
)
async def create_random_character(
    races_service: RacesDataService = Injected(RacesDataService),
    rules_manager: RulesManager = Injected(RulesManager),
    stats_manager: StatsManager = Injected(StatsManager),
    skill_allocation_service: SkillAllocationService = Injected(SkillAllocationService),
    skills_manager: UnifiedSkillsManager = Injected(UnifiedSkillsManager),
    settings_service: SettingsService = Injected(SettingsService),
    image_service: ImageGenerationService = Injected(ImageGenerationService),
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> CharacterResponse:
    """
    Creates a new random character using the system with LLM-generated content.
    """
    try:
        # 1. Get random race and culture
        try:
            random_race_data, random_culture_data = races_service.get_random_race_and_culture()
        except ValueError as error:
            raise HTTPException(status_code=500, detail=str(error))

        # 1b. Random Sex
        random_sex = random.choice(list(CharacterSex))
        
        # 1c. Get Sex Bonuses
        sex_bonuses = rules_manager.get_sex_bonuses(random_sex)

        # 2. Generate random balanced stats (Point Buy System)
        creation_rules = rules_manager.get_stats_creation_rules()
        budget = creation_rules.get('budget', 27)
        costs_table = creation_rules.get('costs', {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9})
        start_value = creation_rules.get('start_value', 8)

        stats_list = [stat.lower() for stat in stats_manager.get_all_stats_names()]
        
        # Initialize all to start value
        generated_stats = {stat: start_value for stat in stats_list}
        
        # Helper to get cost of a value
        def get_cost(val: int) -> int:
            return costs_table.get(val, 0)
        
        # Helper to get incremental cost (from current to current+1)
        def get_incremental_cost(current_val: int) -> int:
            max_val = max(costs_table.keys())
            if current_val >= max_val: return 999 
            return get_cost(current_val + 1) - get_cost(current_val)

        # Distribute points randomly
        max_iterations = 100 # safety break
        while budget > 0 and max_iterations > 0:
            stat = random.choice(stats_list)
            current_val = generated_stats[stat]
            
            if current_val < max(costs_table.keys()):
                cost = get_incremental_cost(current_val)
                if budget >= cost:
                    generated_stats[stat] += 1
                    budget -= cost
            
            max_iterations -= 1
        
        # Apply Sex Stat Bonuses
        if 'stats' in sex_bonuses:
            for stat, bonus in sex_bonuses['stats'].items():
                if stat in generated_stats:
                    generated_stats[stat] += bonus

        random_stats = generated_stats

        # 3. Allocate skills based on race affinities and stats
        stats_obj = Stats(**random_stats)
        
        # Calculate total free skill points (Culture only)
        total_free_points = random_culture_data.free_skill_points or 0

        allocated_skills = skill_allocation_service.allocate_random_skills_for_character(
            random_race_data.name, 
            random_culture_data.name, 
            stats_obj,
            free_skill_points=total_free_points
        )

        # Apply Sex Skill Bonuses
        if 'skills' in sex_bonuses:
             for skill_id, bonus in sex_bonuses['skills'].items():
                 # Check if user already has this skill allocated
                 skill_found = False
                 for group, skills in allocated_skills.items():
                     if skill_id in skills:
                         skills[skill_id] += bonus
                         skill_found = True
                         break
                 
                 if not skill_found:
                     # If skill not present, we need to know its group to add it
                     skill_data = skills_manager.get_skill_data(skill_id)
                     if skill_data:
                         group = skill_data.get('category', 'general') 
                         if group not in allocated_skills:
                             allocated_skills[group] = {}
                         allocated_skills[group][skill_id] = bonus

        # 4. Generate name, background and description with LLM in a single call
        agent = build_simple_gm_agent(output_type=GenerateDetailsResponse)

        # check user language
        preferences = settings_service.get_preferences()
        user_language = preferences.language
        
        is_localized = user_language and user_language.lower() != "english"

        prompt = (
            f"Generate character details for a {random_sex.value} {random_race_data.name} from {random_culture_data.name}.\n"
            "1. A single fantasy name.\n"
            "2. A short background story (creative and concise).\n"
            "3. A physical description using image generation prompt syntax (comma separated keywords, visual descriptors, lighting, style). "
            "Focus on visual details like hair, eyes, skin, armor, accessories. Do not write sentences."
        )

        if is_localized:
            prompt += (
                f"\n\nIMPORTANT: The user speaks {user_language}. "
                f"You MUST provide `background_localized` (translated to {user_language}) and `physical_description_localized` (translated to {user_language}). "
                f"For `physical_description_localized`, keep the same format (comma separated keywords) but translated. "
                "Keep default `background` and `physical_description` in English."
            )

        details_res = await agent.run(prompt)
        details = details_res.output
        character_name = details.name
        background = details.background
        physical_description = details.physical_description
        background_localized = details.background_localized
        physical_description_localized = details.physical_description_localized

        # 4. Calculate combat stats
        strength_modifier = (random_stats['strength'] - 10) // 2
        agility_modifier = (random_stats['agility'] - 10) // 2
        
        max_hp = random_stats['constitution'] * 10 + 5 # level 1
        max_mp = random_stats['intelligence'] * 5 + random_stats['wisdom'] * 3
        ac = 10 + agility_modifier
        attack_bonus = strength_modifier

        # 5. Create and save character
        character_id = str(uuid4())
        now = datetime.now().isoformat()

        character_dict = {
            "id": character_id,
            "name": character_name,
            "race": random_race_data.id,
            "sex": random_sex,
            "culture": random_culture_data.id,
            "stats": Stats(**random_stats).model_dump(),
            "skills": allocated_skills,
            "combat_stats": {
                "max_hit_points": max_hp, "current_hit_points": max_hp, 
                "max_mana_points": max_mp, "current_mana_points": max_mp, 
                "armor_class": ac, "attack_bonus": attack_bonus
            },
            "equipment": {"weapons": [], "armor": [], "accessories": [], "consumables": [], "gold": 0},
            "spells": {"known_spells": [], "spell_slots": {}, "spell_bonus": 0},
            "level": 1, "status": "draft", "experience_points": 0,
            "created_at": now, "updated_at": now,
            "description": background,
            "description_localized": background_localized,
            "physical_description": physical_description,
            "physical_description_localized": physical_description_localized
        }


        
        # 5b. Generate portrait (async)
        try:
            portrait_url = await image_service.generate_character_portrait(character_dict)
            if portrait_url:
                character_dict["portrait_url"] = portrait_url
        except Exception as e:
            # Don't fail creation if image fails
             pass

        character = Character(**character_dict)
        character.sync_status_from_completion()
        
        await data_service.save_character(character, character_id)
        
        return CharacterResponse(
            character=character,
            status="created"
        )

    except Exception as e:
        # Log the full error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Random character creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Random character creation failed: {str(e)}")

@router.post(
    "/generate-details",
    response_model=GenerateDetailsResponse,
    summary="Generate Character Details",
    description="Generates name, background and physical description based on race and culture using AI.",
    responses={
        200: {"description": "Details generated"},
        404: {"description": "Race or Culture not found"}
    }
)
async def generate_details(
    request: GenerateDetailsRequest,
    races_service: RacesDataService = Injected(RacesDataService),
    settings_service: SettingsService = Injected(SettingsService)
) -> GenerateDetailsResponse:
    """
    Generates character details (name, background, description) using AI.
    """
    try:
        # 1. Get race and culture names
        race_data = races_service.get_race_by_id(request.race_id)
        if not race_data:
            raise HTTPException(status_code=404, detail=f"Race with id '{request.race_id}' not found")
        
        culture_data = next((c for c in race_data.cultures if c.id == request.culture_id), None)
        if not culture_data:
            raise HTTPException(status_code=404, detail=f"Culture with id '{request.culture_id}' not found")

        # 2. Generate with LLM in a single call
        agent = build_simple_gm_agent(output_type=GenerateDetailsResponse)
        sex_str = request.sex 

        # check user language
        preferences = settings_service.get_preferences()
        user_language = preferences.language
        
        is_localized = user_language and user_language.lower() != "english"

        prompt = (
            f"Generate character details for a {sex_str} {race_data.name} from {culture_data.name}.\n"
            "1. A single fantasy name.\n"
            "2. A short background story (creative and concise).\n"
            "3. A physical description using image generation prompt syntax (comma separated keywords, visual descriptors, lighting, style). "
            "Focus on visual details like hair, eyes, skin, armor, accessories. Do not write sentences."
        )

        if is_localized:
            prompt += (
                f"\n\nIMPORTANT: The user speaks {user_language}. "
                f"You MUST provide `background_localized` (translated to {user_language}) and `physical_description_localized` (translated to {user_language}). "
                f"For `physical_description_localized`, keep the same format (comma separated keywords) but translated. "
                "Keep default `background` and `physical_description` in English."
            )

        result = await agent.run(prompt)
        return result.output

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Details generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Details generation failed: {str(e)}")



@router.get(
    "/races", 
    summary="List Races", 
    description="Returns the complete list of available races for the system.",
    response_model=List[RaceData],
    responses={
        200: {"description": "List of races"}
    }
)
def get_races(
    races_service: RacesDataService = Injected(RacesDataService)
) -> List[RaceData]:
    """
    Returns the complete list of available races for the system.
    """
    races_data = races_service.get_playable_races()

    # FastAPI will automatically serialize RaceData Pydantic objects to JSON
    return races_data

@router.get(
    "/skills", 
    summary="List Skills", 
    description="Returns the complete skills structure including racial affinities.",
    response_model=SkillsResponse,
    responses={
        200: {"description": "Skills data"}
    }
)
def get_skills(
    skills_manager: UnifiedSkillsManager = Injected(UnifiedSkillsManager),
    rules_manager: RulesManager = Injected(RulesManager)
) -> SkillsResponse:
    """
    Returns the complete skills structure for the system including racial affinities.
    """
    data = skills_manager.get_all_data()
    data['skill_creation_rules'] = rules_manager.get_skill_creation_rules()
    return SkillsResponse(**data)

@router.get(
    "/equipment", 
    summary="List Equipment", 
    description="Returns the complete available equipment catalog.",
    response_model=EquipmentResponse,
    responses={
        200: {"description": "Equipment data"}
    }
)
def get_equipment(
    equipment_manager: EquipmentManager = Injected(EquipmentManager)
) -> EquipmentResponse:
    """
    Returns the complete available equipment catalog.
    """
    equipment_data = equipment_manager.get_all_equipment()

    # Convert dictionaries to EquipmentItem objects, handling type conversions
    def convert_item(item: dict) -> EquipmentItem:
        # Map catalog ID to item_id if missing
        if 'item_id' not in item and 'id' in item:
            item['item_id'] = item['id']
        
        # Handle cost conversion (assuming cost in YAML is in gold)
        if 'cost' in item:
            cost = item.pop('cost')
            # Simple conversion: assume cost is gold
            item['cost_gold'] = int(cost)
            item['cost_silver'] = int((cost - int(cost)) * 10)
            item['cost_copper'] = 0 # Ignore smaller fractions for now
            
        # Ensure required fields for EquipmentItem
        if 'quantity' not in item:
            item['quantity'] = 1
        if 'equipped' not in item:
            item['equipped'] = False
        if 'category' not in item and 'type' in item:
            item['category'] = item['type']
            
        # Convert range to integer if it's a string (EquipmentItem expects Optional[int])
        # But wait, previous code converted int to string? 
        # Model says: range: Optional[int] = None
        # So we should ensure it is int or None.
        if 'range' in item:
            if item['range'] is None or item['range'] == '':
                item['range'] = None
            else:
                try:
                    item['range'] = int(item['range'])
                except (ValueError, TypeError):
                    item['range'] = None

        return EquipmentItem(**item)

    weapons = [convert_item(item.copy()) for item in equipment_data.get("weapons", [])]
    armor = [convert_item(item.copy()) for item in equipment_data.get("armor", [])]
    accessories = [convert_item(item.copy()) for item in equipment_data.get("accessories", [])]
    consumables = [convert_item(item.copy()) for item in equipment_data.get("consumables", [])]
    
    # Process general items and distribute them based on type
    general = []
    for item in equipment_data.get("items", []):
        converted = convert_item(item.copy())
        if converted.type == 'consumable':
            consumables.append(converted)
        elif converted.type == 'accessory':
            accessories.append(converted)
        else:
            general.append(converted)

    return EquipmentResponse(
        weapons=weapons,
        armor=armor,
        accessories=accessories,
        consumables=consumables,
        general=general
    )

@router.get(
    "/rules/stats_creation", 
    summary="Get Stats Rules",
    description="Returns the rules for stats creation (point buy costs, budget).",
    response_model=Dict[str, Any]
)
def get_stats_creation_rules(
    rules_manager: RulesManager = Injected(RulesManager)
) -> Dict[str, Any]:
    """
    Returns the rules for stats creation (point buy costs, budget).
    """
    return rules_manager.get_stats_creation_rules()

@router.get(
    "/stats", 
    summary="List Stats", 
    description="Returns the complete stats definitions and rules.",
    response_model=StatsResponse,
    responses={
        200: {"description": "Stats data"}
    }
)
def get_stats(
    stats_manager: StatsManager = Injected(StatsManager)
) -> StatsResponse:
    """
    Returns the complete stats structure for the system.
    """
    stats_data = stats_manager.get_all_stats_data()

    # StatsManager returns data that matches StatsResponse structure
    return StatsResponse(**stats_data)

@router.get(
    "/rules/sex_bonuses", 
    summary="Get Sex Bonuses", 
    description="Returns the bonuses associated with character sex variables.",
    response_model=Dict[str, Any]
)
def get_sex_bonuses(
    rules_manager: RulesManager = Injected(RulesManager)
) -> Dict[str, Any]:
    """
    Returns the bonuses associated with character sex variables.
    """
    return rules_manager.get_all_sex_bonuses()


@router.post(
    "/create",
    response_model=CreateCharacterResponse,
    summary="Create Character",
    description="Creates a new character using the simplified system with validation.",
    responses={
        200: {"description": "Character created", "content": {"application/json": {"example": {"character_id": "123", "status": "created", "created_at": "2023-01-01"}}}},
        404: {"description": "Race/Culture not found"}
    }
)
async def create_character(
    request: CreateCharacterRequest,
    current_user: User = Depends(get_current_active_user),
    races_service: RacesDataService = Injected(RacesDataService),
    rules_manager: RulesManager = Injected(RulesManager),
    skills_manager: UnifiedSkillsManager = Injected(UnifiedSkillsManager),
    image_service: ImageGenerationService = Injected(ImageGenerationService),
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> CreateCharacterResponse:
    """
    Creates a new character using the system with validation.

    **Request Body:**
    ```json
    {
        "name": "Aragorn",
        "race_id": "humans",
        "culture_id": "gondorians",
        "stats": {
            "strength": 15,
            "constitution": 14,
            "agility": 13,
            "intelligence": 12,
            "wisdom": 16,
            "charisma": 15
        },
        "skills": {
            "combat": {
                "melee_weapons": 3,
                "weapon_handling": 2
            },
            "general": {
                "perception": 4
            }
        },
        "background": "Son of Arathorn, heir to the throne of Gondor",
        "physical_description": "Tall ranger with dark hair and piercing eyes"
    }
    ```

    **Response:**
    ```json
    {
        "character_id": "d7763165-4c03-4c8d-9bc6-6a2568b79eb3",
        "status": "created",
        "created_at": "2025-11-13T21:30:00Z"
    }
    ```
    """
    # Define custom exception for race validation
    class RaceNotFoundError(ValueError):
        pass

    try:
        # Generate unique character ID
        character_id = str(uuid4())
        now = datetime.now().isoformat()
        
        # Validate race and culture
        # races_service injected
        race_data = races_service.get_race_by_id(request.race_id)
        if not race_data:
            raise RaceNotFoundError(f"Race with id '{request.race_id}' not found")
        
        # Create character using model
        # Create character dictionary directly for model
        
        # Calculate combat stats
        stats_data = request.stats if request.stats else {'strength': 10, 'constitution': 10, 'agility': 10, 'intelligence': 10, 'wisdom': 10, 'charisma': 10}
        
        # Validate base stats using Point Buy System
        # rules_manager injected
        creation_rules = rules_manager.get_stats_creation_rules()
        budget = creation_rules.get('budget', 27)
        costs = creation_rules.get('costs', {})
        start_value = creation_rules.get('start_value', 8)

        total_cost = 0
        for stat, value in stats_data.items():
            if value < start_value:
                 raise ValueError(f"Stat {stat} value ({value}) is below the minimum of {start_value}.")
            
            # Calculate cost for this value
            # The cost table maps value -> cumulative cost from start_value
            if value not in costs:
                 # Check if value is above max defined in costs? Or imply extrapolation? 
                 # For now, strict validation against defined costs.
                 # Actually, usually point buy has a max (e.g. 15).
                 max_val = max(costs.keys()) if costs else 15
                 if value > max_val:
                     raise ValueError(f"Stat {stat} value ({value}) exceeds the maximum purchasable value of {max_val}.")
                 else:
                     raise ValueError(f"Stat {stat} value ({value}) has no defined cost.")
            
            total_cost += costs[value]

        if total_cost > budget:
             raise ValueError(f"Total stat point cost ({total_cost}) exceeds the budget of {budget}.")

        # Validate skill points total
        # Calculate total points spent in request.skills
        if request.skills:
            total_skills = 0
            for group, skills in request.skills.items():
                total_skills += sum(skills.values())
            
            # Find culture data to get free skill points
            # race_data is already loaded above
            culture_data = next((c for c in race_data.cultures if c.id == request.culture_id), None)
            free_points = 0
            if culture_data and culture_data.free_skill_points:
                 free_points = culture_data.free_skill_points
            
            max_skill_points = 40 + free_points
            
            if total_skills > max_skill_points:
                raise ValueError(f"Total skill points ({total_skills}) exceed the maximum of {max_skill_points} points.")

        # Apply Racial/Cultural Bonuses
        # races_service injected
        bonuses = races_service.get_complete_character_bonuses(request.race_id, request.culture_id)
        
        if 'characteristic_bonuses' in bonuses:
             for stat, bonus in bonuses['characteristic_bonuses'].items():
                 if stat in stats_data:
                     stats_data[stat] += bonus

        # Apply Sex Bonuses
        try:
            sex_enum = CharacterSex(request.sex)
            # rules_manager injected
            sex_bonuses = rules_manager.get_sex_bonuses(sex_enum)
            if 'stats' in sex_bonuses:
                for stat, bonus in sex_bonuses['stats'].items():
                    if stat in stats_data:
                        stats_data[stat] += bonus
        except ValueError:
             raise ValueError(f"Invalid sex: {request.sex}")

        # Apply Sex Skill Bonuses (Backend Authority)
        # We add these to the user-provided skills
        if 'skills' in sex_bonuses:
            for skill_id, bonus in sex_bonuses['skills'].items():
                # We need to find the group again.
                # Assuming standard structure or checking request.skills
                
                # First check if user allocated points to this skill
                skill_found = False
                if request.skills:
                    for group, skills in request.skills.items():
                         if skill_id in skills:
                             # Add bonus to user allocation
                             skills[skill_id] += bonus
                             skill_found = True
                             break
                
                if not skill_found:
                    # If user didn't allocate, we need to add it to the correct group
                    # We use UnifiedSkillsManager to find the group
                    # skills_manager injected
                    skill_data = skills_manager.get_skill_data(skill_id)
                    if skill_data:
                        group = skill_data.get('category', 'general') # default to general
                        if not request.skills:
                            request.skills = {}
                        if group not in request.skills:
                            request.skills[group] = {}
                        request.skills[group][skill_id] = bonus


        # Automatic Translation of Localized Fields
        # If localized fields are present, we auto-translate them to English
        if request.background_localized or request.physical_description_localized:
            try:
                # We use the agent to translate both fields at once for efficiency
                agent = build_simple_gm_agent(output_type=TranslationResult)
                
                parts = []
                parts.append("Translate the following character details into English. Maintain style and tone.")
                
                if request.background_localized:
                    parts.append(f"Localized Background: {request.background_localized}")
                    parts.append("Goal: Provide 'background_english'.")

                if request.physical_description_localized:
                    parts.append(f"Localized Physical Description: {request.physical_description_localized}")
                    parts.append("Goal: Provide 'physical_description_english'.")
                
                prompt = "\n\n".join(parts)
                
                trans_result = await agent.run(prompt)
                translated_data = trans_result.output # payload is in .output for typed agents
                
                if request.background_localized and translated_data.background_english:
                    request.background = translated_data.background_english
                    
                if request.physical_description_localized and translated_data.physical_description_english:
                    request.physical_description = translated_data.physical_description_english

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Auto-translation failed during creation: {e}")
                # We proceed with whatever data we have, defaulting to existing or empty English fields

        strength_modifier = (stats_data['strength'] - 10) // 2
        agility_modifier = (stats_data['agility'] - 10) // 2
        
        max_hp = stats_data['constitution'] * 10 + 5 # level 1
        max_mp = stats_data['intelligence'] * 5 + stats_data['wisdom'] * 3
        ac = 10 + agility_modifier
        attack_bonus = strength_modifier

        character_dict = {
            "id": character_id,
            "user_id": current_user.id,
            "name": request.name,
            "race": request.race_id,
            "sex": sex_enum,
            "culture": request.culture_id,
            "stats": Stats(**stats_data).model_dump(),
            "skills": Skills(**request.skills).model_dump() if request.skills else Skills().model_dump(),
            "combat_stats": {
                "max_hit_points": max_hp,
                "current_hit_points": max_hp,
                "max_mana_points": max_mp,
                "current_mana_points": max_mp,
                "armor_class": ac,
                "attack_bonus": attack_bonus
            },
            "equipment": {
                "weapons": [],
                "armor": [],
                "accessories": [],
                "consumables": [],
                "gold": 0
            },
            "spells": {
                "known_spells": [],
                "spell_slots": {},
                "spell_bonus": 0
            },
            "level": 1,
            "status": "draft",
            "experience_points": 0,
            "created_at": now,
            "updated_at": now,
            "description": request.background or None,
            "description_localized": request.background_localized,
            "physical_description": request.physical_description,
            "physical_description_localized": request.physical_description_localized
        }


        
        # Generate portrait (async)
        try:
            # image_service injected
            portrait_url = await image_service.generate_character_portrait(character_dict)
            if portrait_url:
                character_dict["portrait_url"] = portrait_url
        except Exception as e:
            # Don't fail creation if image fails, but log the error
            log_warning(
                "Failed to generate character portrait",
                character_id=character_id,
                character_name=request.name,
                error=str(e)
            )

        # Validate using Character model and align status with completion state
        character = Character(**character_dict)
        character.sync_status_from_completion()

        # Save character data
        # data_service injected
        await data_service.save_character(character, character_id)
        
        return CreateCharacterResponse(
            character_id=character_id,
            status="created",
            created_at=now
        )
        
    except RaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Character creation failed: {str(e)}")

@router.post(
    "/update",
    response_model=UpdateCharacterResponse,
    summary="Update character",
    description="Updates an existing character"
)
async def update_character(
    request: UpdateCharacterRequest,
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> UpdateCharacterResponse:
    """
    Updates an existing character with validation.

    **Request Body:**
    ```json
    {
        "character_id": "d7763165-4c03-4c8d-9bc6-6a2568b79eb3",
        "name": "Aragorn II",
        "stats": {
            "strength": 16,
            "constitution": 15,
            "agility": 14,
            "intelligence": 13,
            "wisdom": 17,
            "charisma": 16
        },
        "skills": {
            "combat": {
                "melee_weapons": 5,
                "weapon_handling": 4
            }
        },
        "background": "Heir to the throne of Gondor, skilled ranger",
        "physical_description": "Tall with dark hair and noble bearing"
    }
    ```

    **Response:**
    ```json
    {
        "character": {
            "id": "d7763165-4c03-4c8d-9bc6-6a2568b79eb3",
            "name": "Aragorn II",
            "race": "humans",
            "culture": "gondorians",
            "stats": {
                "strength": 16,
                "constitution": 15,
                "agility": 14,
                "intelligence": 13,
                "wisdom": 17,
                "charisma": 16
            },
            "skills": {
                "combat": {
                    "melee_weapons": 5,
                    "weapon_handling": 4
                }
            },
            "combat_stats": {
                "max_hit_points": 150,
                "current_hit_points": 150,
                "max_mana_points": 130,
                "current_mana_points": 130,
                "armor_class": 12,
                "attack_bonus": 3
            },
            "equipment": {
                "weapons": [],
                "armor": [],
                "accessories": [],
                "consumables": [],
                "gold": 0
            },
            "spells": {
                "known_spells": [],
                "spell_slots": {},
                "spell_bonus": 0
            },
            "level": 1,
            "status": "draft",
            "experience_points": 0,
            "created_at": "2025-11-13T21:30:00Z",
            "updated_at": "2025-11-13T21:35:00Z",
            "description": "Heir to the throne of Gondor, skilled ranger",
            "physical_description": "Tall with dark hair and noble bearing"
        },
        "status": "updated"
    }
    ```
    """
    # Define custom exception for character not found
    class CharacterNotFoundError(ValueError):
        pass
    
    try:
        # Load existing character
        # data_service injected

        # Use simple global container access for now to avoid complexity in this file refactor
        existing_character = await data_service.load_character(request.character_id)
        if existing_character is None:
            raise CharacterNotFoundError(f"Character with id '{request.character_id}' not found")

        # Check if character is in a game session
        if existing_character.status == CharacterStatus.IN_GAME:
            raise ValueError("Character is currently in an adventure and cannot be edited.")

        # Update fields
        if request.name:
            existing_character.name = request.name
        if request.stats:
            existing_character.stats = Stats(**request.stats)
        if request.skills:
            existing_character.skills = Skills(**request.skills)
        if request.background:
            existing_character.description = request.background
        if request.background_localized:
            existing_character.description_localized = request.background_localized
        if request.physical_description is not None:
            existing_character.physical_description = request.physical_description
        if request.physical_description_localized is not None:
            existing_character.physical_description_localized = request.physical_description_localized

        existing_character.sync_status_from_completion()
        existing_character.update_timestamp()

        # 3. Save updated character
        await data_service.save_character(existing_character, request.character_id)
        
        return UpdateCharacterResponse(
            character=existing_character.model_dump(),
            status="updated"
        )
        
    except CharacterNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Character update failed: {str(e)}")



@router.post(
    "/validate-character",
    response_model=ValidateCharacterResponse,
    summary="Validate character",
    description="Validates a character against game rules"
)
async def validate_character(character: ValidateCharacterRequest) -> ValidateCharacterResponse:
    """
    Validates a character against game rules.

    **Request Body:**
    ```json
    {
        "id": "d7763165-4c03-4c8d-9bc6-6a2568b79eb3",
        "name": "Aragorn",
        "race": "humans",
        "culture": "gondorians",
        "stats": {
            "strength": 15,
            "constitution": 14,
            "agility": 13,
            "intelligence": 12,
            "wisdom": 16,
            "charisma": 15
        },
        "skills": {
            "combat": {
                "melee_weapons": 3
            }
        },
        "combat_stats": {
            "max_hit_points": 140,
            "current_hit_points": 140,
            "max_mana_points": 112,
            "current_mana_points": 112,
            "armor_class": 11,
            "attack_bonus": 2
        },
        "equipment": {
            "weapons": [],
            "armor": [],
            "accessories": [],
            "consumables": [],
            "gold": 0
        },
        "spells": {
            "known_spells": [],
            "spell_slots": {},
            "spell_bonus": 0
        },
        "level": 1,
        "status": "draft",
        "experience_points": 0,
        "created_at": "2025-11-13T21:30:00Z",
        "updated_at": "2025-11-13T21:30:00Z",
        "description": "Son of Arathorn",
        "physical_description": "Tall ranger"
    }
    ```

    **Response (Success):**
    ```json
    {
        "valid": true,
        "character": {
            "id": "d7763165-4c03-4c8d-9bc6-6a2568b79eb3",
            "name": "Aragorn",
            "race": "humans",
            "culture": "gondorians",
            "stats": {
                "strength": 15,
                "constitution": 14,
                "agility": 13,
                "intelligence": 12,
                "wisdom": 16,
                "charisma": 15
            },
            "skills": {
                "combat": {
                    "melee_weapons": 3
                }
            },
            "combat_stats": {
                "max_hit_points": 140,
                "current_hit_points": 140,
                "max_mana_points": 112,
                "current_mana_points": 112,
                "armor_class": 11,
                "attack_bonus": 2
            },
            "equipment": {
                "weapons": [],
                "armor": [],
                "accessories": [],
                "consumables": [],
                "gold": 0
            },
            "spells": {
                "known_spells": [],
                "spell_slots": {},
                "spell_bonus": 0
            },
            "level": 1,
            "status": "draft",
            "experience_points": 0,
            "created_at": "2025-11-13T21:30:00Z",
            "updated_at": "2025-11-13T21:30:00Z",
            "description": "Son of Arathorn",
            "physical_description": "Tall ranger"
        },
        "message": "Character is valid"
    }
    ```

    **Response (Failure):**
    ```json
    {
        "valid": false,
        "errors": ["Field 'name' is required"],
        "message": "Validation failed: Field 'name' is required"
    }
    ```
    """
    try:
        return await _validate_character_payload(character.model_dump())
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(exc)}") from exc


@router.post(
    "/validate-character/by-id",
    response_model=ValidateCharacterResponse,
    summary="Validate character by identifier",
    description="Loads a stored character by ID and validates it using the same rules as /validate-character",
)
async def validate_character_by_id(
    request: ValidateCharacterByIdRequest,
    data_service: CharacterDataService = Injected(CharacterDataService)
) -> ValidateCharacterResponse:
    """Validate a persisted character without resending its entire payload."""
    try:
        character = await data_service.load_character(request.character_id)
    except FileNotFoundError as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error)) from not_found_error
    except ValueError as value_error:
        raise HTTPException(status_code=400, detail=str(value_error)) from value_error

    return await _validate_character_payload(character.model_dump(), character_id=request.character_id, data_service=data_service)