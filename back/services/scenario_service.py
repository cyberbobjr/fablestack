import os
from datetime import datetime
from typing import Any, Dict, List

from back.agents.generic_agent import build_simple_gm_agent
from back.config import config, get_data_dir, get_llm_config
from back.models.api.game import ScenarioList, ScenarioStatus
from back.utils.logger import log_debug


class ScenarioService:
    @staticmethod
    def _sanitize_filename(title: str) -> str:
        """Sanitizes a title to be a valid filename."""
        # Kept for compatibility or if needed, but primary generation now uses IDs
        return "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_').lower() + ".md"

    @staticmethod
    async def _parse_metadata(file_path: str) -> dict:
        """
        Parses the YAML frontmatter from a scenario file.
        """
        import aiofiles
        metadata = {}
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                line = await f.readline()
                if line.strip() == '---':
                    while True:
                        line = await f.readline()
                        if not line or line.strip() == '---':
                            break
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip().strip('"').strip("'")
        except Exception as e:
            import traceback
            log_debug(f"Error parsing metadata for {file_path}: {e}\n{traceback.format_exc()}")
            # Continue with empty metadata or partial
        return metadata

    """
    ### list_scenarios
    **Description:** Lists available scenarios.
    **Parameters:** None.
    **Returns:** List of `ScenarioStatus`.
    """
    @staticmethod
    async def list_scenarios() -> ScenarioList:
        # Define paths to scenarios
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")

        # Get active sessions to mark played scenarios
        # Local import to avoid circular dependency
        from back.services.game_session_service import GameSessionService
        try:
            sessions = await GameSessionService.list_all_sessions()
            # scenario_id in sessions is usually the ID from frontmatter, or filename if ID missing
            played_scenario_ids = set()
            for s in sessions:
                sid = s.get("scenario_id")
                if sid:
                    played_scenario_ids.add(sid)
        except Exception as e:
            import traceback
            log_debug(f"Error fetching active sessions for scenario list: {e}\n{traceback.format_exc()}")
            played_scenario_ids = set()

        # Available scenarios (*.md in data/scenarios)
        available = []
        if os.path.isdir(scenarios_dir):
            for fname in os.listdir(scenarios_dir):
                if fname.endswith(".md"):
                    # Parse frontmatter to get ID and Title
                    metadata = await ScenarioService._parse_metadata(os.path.join(scenarios_dir, fname))
                    scenario_id = metadata.get('id')
                    scenario_title = metadata.get('title')
                    
                    status = metadata.get('status', 'available')
                    
                    # Check if this scenario is currently being played
                    # We check both ID and Filename against the session record
                    is_played = (scenario_id in played_scenario_ids) or (fname in played_scenario_ids)

                    available.append(ScenarioStatus(
                        name=fname, 
                        status=status,
                        id=scenario_id,
                        title=scenario_title,
                        is_played=is_played
                    ))
        log_debug("Scenario list requested", action="list_scenarios", available=len(available))
        return ScenarioList(scenarios=available)

    @staticmethod
    async def initiate_creation(description: str) -> ScenarioStatus:
        """
        ### initiate_creation
        **Description:** Creates a placeholder file for the scenario with a timestamp-based ID and returns the 'creating' status.
        This is an asynchronous method that initializes the scenario file with "Generating..." as a placeholder title.
        **Parameters:**
        - `description` (str): The user-provided description of the scenario to be generated.
        **Returns:** `ScenarioStatus` object containing the scenario ID, filename, title ("Generating..."), and status ("creating").
        """
        import aiofiles
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_id = f"scen_{timestamp}"
        filename = f"{scenario_id}.md"
        
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")
        os.makedirs(scenarios_dir, exist_ok=True)
        file_path = os.path.join(scenarios_dir, filename)

        if os.path.exists(file_path):
            raise FileExistsError(f"Scenario file '{filename}' already exists.")
            
        # Write placeholder content
        # Title is initially "Generating..." until AI updates it
        start_title = "Generating..."
        content = (
            "---\n"
            f"id: {scenario_id}\n"
            f"title: {start_title}\n"
            "status: creating\n"
            "---\n\n"
            f"# {start_title}\n\n"
            "Status: **Creating...**\n\n"
            "The scenario is currently being generated by the AI agent. Please wait.\n"
        )
        
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)
            
        return ScenarioStatus(
            id=scenario_id,
            title=start_title,
            name=filename,
            status="creating",
            is_played=False
        )

    @staticmethod
    async def process_creation(description: str, filename: str) -> None:
        """
        Background task: Generates the full scenario content and updates the file.
        Uses a hardcoded strict prompt to ensure compliance with valid scenario format.
        """
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")
        file_path = os.path.join(scenarios_dir, filename)
        scenario_id = filename.replace('.md', '')
        
        # We assume file exists as it was initiated, but good to check
        if not os.path.exists(file_path):
            log_debug(f"Process creation failed: File {filename} not found.")
            return

        # Fetch Game Data
        from back.models.domain.races_manager import RacesManager
        races_manager = RacesManager()
        races = races_manager.get_all_races()
        races_list_str = "\n".join([f"    * {r.name} (ID: `{r.id}`)" for r in races])
        available_race_ids = ", ".join([f"'{r.id}'" for r in races])

        # Fetch Equipment Data
        from back.models.domain.equipment_manager import EquipmentManager
        equipment_manager: EquipmentManager = EquipmentManager()
        all_equipment: Dict[str, List[Dict[str, Any]]] = equipment_manager.get_all_equipment()
        
        equipment_lines: List[str] = []
        for category, items in all_equipment.items():
            equipment_lines.append(f"  **{category.title()}:**")
            for item in items:
                equipment_lines.append(f"    * {item['name']} (ID: `{item['id']}`)")
        equipment_list_str: str = "\n".join(equipment_lines)

        from back.config import config
        world_lore = config.world.lore

        # Hardcoded Strict Prompt based on SCENARIO.md rules with Dynamic Data
        SCENARIO_GENERATION_PROMPT = """
You are an expert Game Master and Designer for a text-based RPG.
Your task is to write a complete scenario file in Markdown format, ready to be integrated into the game engine.

**World Context (Lore):**
{world_lore}

**Strict Constraints:**
1.  **Format**: Use exactly the structure defined below (YAML Frontmatter, specific H2 headers).
2.  **Language**: The narrative content must be in French. Technical keys (IDs) remain in English/Code.
3.  **Technical IDs**:
    *   For each NPC/Creature, you MUST specify a valid `Race ID` from the following list:
{races_list_str}
    *   For each standard item, you MUST use the exact ID from the **Standard Items Reference** below. DO NOT invent generic IDs like `item_misc`.
    *   For checks, use the format: `Name (ID) (Difficulty)`.
4.  **Items**: Each item MUST have a **Attribution Condition** field explaining exactly when the player gets it.
    *   **Standard Items Reference**:
{equipment_list_str}
5.  **Creativity**: Create an immersive atmosphere, sensory descriptions, and NPCs with real personality suitable for the Lore.
6.  **Title**: GENERATE A CREATIVE TITLE for the scenario based on the description.

**Expected Output Structure:**

---
id: "{scenario_id}"
title: "[INSERT GENERATED TITLE HERE]"
status: available
---

# Scenario: [INSERT GENERATED TITLE HERE]

## Context
[Context description...]

## 1. Locations
[Locations description...]

## 2. NPCs & Creatures
For each entity:
* **Name**
* **Race ID**: [CRITICAL: Must be one of: {available_race_ids}]
* **Appearance**: Physical description.
* **Personality**: Character traits.
* **Interaction**: Reaction to player.

## 3. Items & Rewards
* **Item Name** (ID: `item_id`)
  * **Description**
  * **Effect/Bonus**
  * **Attribution Condition**

## 4. Random Encounters
A Markdown table with columns: d20, Encounter, Race ID.

## 5. Progression & XP
List of actions yielding experience.
"""

        system_prompt = SCENARIO_GENERATION_PROMPT.format(
            scenario_id=scenario_id, 
            world_lore=world_lore, 
            races_list_str=races_list_str,
            available_race_ids=available_race_ids,
            equipment_list_str=equipment_list_str
        )
        system_prompt += f"\n\n### User Instructions\nCreate a scenario based on this theme: {description}\n"
        
        # Call Generic Agent
        log_debug(f"Calling GenericAgent for scenario generation (background): {filename}")
        llm_config = get_llm_config()
        from back.agents.generic_agent import GenericAgent
        agent = GenericAgent(llm_config, system_prompt=system_prompt)
        
        try:
            result = await agent.run(description)
            content = result.output
            
            # Clean Content
            content = content.strip()
            if content.startswith("```"):
                lines = content.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
                
            # Save to File (Overwrite placeholder)
            import aiofiles
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
                
            log_debug(f"Scenario generation completed and saved to {file_path}")
            
        except Exception as e:
            import traceback
            log_debug(f"Error during scenario generation: {e}\n{traceback.format_exc()}")
            
            error_content = (
                "---\n"
                f"id: {scenario_id}\n"
                f"title: Generation Failed\n"
                "status: failed\n"
                "---\n\n"
                f"# Generation Failed\n\n"
                "**Generation Failed**\n\n"
                f"Error: {str(e)}\n"
            )
            import aiofiles
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(error_content)





    @staticmethod
    async def update_scenario(filename: str, content: str) -> ScenarioStatus:
        """
        Update the content of an existing scenario file.
        """
        import aiofiles
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")
        file_path = os.path.join(scenarios_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Scenario file '{filename}' not found.")
            
        # Security check: prevent directory traversal
        if not os.path.abspath(file_path).startswith(os.path.abspath(scenarios_dir)):
             raise ValueError("Invalid filename")

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)
            
        # Re-parse metadata to return updated status
        metadata = await ScenarioService._parse_metadata(file_path)
        
        return ScenarioStatus(
            id=metadata.get('id'),
            title=metadata.get('title'),
            name=filename,
            status="available",
            is_played=False # Logic to check if played is complex here, maybe separate or just default false for edit return
        )

    @staticmethod
    async def delete_scenario(filename: str) -> None:
        """
        Deletes a scenario file.
        """
        import aiofiles.os
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")
        file_path = os.path.join(scenarios_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Scenario '{filename}' not found.")
            
        # Optional: Check if played? 
        # For now, we allow deletion but maybe the router should check status first.
        # But this is a raw service method.
        
        await aiofiles.os.remove(file_path)
        log_debug("Scenario deleted", filename=filename)


    @staticmethod
    async def get_scenario_details(scenario_file: str) -> str:
        """
        Retrieves the content of a scenario (Markdown file) from its filename.

        Parameters:
        - scenario_file (str): The scenario file name (e.g., Les_Pierres_du_Passe.md).

        Returns:
        - str: The Markdown file content of the scenario.

        Raises:
        - FileNotFoundError: If the file does not exist.
        """
        import aiofiles
        scenario_path = os.path.join(get_data_dir(), "scenarios", scenario_file)
        if not os.path.isfile(scenario_path):
            raise FileNotFoundError(f"The scenario '{scenario_file}' does not exist.")
        async with aiofiles.open(scenario_path, "r", encoding="utf-8") as f:
            return await f.read()

    @staticmethod
    async def get_scenario_title(scenario_filename: str) -> str:
        """
        Retrieves the title of a scenario from its metadata.
        Returns the filename if no title is found or if the file doesn't exist.
        
        Parameters:
        - scenario_filename (str): The filename of the scenario.
        
        Returns:
        - str: The title of the scenario or the filename if not found.
        """
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")
        scenario_path = os.path.join(scenarios_dir, scenario_filename)
        
        if not os.path.exists(scenario_path):
            return scenario_filename
            
        metadata = await ScenarioService._parse_metadata(scenario_path)
        return metadata.get('title', scenario_filename)
            
    @staticmethod
    async def get_scenario_id(scenario_filename: str) -> str:
        """
        Retrieves the ID of a scenario from its metadata.
        Returns the filename if no ID is found or if the file doesn't exist.
        
        Parameters:
        - scenario_filename (str): The filename of the scenario.
        
        Returns:
        - str: The ID of the scenario or the filename if not found.
        """
        scenarios_dir = os.path.join(get_data_dir(), "scenarios")
        scenario_path = os.path.join(scenarios_dir, scenario_filename)
        
        if not os.path.exists(scenario_path):
            return scenario_filename
            
        metadata = await ScenarioService._parse_metadata(scenario_path)
        return metadata.get('id', scenario_filename)




