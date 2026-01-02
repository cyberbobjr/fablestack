"""
Manager for loading and accessing game rules.
"""
import os
from functools import lru_cache
from typing import Any, Dict, Optional

import yaml

from back.models.enums import CharacterSex
from back.utils.logger import log_info


class RulesManager:
    """
    Manages access to game rules defined in rules.yaml
    """
    
    def __init__(self, rules_file: str = "back/gamedata/rules.yaml"):
        self.rules_file: str = rules_file
        self._rules_data: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load rules from YAML file"""
        # Use get_data_dir to resolve the path to rules.yaml
        # rules_file is expected to be just the filename "rules.yaml" or relative to data dir
        # If self.rules_file is absolute, os.path.join will use it as is (on Linux), 
        # but the default in __init__ is currently "back/gamedata/rules.yaml".
        # We should clean that up or handle it. 
        # Ideally, we change the default in __init__ too, but let's handle the path here safely.
        
        from back.config import get_data_dir
        
        data_dir = get_data_dir()
        filename = os.path.basename(self.rules_file) # Extract just "rules.yaml" if a path was passed
        
        # Construct path: data_dir + filename
        # data_dir is usually .../back/gamedata
        self.rules_file = os.path.join(data_dir, filename)
        
        abs_path = os.path.abspath(self.rules_file)
        
        if os.path.exists(abs_path):
            try:
                log_info(f"Loading rules from {abs_path}")
                with open(abs_path, 'r', encoding='utf-8') as f:
                    self._rules_data = yaml.safe_load(f) or {}
                log_info(f"DEBUG: Loaded keys: {list(self._rules_data.keys())}")
            except Exception as e:
                log_info(f"Failed to load rules from {abs_path}: {e}")
                self._rules_data = {}
        else:
            log_info(f"WARNING: Rules file not found at {abs_path}")
            self._rules_data = {}

    def get_sex_bonuses(self, sex: CharacterSex) -> Dict[str, Any]:
        """
        Get bonuses for a specific sex.
        Returns a dict with 'stats', 'free_skill_points', etc.
        """
        sex_key = sex.value.lower()
        return self._rules_data.get('sex_bonuses', {}).get(sex_key, {})

    @lru_cache(maxsize=1)
    def get_all_sex_bonuses(self) -> Dict[str, Any]:
        """Get all sex bonuses configuration"""
        return self._rules_data.get('sex_bonuses', {})

    def get_stats_creation_rules(self) -> Dict[str, Any]:
        """
        Get stats creation rules (budget, costs, etc.)
        """
        return self._rules_data.get('stats_creation', {})

    def get_skill_creation_rules(self) -> Dict[str, Any]:
        """
        Get skill creation rules (max_points, starting_points)
        """
        return self._rules_data.get('skill_creation', {})
