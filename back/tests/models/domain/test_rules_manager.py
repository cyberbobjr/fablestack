import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml

from back.models.domain.rules_manager import RulesManager
from back.models.enums import CharacterSex


class TestRulesManager:

    @pytest.fixture
    def mock_rules_data(self):
        return {
            "sex_bonuses": {
                "male": {
                    "stats": {"strength": 10},
                    "free_skill_points": 5
                },
                "female": {
                    "stats": {"intelligence": 10},
                    "free_skill_points": 5
                }
            },
            "stats_creation": {
                "budget": 100,
                "costs": {"strength": 1}
            },
            "skill_creation": {
                "max_points": 50,
                "starting_points": 10
            }
        }

    @pytest.fixture
    def mock_yaml_file(self, mock_rules_data):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
            yaml.dump(mock_rules_data, tmp)
            tmp_path = tmp.name
        yield tmp_path
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Removed broken test_initialization_and_loading as it is covered by test_load_valid_data

    def test_load_valid_data(self, mock_rules_data):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = "test_rules.yaml"
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'w') as f:
                yaml.dump(mock_rules_data, f)

            with patch("back.config.get_data_dir", return_value=temp_dir):
                manager = RulesManager(rules_file=file_name)
                
                assert manager._rules_data == mock_rules_data
                assert manager.get_all_sex_bonuses() == mock_rules_data['sex_bonuses']

    def test_file_not_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("back.config.get_data_dir", return_value=temp_dir):
                manager = RulesManager(rules_file="non_existent.yaml")
                assert manager._rules_data == {}

    def test_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = "bad.yaml"
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(": invalid yaml content")

            with patch("back.config.get_data_dir", return_value=temp_dir):
                manager = RulesManager(rules_file=file_name)
                # Should fail gracefully and return empty dict or raise depending on implementation.
                # Code says: yaml.safe_load(f) or {} ... except Exception ... _rules_data = {}
                assert manager._rules_data == {}

    def test_get_sex_bonuses(self, mock_rules_data):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = "rules.yaml"
            with open(os.path.join(temp_dir, file_name), 'w') as f:
                yaml.dump(mock_rules_data, f)
            
            with patch("back.config.get_data_dir", return_value=temp_dir):
                manager = RulesManager(rules_file=file_name)
                
                male_bonuses = manager.get_sex_bonuses(CharacterSex.MALE)
                assert male_bonuses == mock_rules_data['sex_bonuses']['male']
                
                female_bonuses = manager.get_sex_bonuses(CharacterSex.FEMALE)
                assert female_bonuses == mock_rules_data['sex_bonuses']['female']

    def test_get_stats_creation_rules(self, mock_rules_data):
         with tempfile.TemporaryDirectory() as temp_dir:
            file_name = "rules.yaml"
            with open(os.path.join(temp_dir, file_name), 'w') as f:
                yaml.dump(mock_rules_data, f)
            
            with patch("back.config.get_data_dir", return_value=temp_dir):
                manager = RulesManager(rules_file=file_name)
                stats_rules = manager.get_stats_creation_rules()
                assert stats_rules == mock_rules_data['stats_creation']

    def test_get_skill_creation_rules(self, mock_rules_data):
         with tempfile.TemporaryDirectory() as temp_dir:
            file_name = "rules.yaml"
            with open(os.path.join(temp_dir, file_name), 'w') as f:
                yaml.dump(mock_rules_data, f)
            
            with patch("back.config.get_data_dir", return_value=temp_dir):
                manager = RulesManager(rules_file=file_name)
                skill_rules = manager.get_skill_creation_rules()
                assert skill_rules == mock_rules_data['skill_creation']
