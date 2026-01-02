"""
Helper functions for integration tests.
"""

from pathlib import Path
import json
from back.models.domain.character import Character


def assert_character_state(character: Character, expected_hp: int, expected_gold: int, expected_xp: int):
    """Assert character state matches expectations"""
    assert character.combat_stats.current_hit_points == expected_hp, \
        f"Expected HP {expected_hp}, got {character.combat_stats.current_hit_points}"
    assert character.equipment.gold == expected_gold, \
        f"Expected gold {expected_gold}, got {character.equipment.gold}"
    assert character.experience_points == expected_xp, \
        f"Expected XP {expected_xp}, got {character.experience_points}"


def load_character_from_file(temp_data_dir: Path, character_id: str) -> dict:
    """Load character from temporary test data directory"""
    char_path = temp_data_dir / "characters" / f"{character_id}.json"
    return json.loads(char_path.read_text())


def create_directive_message(instruction: str) -> str:
    """Create a very directive user message for predictable LLM behavior"""
    return f"<TEST_INSTRUCTION>{instruction}</TEST_INSTRUCTION>"


def verify_file_exists(temp_data_dir: Path, relative_path: str) -> bool:
    """Verify that a file exists in the temp data directory"""
    file_path = temp_data_dir / relative_path
    return file_path.exists()
