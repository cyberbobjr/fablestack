"""
Services package initialization.
Handles circular import resolution by providing lazy imports.
"""
from typing import TYPE_CHECKING

# Type checking imports (won't cause circular imports)
if TYPE_CHECKING:
    from back.services.agent_runner_service import AgentRunnerService
    from back.services.character_data_service import CharacterDataService
    from back.services.character_service import CharacterService
    from back.services.combat_service import CombatService
    from back.services.equipment_service import EquipmentService
    from back.services.game_session_service import GameSessionService
    from back.services.logic_oracle_service import LogicOracleService
    from back.services.races_data_service import RacesDataService
    from back.services.scenario_service import ScenarioService
    from back.services.settings_service import SettingsService
    from back.services.skill_allocation_service import SkillAllocationService

# Runtime imports (lazy loading to avoid circular dependencies)
def __getattr__(name: str):
    """Lazy import mechanism to break circular dependencies."""
    if name == "GameSessionService":
        from back.services.game_session_service import GameSessionService
        return GameSessionService
    elif name == "CharacterService":
        from back.services.character_service import CharacterService
        return CharacterService
    elif name == "EquipmentService":
        from back.services.equipment_service import EquipmentService
        return EquipmentService
    elif name == "AgentRunnerService":
        from back.services.agent_runner_service import AgentRunnerService
        return AgentRunnerService
    elif name == "CombatService":
        from back.services.combat_service import CombatService
        return CombatService
    elif name == "LogicOracleService":
        from back.services.logic_oracle_service import LogicOracleService
        return LogicOracleService
    elif name == "RacesDataService":
        from back.services.races_data_service import RacesDataService
        return RacesDataService
    elif name == "ScenarioService":
        from back.services.scenario_service import ScenarioService
        return ScenarioService
    elif name == "SettingsService":
        from back.services.settings_service import SettingsService
        return SettingsService
    elif name == "SkillAllocationService":
        from back.services.skill_allocation_service import \
            SkillAllocationService
        return SkillAllocationService
    elif name == "CharacterDataService":
        from back.services.character_data_service import CharacterDataService
        return CharacterDataService

    raise AttributeError(f"module 'back.services' has no attribute '{name}'")