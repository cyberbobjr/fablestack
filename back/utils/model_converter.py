"""
Utilitaire pour la conversion entre objets Pydantic et dictionnaires.
Centralise la logique pour respecter DRY et faciliter les tests.
"""

from typing import Any, Dict


class ModelConverter:
    """
    Classe utilitaire pour convertir des objets en dictionnaires de manière cohérente.
    Gère les objets Pydantic (model_dump), les objets avec dict(), et les objets standards.
    """

    @staticmethod
    def to_dict(obj: Any) -> Dict[str, Any]:
        """
        Convertit un objet en dictionnaire.

        Args:
            obj: L'objet à convertir (Pydantic model, dict, ou objet standard).

        Returns:
            Dict[str, Any]: Le dictionnaire de l'objet.

        Raises:
            ValueError: Si la conversion échoue.
        """
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif isinstance(obj, dict):
            return obj
        else:
            # Pour les objets standards, utiliser vars() ou retourner tel quel si déjà dict
            try:
                return vars(obj)
            except TypeError:
                raise ValueError(f"Impossible de convertir l'objet de type {type(obj)} en dictionnaire.")

    @staticmethod
    def to_json(obj: Any) -> str:
        """
        Convertit un objet en JSON string via model_dump_json si disponible.

        Args:
            obj: L'objet à convertir.

        Returns:
            str: La représentation JSON.
        """
        if hasattr(obj, 'model_dump_json'):
            return obj.model_dump_json()
        else:
            import json
            return json.dumps(ModelConverter.to_dict(obj))