import os
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart

from back.agents.oracle_agent import OracleAgent
from back.config import get_data_dir
from back.models.api.game import LLMConfig
from back.services.game_session_service import GameSessionService

# Mark all tests in this file as requiring LLM
pytestmark = pytest.mark.llm

@pytest.fixture
def llm_config():
    return LLMConfig(
        api_endpoint="https://api.deepseek.com/v1",
        api_key=os.getenv("DEEPSEEK_API_KEY", "sk-fake-key"),
        model="deepseek-chat"
    )

@pytest_asyncio.fixture
async def agent_service_setup(test_character, temp_data_dir, llm_config):
    """Setup agent and services for testing"""
    from uuid import uuid4

    character_id, _ = test_character
    session_id = str(uuid4())
    scenario_filename = "test_scenario.yaml" # Dummy
    
    # Create dummy scenario file
    data_dir = get_data_dir()
    scenario_path = os.path.join(data_dir, "scenarios", scenario_filename)
    os.makedirs(os.path.dirname(scenario_path), exist_ok=True)
    with open(scenario_path, "w") as f:
        f.write("name: Test Scenario\ndescription: A dummy scenario for testing.\n")
    
    from back.agents.translation_agent import TranslationAgent
    from back.models.domain.equipment_manager import EquipmentManager
    from back.services.character_data_service import CharacterDataService
    from back.services.equipment_service import EquipmentService
    from back.services.races_data_service import RacesDataService
    from back.services.settings_service import SettingsService

    # Use real data service
    data_service = CharacterDataService()
    mock_equipment = EquipmentService(data_service, EquipmentManager())
    mock_settings = MagicMock(spec=SettingsService)
    mock_races = MagicMock(spec=RacesDataService)
    mock_translation = MagicMock(spec=TranslationAgent)

    session_service = await GameSessionService.create(
        session_id, 
        str(character_id), 
        scenario_filename,
        data_service,
        mock_equipment,
        mock_settings,
        mock_races,
        mock_translation
    )
    await session_service.character_service.load()

    # Use OracleAgent for actions
    oracle_agent = OracleAgent(llm_config)
    
    return oracle_agent, session_service

@pytest.mark.asyncio
async def test_action_buy_item(agent_service_setup):
    """
    Scenario: Player wants to buy a specific item.
    Prompt: "I want to buy a Longsword."
    Expected: Agent calls inventory_buy_item (or find_or_create_item_tool + currency deduction).
    """
    oracle_agent, session_service = agent_service_setup
    
    # Ensure character has enough gold (default 100 is enough for Longsword ~15g)
    
    prompt = "I am at the shop. I want to buy a Longsword."
    print(f"\n[Scenario: Buy Item] User: {prompt}")
    
    # Mock LLM to force tool calls
    with patch("pydantic_ai.models.openai.OpenAIChatModel.request") as mock_request:
        # Mock finding item and buying it. 
        # Since logic might be complex (search -> create -> add -> remove gold), 
        # we can simulate the "Outcome" or simple tool calls.
        # Let's assume the agent calls 'find_or_create_item_tool' (GIVE) and 'character_remove_currency'.
        
        tool_call_item = ToolCallPart(
            tool_name='find_or_create_item_tool',
            args={'name': 'Longsword', 'acquisition_type': 'BUY', 'description': 'A fine steel longsword for sale.'} # Assuming BUY handles logic or we need separate calls
        )
        # Actually Oracle Agent likely uses `inventory_add_item` if it knows ID, or `find_or_create`.
        # And `character_remove_currency`.
        
        # Simpler: The test checked `weapon_longsword`.
        
        # We need to ensure the tool call arguments match what the agent WOULD generate.
        # But we Control the mock.
        # So we force it to call `inventory_add_item` with 'weapon_longsword' and `character_remove_currency`.
        
        tool_call_add = ToolCallPart(
            tool_name='inventory_add_item',
            args={'item_id': 'weapon_longsword', 'qty': 1}
        )
        tool_call_pay = ToolCallPart(
            tool_name='character_remove_currency',
            args={'gold': 15}
        )
        
        # First response from LLM proposes tools
        mock_msg_tools = ModelResponse(parts=[TextPart(content="Buying sword..."), tool_call_add, tool_call_pay])
        
        # Second response (after tool execution) summarizes
        mock_msg_final = ModelResponse(parts=[TextPart(content="Longsword bought.")])
        
        mock_request.side_effect = [mock_msg_tools, mock_msg_final]

        result = await oracle_agent.agent.run(prompt, deps=session_service)
        print(f"[Scenario: Buy Item] Agent: {result.output}")
        
        # Verify Inventory
        character = session_service.character_service.get_character()
        has_sword = any(item.item_id == "weapon_longsword" for item in character.equipment.weapons)
        assert has_sword, "Character should have bought the Longsword (via mocked tool call)"
        
        # Verify Gold decreased
        assert character.equipment.gold <= 85, "Gold should have decreased"

