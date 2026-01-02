from haystack.tools import Tool
from haystack.dataclasses import ChatMessage
from back.utils.logger import log_debug
from typing import Any
import json


class LoggingTool(Tool):
    """
    ### LoggingTool
    **Description :** Wrapper qui enveloppe un outil Haystack pour intercepter et journaliser ses appels et résultats.
    **Paramètres :**
    - `wrapped_tool` (Tool) : L'outil Haystack à envelopper.
    - `store` : Instance du store pour sauvegarder l'historique des messages.
    - `agent` : Référence à l'agent pour accéder à son historique.
    **Retour :**
    - Instance de LoggingTool qui conserve toutes les fonctionnalités de l'outil original.
    """
    
    def __init__(self, wrapped_tool: Tool, store=None, agent=None):
        # Initialiser avec les propriétés de l'outil original
        super().__init__(
            name=wrapped_tool.name,
            description=wrapped_tool.description,
            parameters=wrapped_tool.parameters,
            function=self._wrapped_function
        )
        self.wrapped_tool = wrapped_tool
        self.store = store
        self.agent = agent
        self.original_function = wrapped_tool.function
        
    def _wrapped_function(self, **kwargs) -> Any:
        """
        ### _wrapped_function
        **Description :** Fonction wrapper qui intercepte l'appel à l'outil original.
        **Paramètres :**
        - `**kwargs` : Arguments passés à l'outil original.
        **Retour :**
        - Résultat de l'outil original.
        """
        # Journaliser l'appel de l'outil
        log_debug(
            f"Tool called: {self.name}",
            action="tool_called",
            tool_name=self.name,
            parameters=kwargs
        )        # Créer un message pour l'appel de l'outil
        tool_call_content = f"[TOOL_CALL] {self.name}: {json.dumps(kwargs, ensure_ascii=False)}"
        tool_call_message = ChatMessage.from_tool(
            tool_call_content,
            origin=self.name
        )
        
        # Ajouter à l'historique si l'agent est disponible
        if self.agent and hasattr(self.agent, '_chat_history'):
            self.agent._chat_history.append(tool_call_message)
        
        try:
            # Exécuter l'outil original
            result = self.original_function(**kwargs)
            
            # Journaliser le résultat
            log_debug(
                f"Tool completed: {self.name}",
                action="tool_completed",
                tool_name=self.name,
                result=str(result)[:200]  # Limiter la longueur pour les logs
            )            # Créer un message pour le résultat de l'outil
            tool_result_content = f"[TOOL_RESULT] {self.name}: {str(result)}"
            tool_result_message = ChatMessage.from_tool(
                tool_result_content,
                origin=self.name
            )
            
            # Ajouter à l'historique si l'agent est disponible
            if self.agent and hasattr(self.agent, '_chat_history'):
                self.agent._chat_history.append(tool_result_message)
                
                # Sauvegarder l'historique complet
                # if self.store:
                    # self.store.save(self.agent._chat_history)
            
            return result
            
        except Exception as e:
            # Journaliser l'erreur
            log_debug(
                f"Tool error: {self.name}",
                action="tool_error",
                tool_name=self.name,
                error=str(e)
            )            # Créer un message pour l'erreur
            tool_error_content = f"[TOOL_ERROR] {self.name}: {str(e)}"
            tool_error_message = ChatMessage.from_tool(
                tool_error_content,
                origin=self.name
            )
            
            # Ajouter à l'historique si l'agent est disponible
            if self.agent and hasattr(self.agent, '_chat_history'):
                self.agent._chat_history.append(tool_error_message)
                
                # Sauvegarder même en cas d'erreur
                if self.store:
                    self.store.save(self.agent._chat_history)
            
            # Re-lever l'exception
            raise e
    
    def set_agent(self, agent):
        """
        ### set_agent
        **Description :** Définit la référence à l'agent après sa création.
        **Paramètres :**
        - `agent` : Instance de l'agent Haystack.
        **Retour :** Aucun.
        """
        self.agent = agent


def wrap_tools_with_logging(tools: list, store=None) -> list:
    """
    ### wrap_tools_with_logging
    **Description :** Enveloppe une liste d'outils avec LoggingTool pour activer la journalisation.
    **Paramètres :**
    - `tools` (list) : Liste des outils Haystack à envelopper.
    - `store` : Instance du store pour la sauvegarde.
    **Retour :**
    - (list) : Liste des outils enveloppés avec LoggingTool.
    """
    wrapped_tools = []
    for tool in tools:
        if isinstance(tool, LoggingTool):
            # Déjà enveloppé, ajouter tel quel
            wrapped_tools.append(tool)
        else:
            # Envelopper avec LoggingTool
            wrapped_tool = LoggingTool(tool, store=store)
            wrapped_tools.append(wrapped_tool)
    
    return wrapped_tools
