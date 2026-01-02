from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from back.config import LLMConfig
from back.models.domain.payloads import (CombatTurnContinuePayload,
                                         CombatTurnEndPayload)
from back.tools.combat_tools import (check_combat_end_tool, end_combat_tool,
                                     end_turn_tool, execute_attack_tool,
                                     get_combat_status_tool,
                                     search_enemy_archetype_tool,
                                     start_combat_tool)
from back.tools.skill_tools import skill_check_with_character


class CombatAgent:
    def __init__(self, config: LLMConfig):
        self.config = config
        
        provider = OpenAIProvider(
            base_url=config.api_endpoint,
            api_key=config.api_key
        )
        model = OpenAIChatModel(
            model_name=config.model,
            provider=provider
        )
        
        self.agent = Agent(
            model=model,
            deps_type=Any,
            output_type=CombatTurnContinuePayload | CombatTurnEndPayload,
            tools=[
                start_combat_tool,
                execute_attack_tool,
                end_turn_tool,
                check_combat_end_tool,
                end_combat_tool,
                get_combat_status_tool,
                search_enemy_archetype_tool,
                skill_check_with_character
            ],
            retries=3
        )
        # Register dynamic system prompt
        self.agent.system_prompt(self._inject_dynamic_system_prompt)

    async def _inject_dynamic_system_prompt(self, ctx: RunContext[Any]) -> str:
        # We can fetch combat state from deps if needed for context,
        # but the tools generally handle the state. 
        # The prompt should focus on TACTICAL COMBAT.
        
        prompt = (
            "You are the Tactical Combat Engine. Your SOLE responsibility is to manage combat encounters strictly and fairly.\n\n"

            "**YOUR MODES:**\n"
            "1. **INITIALIZATION**: If `combat_state` is 'initializing' (or logic implies start), YOU MUST call `start_combat_tool`.\n"
            "   - **Task**: Parse the provided `description` (e.g., 'Two goblins attack') into a VALID `enemies` list.\n"
            "   - **Rule**: You MUST populate the `enemies` list with names and optional archetypes. Use `search_enemy_archetype_tool` if useful.\n\n"

            "2. **ROUND RESOLUTION**: If combat is active.\n"
            "   - **Task**: Resolve the turn for the entity specified in `current_turn`.\n"
            "   - **Player Turn**: Interpret player input (e.g., 'I attack X') -> Call `execute_attack_tool(target_name='Goblin A')`.\n"
            "     - **NOTE**: You do NOT need IDs. Just use the name or a clear partial name.\n"

            "   - **Skill Actions**: If player tries a stunt (e.g. 'Push him', 'Hide', 'Dodge'), use `skill_check_with_character`.\n"
            "   - **NPC Turn**: AI decides action (Attack Player) -> Call `execute_attack_tool(target_name='PlayerName')`.\n"
            "   - **End Turn**: After ONE action, you MUST call `end_turn_tool`.\n\n"

            "**CRITICAL RULES:**\n"
            "- **NO FLUFF**: Output simple, tactical logs. No storytelling.\n"
            "- **CHECK END**: After damage/death, call `check_combat_end_tool`.\n"
            "- **ONE ACTION**: Each turn allows ONE major action (Attack, Spell, Item). Then END TURN.\n"
            "- **SKILL SYNERGY (MANDATORY)**: You MUST check the 'PRE-ACTION SKILL CHECK' line in the prompt.\n"
            "  - If it says **Success**: You MUST call `execute_attack_tool` with `attack_modifier=2`.\n"
            "  - If context implies Advantage (e.g. 'Hidden', 'Prone target'): You MUST set `advantage=True`.\n"
        )
        return prompt

    async def run(self, input_text: str, deps: Any, message_history: list = None):
        return await self.agent.run(input_text, deps=deps, message_history=message_history)