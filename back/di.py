"""
Dependency Injection Configuration for the application.
"""
from fastapi import FastAPI
from fastapi_injector import attach_injector
from injector import Binder, Injector, Module, SingletonScope

from back.agents.translation_agent import TranslationAgent
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.equipment_manager import EquipmentManager
from back.models.domain.races_manager import RacesManager
from back.models.domain.stats_manager import StatsManager
from back.models.domain.unified_skills_manager import UnifiedSkillsManager
from back.services.agent_runner_service import AgentRunnerService
from back.services.auth_service import AuthService
from back.services.character_data_service import CharacterDataService
from back.services.email_service import EmailService
from back.services.equipment_service import EquipmentService
from back.services.image_generation_service import ImageGenerationService
from back.services.races_data_service import RacesDataService
from back.services.settings_service import SettingsService
from back.services.skill_allocation_service import SkillAllocationService
from back.services.user_manager_factory import UserManagerFactory


class ServiceModule(Module):
    """
    Module for binding services.
    """
    def configure(self, binder: Binder) -> None:
        # Managers
        binder.bind(EquipmentManager, to=EquipmentManager, scope=SingletonScope)
        binder.bind(RacesManager, to=RacesManager, scope=SingletonScope)
        binder.bind(StatsManager, to=StatsManager, scope=SingletonScope)
        binder.bind(UnifiedSkillsManager, to=UnifiedSkillsManager, scope=SingletonScope)
        
        # Services
        binder.bind(CharacterDataService, to=CharacterDataService, scope=SingletonScope)
        binder.bind(RacesDataService, to=RacesDataService, scope=SingletonScope)
        binder.bind(SettingsService, to=SettingsService, scope=SingletonScope)
        binder.bind(AgentRunnerService, to=AgentRunnerService, scope=SingletonScope)
        binder.bind(TranslationAgent, to=TranslationAgent, scope=SingletonScope)
        binder.bind(EmailService, to=EmailService, scope=SingletonScope)
        binder.bind(SkillAllocationService, to=SkillAllocationService, scope=SingletonScope)
        binder.bind(ImageGenerationService, to=ImageGenerationService, scope=SingletonScope)

        # Services with complex dependencies or factories
        binder.bind(EquipmentService, to=EquipmentService, scope=SingletonScope)
        
        # User Manager & Auth (Instantiated via Factory)
        user_manager_instance = UserManagerFactory.get_user_manager()
        binder.bind(UserManagerProtocol, to=user_manager_instance, scope=SingletonScope)
        
        # Auth Service (depends on UserManagerProtocol, which is now bound)
        binder.bind(AuthService, to=AuthService, scope=SingletonScope)

def configure_injector(app: FastAPI) -> Injector:
    """
    Configures and attaches the injector to the FastAPI app.
    """
    injector = Injector([ServiceModule()])
    attach_injector(app, injector)
    return injector