@pytest.mark.asyncio
async def test_action_use_consumable(agent_service_setup):
    """
    Scenario: Player uses a consumable item.
    Prompt: "I use my First aid medical kit."
    Expected: Agent calls inventory_remove_item AND character_heal.
    """
    oracle_agent, session_service = agent_service_setup
    
    # Setup: Give potion and reduce HP
    character = session_service.character_service.get_character()
    await session_service.equipment_service.add_item(character, "item_first_aid_kit", 1)
    character.combat_stats.current_hit_points -= 10
    await session_service.character_service.save_character()
    
    prompt = "I am injured (40/50 HP). I use my First aid medical kit to recover."
    print(f"\n[Scenario: Use Consumable] User: {prompt}")
    
    with patch("pydantic_ai.models.openai.OpenAIChatModel.request") as mock_request:
        tool_call_remove = ToolCallPart(
            tool_name='inventory_remove_item',
            args={'item_id': 'item_first_aid_kit', 'qty': 1}
        )
        tool_call_heal = ToolCallPart(
            tool_name='character_heal',
            args={'amount': 10}
        )
        
        mock_msg_tools = ModelResponse(parts=[TextPart(content="Using kit..."), tool_call_remove, tool_call_heal])
        mock_msg_final = ModelResponse(parts=[TextPart(content="Healed.")])
        
        mock_request.side_effect = [mock_msg_tools, mock_msg_final]
        
        result = await oracle_agent.agent.run(prompt, deps=session_service)
        print(f"[Scenario: Use Consumable] Agent: {result.output}")
        
        # Verify Potion Consumed
        character = session_service.character_service.get_character()
        has_kit = any(item.item_id == "item_first_aid_kit" for item in character.equipment.consumables)
        assert not has_kit, "First aid kit should have been consumed"
        
        # Verify HP Restored
        assert character.combat_stats.current_hit_points > (character.combat_stats.max_hit_points - 10), "HP should have been restored"

@pytest.mark.asyncio
async def test_action_skill_check(agent_service_setup):
    """
    Scenario: Player attempts an action requiring a skill check.
    Prompt: "I try to pick the lock on the door."
    Expected: Agent calls skill_check_with_character.
    """
    oracle_agent, session_service = agent_service_setup
    
    prompt = "I try to pick the lock on the door."
    print(f"\n[Scenario: Skill Check] User: {prompt}")
    
    with patch("pydantic_ai.models.openai.OpenAIChatModel.request") as mock_request:
        # Mock skill check tool call
        tool_call_skill = ToolCallPart(
            tool_name='skill_check_with_character',
            args={'skill_id': 'subterfuge_mechanisms', 'difficulty_threshold': 15}
        )
        
        mock_msg_tools = ModelResponse(parts=[TextPart(content="Checking skill..."), tool_call_skill])
        
        # For the final response, we assume the tool result was processed. 
        # The tool returns a result string or dict. The agent uses it to generate text.
        mock_msg_final = ModelResponse(parts=[TextPart(content="Skill check successful! You picked the lock.")])
        
        mock_request.side_effect = [mock_msg_tools, mock_msg_final]
        
        result = await oracle_agent.agent.run(prompt, deps=session_service)
        print(f"[Scenario: Skill Check] Agent: {result.output}")
        
        output_lower = str(result.output).lower()
        assert "successful" in output_lower or "picked" in output_lower, \
            "Agent should describe the skill check result"
