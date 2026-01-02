import yaml
import os
from typing import Dict, List, Optional
from ...config import get_data_dir

class StatsManager:
    """
    Stats manager for the simplified V2 system (3–20).

    Purpose:
        Manages character statistics using the simplified 3-20 point scale system.
        This manager loads stat metadata from YAML, calculates modifiers using the
        simplified formula (value - 10) // 2, and tracks racial bonuses. It provides
        a clean interface for stat-related operations while abstracting the underlying
        calculation rules, enabling consistent stat management across character creation
        and gameplay.

    Attributes:
        _stats_info (Dict[str, Any]): Metadata for each stat from YAML.
        _stats (Dict[str, int]): Current stat values (defaults to 10).
        _racial_bonuses (Dict[str, int]): Racial bonuses for each stat.

    Note: Legacy concepts like 0–100 scales, 400 starting points, and cost tables
    are no longer used. Any related methods now behave as no-ops for compatibility.
    """

    def __init__(self):
        """Initialize the stats manager with default values (3–20 scale).

        **Description:** Loads stats data from YAML and initializes each stat
        value to 10 by default with zero racial bonuses.
        **Parameters:** None
        **Returns:** None
        """
        self.values: Dict[str, int] = {}
        self.racial_bonuses: Dict[str, int] = {}
        self._load_stats_data()
        # Initialize default values on the 3–20 scale
        for name in self.names:
            self.values[name] = 10
            self.racial_bonuses[name] = 0

    def _load_stats_data(self) -> None:
        """Load stats metadata from the YAML file.

        **Description:** Loads `stats.yaml` from the configured data directory.
        Only the `stats` section is required. Legacy fields (`bonus_table`,
        `cost_table`, `starting_points`) are optional and ignored by logic.
        **Parameters:** None
        **Returns:** None
        """
        data_path = os.path.join(get_data_dir(), "stats.yaml")
        with open(data_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        self.stats_info: Dict = data.get("stats", {})
        self.names: List[str] = list(self.stats_info.keys())
        # Legacy/optional fields retained for backward-compatible payloads
        self.bonus_table: Dict = data.get("bonus_table", {})
        self.cost_table: Dict = data.get("cost_table", {})
        self.starting_points: Optional[int] = data.get("starting_points")

    def get_description(self, stat: str) -> str:
        """Return the description of a stat.

        **Description:** Retrieves the description text for a given stat from the stats info.
        **Parameters:**
        - `stat` (str): Name of the stat to get description for.
        **Returns:** A string containing the stat description or empty string if not found.
        """
        stat_info = self.stats_info.get(stat, {})
        return stat_info.get("description", "")

    def get_bonus(self, stat: str) -> int:
        """Calculate the final modifier for a stat.

        **Description:** Computes the total modifier as the sum of the base
        modifier derived from the stat value using the simplified formula and
        the racial bonus.
        **Parameters:**
        - `stat` (str): Name of the stat to calculate the modifier for.
        **Returns:** An integer representing the total modifier for the stat.
        """
        base_value = self.values.get(stat, 10)
        base_bonus = self._get_base_bonus(base_value)
        racial_bonus = self.racial_bonuses.get(stat, 0)
        return base_bonus + racial_bonus

    def _get_base_bonus(self, value: int) -> int:
        """Calculate the base modifier from a stat value (3–20).

        **Description:** Applies the simplified rule: (value - 10) // 2.
        **Parameters:**
        - `value` (int): The stat value (expected range 3–20).
        **Returns:** The calculated modifier as an integer.
        """
        if not (3 <= value <= 20):
            # Clamp silently to keep manager resilient; validation happens elsewhere
            value = max(3, min(20, value))
        return (value - 10) // 2

    def calculate_cost(self, value: int) -> int:
        """Legacy no-op: stat cost calculation is no longer used.

        **Description:** Always returns 0 under the simplified 3–20 rules.
        **Parameters:**
        - `value` (int): Ignored.
        **Returns:** 0
        """
        return 0

    def _get_cost_for_value(self, value: int) -> int:
        """Legacy no-op: per-point cost is not applicable anymore.

        **Returns:** 0
        """
        return 0

    def set_racial_bonus(self, stat: str, bonus: int) -> None:
        """Set the racial bonus for a specific stat.

        **Description:** Assigns a racial bonus value to the specified stat.
        This bonus is added to the base bonus when calculating final bonuses.
        **Parameters:**
        - `stat` (str): Name of the stat to set racial bonus for.
        - `bonus` (int): The racial bonus value to assign.
        **Returns:** None.
        """
        self.racial_bonuses[stat] = bonus

    def set_value(self, stat: str, value: int) -> None:
        """Set the value of a specific stat (3–20).

        **Description:** Assigns a new value to the specified stat and validates
        it falls within the allowed range.
        **Parameters:**
        - `stat` (str): Name of the stat to set value for.
        - `value` (int): The new value (3–20).
        **Returns:** None.
        **Raises:**
        - ValueError: If value is out of the 3–20 range
        """
        if not (3 <= int(value) <= 20):
            raise ValueError(f"Stat '{stat}' must be between 3 and 20, got {value}")
        self.values[stat] = int(value)

    def get_all_stats_names(self) -> List[str]:
        """Get all available stat names.

        **Description:** Returns a list of all stat names available
        in the loaded stats data.
        **Parameters:** None.
        **Returns:** List[str] - A list containing all stat names.
        """
        return list(self.names)

    def get_all_stats_data(self) -> Dict:
        """Get all stats metadata for the V2 system.

        **Description:** Returns stat definitions and simplified rule hints. Legacy
        fields are included as empty/None for backward compatibility.
        **Parameters:** None.
        **Returns:** Dict with `stats`, `value_range`, `bonus_formula`, and legacy placeholders.
        """
        # Transform stats_info to match StatsResponse schema
        transformed_stats = {}
        for stat_name, stat_data in self.stats_info.items():
            stat_id = stat_name.lower()
            transformed_stats[stat_id] = {
                "id": stat_id,
                "name": stat_name,
                "description": stat_data.get("description", ""),
                "min_value": 3,
                "max_value": 20,
            }

        return {
            "stats": transformed_stats,
            "value_range": {"min": 3, "max": 20},
            "bonus_formula": "(value - 10) // 2",
            # Legacy placeholders
            "bonus_table": {},
            "cost_table": {},
            "starting_points": None,
        }

    def get_all_stats_with_values(self, stats: Optional[Dict[str, int]] = None) -> Dict:
        """Get all stats with their current values and bonuses.

        **Description:** Returns comprehensive stats information including
        the complete JSON structure plus current values and bonuses for each stat.
        **Parameters:**
        - `stats` (Dict[str, int], optional): Dictionary mapping stat
          names to their current values. Defaults to empty dictionary if None.
        **Returns:** Dict - A dictionary containing the complete stats data
        structure (stats, bonus_table, cost_table, starting_points) plus current
        values and bonuses for each stat.
        """
        stats = stats or {}

        result = self.get_all_stats_data()

        for name, stat_info in result["stats"].items():
            current_value = stats.get(name, 10)  # Default to 10 if not provided
            # Validate and set value
            try:
                self.set_value(name, current_value)
            except ValueError:
                # Clamp gracefully for output in case of invalid external data
                self.values[name] = max(3, min(20, int(current_value)))
            current_bonus = self.get_bonus(name)

            stat_info['current_value'] = current_value
            stat_info['current_bonus'] = current_bonus

        return result
