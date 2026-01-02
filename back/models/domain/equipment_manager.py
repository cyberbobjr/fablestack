"""
Equipment manager for the role-playing game system.
Loads and exposes equipment data from YAML file and exposes a
standardized item schema for use by services.

Canonical item keys:
- id (str): slug generated from name (lowercase, hyphens)
- name (str)
- category (str): one of 'weapon', 'armor', 'accessory', 'consumable'
- cost (float)
- weight (float)
- quantity (int, default 1)
- equipped (bool, default False)

Optional keys preserved from source data (not normalized beyond passthrough):
- damage (str), range (int|str) for weapons
- protection (int) for armor
- description (str), type (str)
"""

import os
import re
from typing import Any, Dict, List, Optional

import yaml

from back.config import get_data_dir


class EquipmentManager:
    """
    Equipment manager for the game.

    Purpose:
        Manages all equipment data loaded from YAML configuration files.
        This manager provides standardized access to weapons, armor, accessories, and
        consumables, ensuring consistent item schemas across the application. It handles
        data normalization, category classification, and item lookup operations, enabling
        services and tools to work with equipment without directly parsing YAML files.

    Attributes:
        _equipment_data (Optional[Dict[str, Any]]): Raw equipment data loaded from YAML.
    """
    
    @property
    def equipment_data(self) -> Dict[str, Any]:
        """Lazy load equipment data."""
        if self._equipment_data is None:
            self._equipment_data = self._load_equipment_data()
        return self._equipment_data
    
    def __init__(self):
        """
        ### __init__
        **Description:** Initialize equipment manager. Data is loaded lazily.
        **Parameters:** None
        **Returns:** None
        """
        self._equipment_data = None
    
    def _load_equipment_data(self) -> Dict[str, Any]:
        """
        ### _load_equipment_data
        **Description:** Load equipment data from YAML files (standard and unique).
        **Parameters:** None
        **Returns:** Equipment data dictionary (merged).
        """
        # Load standard equipment
        data_path = os.path.join(get_data_dir(), 'equipment.yaml')
        standard_data = {}
        try:
            with open(data_path, 'r', encoding='utf-8') as file:
                standard_data = yaml.safe_load(file) or {}
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Equipment data file not found: {data_path}. "
                f"Please ensure that file exists and contains valid YAML data with equipment definitions."
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in equipment file {data_path}: {str(e)}. "
                f"Please check the file format and syntax."
            )

        # Load unique items
        unique_path = os.path.join(get_data_dir(), 'unique_items.yaml')
        unique_data = {}
        if os.path.exists(unique_path):
            try:
                with open(unique_path, 'r', encoding='utf-8') as file:
                    unique_data = yaml.safe_load(file) or {}
            except yaml.YAMLError as e:
                # Log warning but don't crash if unique items file is corrupt? 
                # For now, let's raise to be safe or just log. Raising is safer for data integrity.
                raise yaml.YAMLError(
                    f"Invalid YAML in unique items file {unique_path}: {str(e)}."
                )
        
        # Merge data
        # Structure is { 'weapons': {...}, 'armor': {...}, 'items': {...} }
        merged_data = standard_data.copy()
        
        for category, items in unique_data.items():
            if category not in merged_data:
                merged_data[category] = {}
            if isinstance(items, dict):
                merged_data[category].update(items)
                
        return merged_data
            
    def get_all_equipment(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return all equipment as standardized dictionaries grouped by categories.

        Parameters:
        - None

        Returns:
        - Dict[str, List[Dict[str, Any]]]: Dictionary with keys 'weapons', 'armor', 'accessories', 'consumables'.

        Example output item (weapon):
        {
            "id": "longsword",
            "name": "Longsword",
            "category": "weapon",
            "cost_gold": 2,
            "cost_silver": 0,
            "cost_copper": 0,
            "weight": 1.5,
            "quantity": 1,
            "equipped": False,
            "damage": "1d8+4",
            "description": "Balanced and versatile one-handed sword"
        }
        """
        return self._standardize_catalog(self.equipment_data)
    
    def get_equipment_names(self) -> List[str]:
        """
        ### get_equipment_names
        **Description:** Retourne uniquement les noms de tous les équipements.
        **Paramètres:** Aucun
        **Retour:** Liste des noms d'équipements.
        """
        all_names = []
        for category in self.equipment_data.values():
            if isinstance(category, dict):
                all_names.extend(category.keys())
        return all_names
    
    def get_weapons(self) -> Dict[str, Dict[str, Any]]:
        """
        ### get_weapons
        **Description:** Retourne uniquement les armes.
        **Paramètres:** Aucun
        **Retour:** Dictionnaire des armes.
        """
        return self.equipment_data.get("weapons", {})
    
    def get_armor(self) -> Dict[str, Dict[str, Any]]:
        """
        ### get_armor
        **Description:** Retourne uniquement les armures.
        **Paramètres:** Aucun
        **Retour:** Dictionnaire des armures.
        """
        return self.equipment_data.get("armor", {})
    
    def get_items(self) -> Dict[str, Dict[str, Any]]:
        """
        ### get_items
        **Description:** Retourne uniquement les objets divers.
        **Paramètres:** Aucun
        **Retour:** Dictionnaire des objets.
        """
        return self.equipment_data.get("items", {})


    # --- Standardization helpers ---
    @staticmethod
    def _slugify(name: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip()).strip("-").lower()
        return s

    def _standardize_item(self, name: str, src: Dict[str, Any], category_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Standardize a raw YAML item to canonical dict with required keys.
        Category resolution:
        - 'weapons' group -> category 'weapon'
        - 'armor' group -> category 'armor'
        - 'items' group -> if type == 'consumable' -> 'consumable', else 'accessory'
        """
        category = category_hint
        if category_hint == 'weapons':
            category = 'weapon'
        elif category_hint == 'armor':
            category = 'armor'
        elif category_hint == 'items':
            category = 'consumable' if str(src.get('type', '')).lower() == 'consumable' else 'accessory'

        out: Dict[str, Any] = {
            'id': str(src.get('id') or self._slugify(name)),
            'name': name,
            'category': category or str(src.get('type', '')).lower() or 'accessory',
            'cost_gold': int(src.get('cost_gold', 0)),
            'cost_silver': int(src.get('cost_silver', 0)),
            'cost_copper': int(src.get('cost_copper', 0)),
            'weight': float(src.get('weight', 0)),
            'quantity': int(src.get('quantity', 1)),
            'equipped': False,
            'can_buy': src.get('canBuy', src.get('can_buy', True)),  # Default to True for standard catalog items
        }
        # Preserve common optional fields without renaming
        for key in ('damage', 'range', 'protection', 'description', 'type'):
            if key in src:
                out[key] = src[key]
        return out

    def _standardize_catalog(self, data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        weapons = []
        armor = []
        accessories = []
        consumables = []

        for group_name, group in data.items():
            # Skip non-dict groups and metadata sections
            if not isinstance(group, dict) or str(group_name).startswith('_'):
                continue
            for item_name, item_data in group.items():
                # Skip entries that are not proper item dictionaries (e.g., metadata strings)
                if not isinstance(item_data, dict):
                    continue
                std = self._standardize_item(item_name, item_data, category_hint=group_name)
                if std['category'] == 'weapon':
                    weapons.append(std)
                elif std['category'] == 'armor':
                    armor.append(std)
                elif std['category'] == 'consumable':
                    consumables.append(std)
                else:
                    accessories.append(std)

        return {
            'weapons': weapons,
            'armor': armor,
            'accessories': accessories,
            'consumables': consumables,
        }

    def get_equipment_by_id(self, id_or_name: str) -> Optional[Dict[str, Any]]:
        """
        Lookup an equipment item by canonical id (slug) or exact name, case-insensitive.
        Returns standardized item dict or None.
        """
        catalog = self._standardize_catalog(self.equipment_data)
        target = id_or_name.strip().lower()
        for lst in (catalog['weapons'], catalog['armor'], catalog['accessories'], catalog['consumables']):
            for it in lst:
                if it['id'] == target or it['name'].lower() == target:
                    return it
        return None

    def create_item(self, category: str, item_data: Dict[str, Any], is_unique: bool = False, can_buy: bool = False) -> str:
        """
        Create a new item in the equipment catalog and save it to YAML.
        
        Args:
            category (str): Target category ('weapon', 'armor', 'consumable', 'accessory').
            item_data (dict): Item details (name, cost, weight, etc.).
            is_unique (bool): If True, save to unique_items.yaml instead of equipment.yaml.
            
        Returns:
            str: The generated item_id.
        """
        # Ensure data is loaded
        if self._equipment_data is None:
            self._equipment_data = self._load_equipment_data()
            
        # Determine target group in YAML structure
        # YAML structure: weapons, armor, items (accessories + consumables)
        yaml_group = 'items'
        if category == 'weapon':
            yaml_group = 'weapons'
        elif category == 'armor':
            yaml_group = 'armor'
            
        # Generate ID
        name = item_data.get('name', 'Unknown Item')
        item_id = item_data.get('id') or f"{category}_{self._slugify(name)}"
        
        # Prepare data for YAML
        new_entry = {
            'id': item_id,
            'type': 'consumable' if category == 'consumable' else ('equipment' if category == 'accessory' else category),
            'weight': float(item_data.get('weight', 0)),
            'cost_gold': int(item_data.get('cost_gold', 0)),
            'cost_silver': int(item_data.get('cost_silver', 0)),
            'cost_copper': int(item_data.get('cost_copper', 0)),
            'description': item_data.get('description', ''),
            'canBuy': can_buy,
        }
        
        # Add optional fields
        if 'damage' in item_data:
            new_entry['damage'] = item_data['damage']
        if 'range' in item_data:
            new_entry['range'] = int(item_data['range'])
        if 'protection' in item_data:
            new_entry['protection'] = int(item_data['protection'])
        if 'properties' in item_data:
            new_entry['properties'] = item_data['properties']
        if 'quantity' in item_data:
            new_entry['quantity'] = int(item_data['quantity'])
            
        # Update in-memory data
        if yaml_group not in self._equipment_data:
            self._equipment_data[yaml_group] = {}
            
        self._equipment_data[yaml_group][name] = new_entry
        
        # Save to file
        if is_unique:
            self._save_unique_equipment_data(yaml_group, name, new_entry)
        else:
            self._save_standard_equipment_entry(yaml_group, name, new_entry)
        
        return item_id

    def _save_unique_equipment_data(self, group: str, name: str, entry: Dict[str, Any]) -> None:
        """Save a unique item to unique_items.yaml."""
        data_path = os.path.join(get_data_dir(), 'unique_items.yaml')
        try:
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file) or {}
            else:
                data = {}
            
            if group not in data:
                data[group] = {}
            
            data[group][name] = entry
            
            with open(data_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
        except Exception as e:
            raise IOError(f"Failed to save unique equipment data: {str(e)}")

    def _save_standard_equipment_entry(self, group: str, name: str, entry: Dict[str, Any]) -> None:
        """Save a standard item to equipment.yaml."""
        data_path = os.path.join(get_data_dir(), 'equipment.yaml')
        try:
            with open(data_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or {}
            
            if group not in data:
                data[group] = {}
            
            data[group][name] = entry
            
            with open(data_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
        except Exception as e:
            raise IOError(f"Failed to save equipment data: {str(e)}")

