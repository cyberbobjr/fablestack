
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from back.agents.illustration_extraction_agent import \
    IllustrationExtractionAgent


async def test_extraction():
    agent = IllustrationExtractionAgent()
    
    scenario_text = """
    # The Lost Temple
    
    ## Context
    A dark and gloomy temple hidden in the jungle.
    
    ## Locations
    The Main Hall is vast and filled with cobwebs.
    
    ## NPCs (Visual Reference)
    List each major NPC here with a detailed visual description to facilitate illustration generation.
    - **Name**: High Priestess Elara
    - **Visual**: A tall elven woman with silver hair, wearing flowing blue robes embroidered with stars. She holds a glowing crystal staff. Her eyes are violet and glowing.
    
    - **Name**: Gorgon the Destroyer
    - **Visual**: A massive orc warlord clad in blackened iron plate armor. He wields a jagged greataxe. His face is scarred and he has one white eye.
    """
    
    print("Running extraction...")
    result = await agent.analyze_scenario(scenario_text)
    print(f"Result: {result}")
    
    for item in result:
        print(f"Subject: {item.subject}, Type: {item.type}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
