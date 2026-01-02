from typing import TYPE_CHECKING, List

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from back.models.api.game import ChoiceData, LLMConfig
from back.models.domain.stats_manager import StatsManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

class ChoiceList(BaseModel):
    """Container for a list of choices."""
    choices: List[ChoiceData]

class ChoiceAgent:
    """
    Agent responsible for generating immersive choices based on the current narrative.
    """
    def __init__(self, llm_config: LLMConfig):
        provider = OpenAIProvider(
            base_url=llm_config.api_endpoint,
            api_key=llm_config.api_key
        )
        model = OpenAIChatModel(
            model_name=llm_config.model,
            provider=provider
        )
        # Use lazy import for GameSessionService to avoid circular dependency
        from back.services import GameSessionService

        stats_manager = StatsManager()
        skills_manager = UnifiedSkillsManager()
        
        self.stats_list = ", ".join(stats_manager.get_all_stats_names())
        self.skills_list = ", ".join(skills_manager.get_all_skill_ids())

        self.agent = Agent(
            model=model,
            deps_type=GameSessionService,
            output_type=ChoiceList,
        )
        
        @self.agent.system_prompt
        async def _inject_dynamic_system_prompt(ctx: RunContext["GameSessionService"]) -> str:
            """
            ### _inject_dynamic_system_prompt
            **Purpose:** Generates the dynamic system prompt for the Oracle Agent.
            It defines the strict role of the agent as a game engine and referee.
            """
            return (
                "You are an expert Game Master assistant responsible for proposing actions to the player.\n"
                "Based on the provided narrative context, suggest 3 to 5 distinct, actionable choices.\n"
                "Choices should be:\n"
                "1. Relevant to the immediate situation.\n"
                "2. Action-oriented (e.g., 'Inspect the altar', 'Attack the goblin', 'Talk to the merchant').\n"
                "3. Diverse (include risks, investigation, or combat options if applicable).\n"
                "4. Concise (short description).\n"
                "Respect these rules:\n"
                "- NPC names should only be revealed if the player has explicitly asked for them.\n"
                "- Preserve the wonder of exploration - describe places as the CHARACTER experiences them for the first time.\n"
                "\n"
                f"AVAILABLE STATS: {self.stats_list}\n"
                f"AVAILABLE SKILLS: {self.skills_list}\n"
                "\n"
                "For each choice, determine if a skill check or stat check is required.\n"
                "- **DEFAULT TO NULL**: Most actions do NOT need a check. Only assign one if failure has interesting consequences.\n"
                "- **NO TRIVIAL CHECKS**: 'Looking around', 'Talking to someone', 'Walking', or 'Inspecting visible items' MUST be null.\n"
                "- **EXCEPTIONAL TASKS ONLY**: Only assign a skill (e.g., 'Stealth', 'Athletics', 'Persuasion') if the action is inherently difficult OR risky (e.g., 'Climbing a sheer wall', 'Lying to a guard', 'Deciphering ancient runes').\n"
                "- 'skill_check' should be the exact name of the skill or stat.\n"
                "- 'difficulty': Determine if the check is 'favorable' (situational advantage, help, easy task), 'normal' (standard), or 'unfavorable' (situational disadvantage, very hard task, time pressure).\n"
                "\n"
                "Return a structured list of choices.\n\n"
#                "SCENARIO: \n"
#                f"{scenario}\n"
            )

    async def generate_choices(self, narrative_context: str, deps: "GameSessionService", user_language: str = "English") -> List[ChoiceData]:
        """
        Generates a list of choices based on the narrative.
        """
        prompt = f"NARRATIVE CONTEXT:\n{narrative_context}\n\nPropose 4 distinct choices for the player in {user_language}."
        
        result = await self.agent.run(prompt, deps=deps)
        return result.output.choices
