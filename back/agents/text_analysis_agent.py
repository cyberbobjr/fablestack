
from typing import TYPE_CHECKING, List, Union

from langchain_core.messages import BaseMessage, HumanMessage

from back.models.api.game import TextIntentResult
from back.models.domain.stats_manager import StatsManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager

# Use lazy import for GameSessionService in methods to avoid circular dependency if needed, 
# or use TYPE_CHECKING import and string forward reference for deps_type.
if TYPE_CHECKING:
    from back.factories.agent_factory import AgentFactory
    from back.services.game_session_service import GameSessionService

class TextAnalysisAgent:
    """
    Agent responsible for analyzing user text to detect implied skill checks.
    """
    def __init__(self, agent_factory: "AgentFactory"):
        stats_manager = StatsManager()
        skills_manager = UnifiedSkillsManager()
        
        self.stats_list = ", ".join(stats_manager.get_all_stats_names())
        self.skills_list = ", ".join(skills_manager.get_all_skill_ids())
        
        system_prompt = (
            "You are an expert Game Master Judge. Your job is to analyze the player's text action "
            "and determine if it requires a Dice Roll (Skill Check or Stat Check) to succeed.\n\n"
            "### CRITERIA FOR SKILL CHECKS:\n"
            "1. **EXCEPTIONAL or RISKY**: Only call for a check if the action is difficult, dangerous, or has a chance of failure that matters.\n"
            "2. **MUNDANE IS FREE**: Walking, talking, looking around, eating, or normal movement DOES NOT require a check. Return `null` (JSON null) for `skill_check`.\n"
            "3. **IMPLICIT COMBAT**: If the user tries to attack, grapple, or defend, select `Strength`, `Dexterity`, or `Fighting` (if available).\n\n"
            "### AVAILABLE STATS & SKILLS:\n"
            f"STATS: {self.stats_list}\n"
            f"SKILLS: {self.skills_list}\n\n"
            "### INSTRUCTIONS:\n"
            "- Review the Context/History to understand if this is a follow-up action.\n"
            "- If a check is needed, return the EXACT name from the lists above in `skill_check`.\n"
            "- Determine `difficulty`: 'favorable', 'normal', or 'unfavorable' based on context.\n"
            "- If no check is needed, set `skill_check` to `null` (not the string 'null').\n"
            "- Always provide `reasoning`."
        )

        self.agent = agent_factory.create_agent(
            structured_output=TextIntentResult,
            system_prompt=system_prompt
        )

    async def analyze(
        self, 
        text_content: str, 
        deps: "GameSessionService", 
        history_messages: Union[List[BaseMessage], List[dict]] = []
    ) -> TextIntentResult:
        """
        Analyzes the text content to see if a skill check is implied.
        """
        prompt = f"PLAYER ACTION: \"{text_content}\"\n\nAnalyze this action. Does it require a skill check based on the criteria?"
        
        messages = []
        if history_messages:
            messages.extend(history_messages)
        messages.append(HumanMessage(content=prompt))
        
        result = await self.agent.invoke(messages)
        
        if not isinstance(result, TextIntentResult):
            raise ValueError(f"Agent did not return TextIntentResult, got {type(result).__name__} instead")
        
        return result
