from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from back.services.character_service import CharacterService
    from back.services.equipment_service import EquipmentService

class GameSessionContextProtocol(Protocol):
    """
    Protocol defining the expected interface for the GameSessionService 
    when accessed via RunContext in tools.
    """
    session_id: str
    character_id: Optional[str]
    scenario_id: str
    
    character_service: Optional["CharacterService"]
    equipment_service: Optional["EquipmentService"]
