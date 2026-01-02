from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from back.models.domain.character import Character, CombatStats, Skills, Stats
from back.services.game_session_service import GameSessionService
from back.tools.skill_tools import skill_check_with_character


@pytest.fixture
def mock_session_service():
    """Create a mock GameSessionService"""
    service = MagicMock(spec=GameSessionService)
    service.character_id = str(uuid4())
    service.character_service = MagicMock()
    service.data_service = MagicMock()
    service.races_service = MagicMock()
    return service


@pytest.fixture
def mock_run_context(mock_session_service):
    """Create a mock RunContext with the session service"""
    mock_model = MagicMock()
    usage = RunUsage(requests=1)
    return RunContext(
        deps=mock_session_service, 
        retry=0, 
        tool_name="test_tool", 
        model=mock_model, 
        usage=usage
    )


@pytest.fixture
def sample_character():
    """Create a sample Character object for testing"""
    stats = Stats(
        strength=12,
        constitution=14,
        agility=10,
        intelligence=13,
        wisdom=11,
        charisma=15
    )
    
    skills = Skills(
        artistic={"comedy": 3, "storytelling": 2},
        magic_arts={"alchemy": 2},
        athletic={"acrobatics": 4, "climbing": 2},
        combat={"weapon_handling": 5},

        general={"perception": 6, "crafting": 2}
    )
    
    combat_stats = CombatStats(
        max_hit_points=100,
        current_hit_points=100,
        armor_class=12
    )
    
    return Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        name="Test Hero",
        race="human",
        culture="gondor",
        stats=stats,
        skills=skills,
        combat_stats=combat_stats
    )


@patch('back.tools.skill_tools.random.randint')
def test_skill_check_base_stat(mock_randint, mock_run_context, sample_character):
    """Test skill check against a base stat (charisma)"""
    mock_randint.return_value = 40
    
    # Mock CharacterService result
    from back.models.api.skills import SkillCheckResult
    mock_result = SkillCheckResult(
        skill_name="charisma",
        roll=40,
        target=75,
        success=True,
        degree="Simple Success",
        source_used="Base stat Charisma",
        message="Skill check for charisma..."
    )
    
    mock_run_context.deps.character_service.perform_skill_check.return_value = mock_result
    
    result = skill_check_with_character(mock_run_context, "charisma", "normal")
    
    assert result.skill_name == "charisma"
    assert "Base stat Charisma" in result.source_used
    assert result.roll == 40
    assert result.success is True
    assert "Success" in result.degree


@patch('back.tools.skill_tools.random.randint')
def test_skill_check_trained_skill(mock_randint, mock_run_context, sample_character):
    """Test skill check using a trained skill (perception)"""
    mock_randint.return_value = 50
    
    from back.models.api.skills import SkillCheckResult
    mock_result = SkillCheckResult(
        skill_name="perception",
        roll=50,
        target=115,
        success=True,
        degree="Simple Success",
        source_used="Skill perception (rank 6)",
        message="Skill check for perception..."
    )
    
    mock_run_context.deps.character_service.perform_skill_check.return_value = mock_result
    
    result = skill_check_with_character(mock_run_context, "perception", "normal")
    
    assert result.skill_name == "perception"
    assert "Skill perception (rank 6)" in result.source_used
    assert result.success is True


@patch('back.tools.skill_tools.random.randint')
def test_skill_check_untrained_skill(mock_randint, mock_run_context, sample_character):
    """Test skill check using an untrained skill"""
    mock_randint.return_value = 40
    
    from back.models.api.skills import SkillCheckResult
    mock_result = SkillCheckResult(
        skill_name="unknown_skill",
        roll=40,
        target=55,
        success=True,
        degree="Simple Success",
        source_used="Untrained skill",
        message="Skill check for unknown_skill"
    )
    
    mock_run_context.deps.character_service.perform_skill_check.return_value = mock_result
    
    result = skill_check_with_character(mock_run_context, "unknown_skill", "normal")
    
    assert result.skill_name == "unknown_skill"
    assert result.target == 55
    assert "Skill check for unknown_skill" in result.message


@patch('back.tools.skill_tools.random.randint')
def test_skill_check_with_difficulty(mock_randint, mock_run_context, sample_character):
    """Test skill check with difficulty modifier"""
    mock_randint.return_value = 60
    
    from back.models.api.skills import SkillCheckResult
    mock_result = SkillCheckResult(
        skill_name="strength",
        roll=60,
        target=40,
        success=False,
        degree="Simple Failure",
        source_used="Base stat Strength",
        message="Failure..."
    )
    
    mock_run_context.deps.character_service.perform_skill_check.return_value = mock_result
    
    result = skill_check_with_character(mock_run_context, "strength", "unfavorable")
    
    assert result.skill_name == "strength"
    assert result.target == 40
    assert result.success is False
    assert "Failure" in result.degree


@patch('back.tools.skill_tools.random.randint')
def test_skill_check_critical_success(mock_randint, mock_run_context, sample_character):
    """Test skill check resulting in critical success"""
    mock_randint.return_value = 1
    
    from back.models.api.skills import SkillCheckResult
    mock_result = SkillCheckResult(
        skill_name="charisma",
        roll=1,
        target=75,
        success=True,
        degree="Critical Success",
        source_used="Base stat Charisma",
        message="Critical Success..."
    )
    
    mock_run_context.deps.character_service.perform_skill_check.return_value = mock_result
    
    result = skill_check_with_character(mock_run_context, "charisma", "normal")
    
    assert result.degree == "Critical Success"
    assert result.success is True


def test_skill_check_error(mock_run_context):
    """Test skill check error handling"""
    mock_run_context.deps.character_service.perform_skill_check.side_effect = Exception("Service error")
    
    # The tool now re-raises the exception
    with pytest.raises(Exception, match="Service error"):
        skill_check_with_character(mock_run_context, "perception")
