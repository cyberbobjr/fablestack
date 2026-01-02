import random
from typing import TYPE_CHECKING, Any, Optional

from pydantic_ai import RunContext

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

from back.models.api.skills import SkillCheckResult
from back.models.domain.character import Character
from back.utils.logger import log_debug


def skill_check_with_character(
    ctx: RunContext[Any], 
    skill_name: str, 
    difficulty_name: str = "normal", 
    difficulty_modifier: int = 0,
    fallback_stat_name: Optional[str] = None
) -> SkillCheckResult:
    """
    Performs a skill check using the session character's data.

    This tool resolves skill checks by looking up the skill in the character's stats or skill groups.
    It should be used when the character attempts an action with a chance of failure (e.g., climbing, persuading).
    It calculates the target number based on stats/skills and difficulty, then rolls 1d100.

    Args:
        skill_name (str): Name of the skill or stat to test (e.g., "perception", "strength", "acrobatics").
        difficulty_name (str): Difficulty level ("favorable", "normal", "unfavorable"). Default is "normal".
        difficulty_modifier (int): Additional difficulty penalty (positive increases difficulty, negative decreases it). Default is 0.
        fallback_stat_name (Optional[str]): Stat to use if skill is not found (e.g., "strength", "agility"). Default is None (uses Wisdom).

    Returns:
        dict: A dictionary containing the detailed result of the test including roll, target, success status, and degree.
    """
    args_log = {
        "tool": "skill_check_with_character",
        "player_id": str(ctx.deps.character_id),
        "skill_name": skill_name
    }

    try:
        # Get character service from deps
        character_service = ctx.deps.character_service
        
        if not character_service:
             return {"error": "Character service not available"}

        # Delegate to service (SRP)
        result = character_service.perform_skill_check(
            skill_name=skill_name,
            difficulty_name=difficulty_name,
            difficulty_modifier=difficulty_modifier,
            fallback_stat_name=fallback_stat_name
        )
        
        log_debug(
            "Tool skill_check_with_character success", 
            **args_log,
            roll=result.roll, 
            target=result.target, 
            success=result.success, 
            degree=result.degree
        )
        
        return result

    except Exception as e:
        log_debug("Error in skill_check_with_character", error=str(e), **args_log)
        raise e
