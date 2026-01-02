from typing import TYPE_CHECKING, Union

from back.models.domain.payloads import CombatIntentPayload, ScenarioEndPayload

if TYPE_CHECKING:
    from back.services.game_session_service import GameSessionService

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from back.models.api.game import LLMConfig
from back.utils.history_processors import summarize_old_messages


class OracleAgent:
    """
    ### OracleAgent
    **Description:** PydanticAI agent dedicated to game logic and rules adjudication.
    Handles player input analysis, scenario triggers, and game mechanics execution.
    """

    def __init__(self, llm_config: LLMConfig):
        """
        ### __init__
        **Description:** Initialize the oracle agent with LLM configuration.
        **Parameters:**
        - `llm_config` (LLMConfig): LLM configuration containing api_endpoint, api_key, model.
        """
        provider = OpenAIProvider(
            base_url=llm_config.api_endpoint,
            api_key=llm_config.api_key
        )
        model = OpenAIChatModel(
            model_name=llm_config.model,
            provider=provider
        )

        # Register Tools (Runtime Import to avoid circular dependencies)
        from back.tools.character_tools import (character_add_currency,
                                                character_apply_xp,
                                                character_heal,
                                                character_remove_currency,
                                                character_take_damage)
        from back.tools.combat_tools import declare_combat_start_tool
        from back.tools.equipment_tools import (check_inventory_quantity,
                                                find_or_create_item_tool,
                                                inventory_add_item,
                                                inventory_decrease_quantity,
                                                inventory_increase_quantity,
                                                inventory_remove_item,
                                                inventory_sell_item,
                                                list_available_equipment)
        from back.tools.scenario_tools import end_scenario_tool
        from back.tools.skill_tools import skill_check_with_character

        self.agent = Agent(
            model=model,
            deps_type="GameSessionService",
            output_type=Union[str, CombatIntentPayload, ScenarioEndPayload],
            tools=[
                declare_combat_start_tool,
                find_or_create_item_tool,
                inventory_add_item,
                inventory_remove_item,
                inventory_sell_item,
                inventory_decrease_quantity,
                inventory_increase_quantity,
                check_inventory_quantity,
                list_available_equipment,
                character_add_currency,
                character_remove_currency,
                character_heal,
                character_take_damage,
                character_apply_xp,
                skill_check_with_character,
                end_scenario_tool,
            ],
            history_processors=[summarize_old_messages],
            retries=3
        )

        @self.agent.system_prompt
        async def _inject_dynamic_system_prompt(ctx: RunContext["GameSessionService"]) -> str:
            """
            ### _inject_dynamic_system_prompt
            **Purpose:** Generates the dynamic system prompt for the Oracle Agent.
            It defines the strict role of the agent as a game engine and referee.
            """
            scenario = await ctx.deps.load_current_scenario_content()
            return (
                "You are the Game Engine and Referee. Your job is to strictly adjudicate game mechanics. "
                "You effectively act as an Intelligent Oracle.\n\n"

                "**INPUT:** You will receive User Input, Conversation History, and the **Current Scenario Content**.\n"
                "**TASK:**\n"
                "1. **Analyze Intent:** Resolve pronouns (e.g., 'attack him' -> 'attack Goblin Warrior').\n"
                "2. **Check Scenario Triggers:** Does this action trigger a scripted event in the Scenario file? (e.g., 'If player talks to X, give item Y').\n"
                "3. **Check Game Rules:** Is this a Combat Action? A Skill Check? A Transaction?\n"
                "4. **EXECUTE:** Call the appropriate Tool to resolve the action.\n"
                "5. **OUTPUT:** Return a concise, factual summary of the outcome (e.g., 'Attack Hit (15 dmg). Enemy Dead. Item Looted').\n\n"

                "**CRITICAL COMBAT RULE - LISTEN CAREFULLY:**\n"
                "If the player's action initiates a fight (e.g. 'I attack', 'Ambushes enemies'), you **MUST** call `declare_combat_start_tool`.\n"
                "You CANNOT resolve attacks yourself. You are the Narrator, not the Combat Engine.\n"
                "1. Call `declare_combat_start_tool(description='...')`.\n"
                "2. The system will handle the rest.\n\n"

                "**TOOL USAGE RULES:**\n"
                "- **declare_combat_start_tool**: MANDATORY when a fight breaks out. Provide a description of WHO is attacking/being attacked.\n"
                "- **end_scenario_tool**: ONLY use this tool when the scenario's MAIN OBJECTIVE is COMPLETED or IRREVERSIBLY FAILED.\n"
                "  NEVER use it for starting scenarios, describing locations, or normal progression.\n"
                "  ONLY use when: player achieves final quest goal OR fails in a way that makes completion impossible.\n"
                "- **character_apply_xp**: Use for XP rewards when specific scenario milestones are reached.\n"
                "- **character_add_currency**: Use for gold rewards from quests or loot.\n"
                "- **Other tools**: Use appropriate tools for combat, skill checks, inventory management, etc.\n\n"

                "**CORRECT EXAMPLES - STUDY THESE:**\n"
                "User: 'I draw my sword and attack the two goblins!'\n"
                "Reasoning: Combat triggered. I identified 2 enemies: 'Goblin'. I must call declare_combat_start_tool.\n"
                "Tool Call: `declare_combat_start_tool(description='Two goblins attack!')`\n\n"

                "User: 'A mysterious shadow strikes from the dark!'\n"
                "Reasoning: Ambush! 1 Enemy: 'Shadow'. Stats unknown, using placeholder.\n"
                "Tool Call: `declare_combat_start_tool(description='Ambush by a shadow.')`\n\n"

                "**CONSTRAINT:** Before calling a tool, you MUST explain your reasoning in a short sentence starting with 'REASONING:'.\n"
                "**CONSTRAINT:** If calling `declare_combat_start_tool`, your REASONING must explicitly list the enemies you identified.\n"
                "**CONSTRAINT:** DO NOT write flavor text. DO NOT narrate. Only output logic facts.\n"
                "**CONSTRAINT:** If the user input is just asking a question (lore), answer it based on Scenario/History context but keep it brief.\n"
                "**CONSTRAINT:** For scenario initialization or description, NEVER call end_scenario_tool. Just describe the situation.\n"
                "=== CURRENT SCENARIO (IMMUTABLE CONTEXT) ===\n"
                f"SCENARIO: {scenario}\n"
            )


