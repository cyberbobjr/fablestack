import os
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from back.services.scenario_service import ScenarioService


class TestScenarioService:

    @pytest.mark.asyncio
    async def test_get_scenario_details_success(self, tmp_path):
        """Test retrieving scenario content."""
        scenario_file = "test_scenario.md"
        content = "# Test Scenario\n\nThis is a test."
        
        # Create scenario file
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        (scenarios_dir / scenario_file).write_text(content, encoding="utf-8")
        
        with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
            result = await ScenarioService.get_scenario_details(scenario_file)
            
            assert result == content

    @pytest.mark.asyncio
    async def test_get_scenario_details_not_found(self, tmp_path):
        """Test retrieving non-existent scenario."""
        with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
            with pytest.raises(FileNotFoundError, match="does not exist"):
                await ScenarioService.get_scenario_details("nonexistent.md")

    @pytest.mark.asyncio
    async def test_list_scenarios_empty(self, tmp_path):
        """Test listing scenarios when none exist."""
        # Create empty directories
        (tmp_path / "scenarios").mkdir()
        (tmp_path / "sessions").mkdir()
        
        with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
            result = await ScenarioService.list_scenarios()
            
            assert len(result.scenarios) == 0

    @pytest.mark.asyncio
    async def test_list_scenarios_available_only(self, tmp_path):
        """Test listing available scenarios."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        (scenarios_dir / "scenario1.md").write_text("# Scenario 1")
        (scenarios_dir / "scenario2.md").write_text("# Scenario 2")
        (tmp_path / "sessions").mkdir()
        
        with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
            result = await ScenarioService.list_scenarios()
            
            assert len(result.scenarios) == 2
            assert all(s.status == "available" for s in result.scenarios)
            assert {s.name for s in result.scenarios} == {"scenario1.md", "scenario2.md"}

    @pytest.mark.asyncio
    async def test_initiate_creation_generates_timestamp_id(self, tmp_path):
        """Test that initiate_creation generates timestamp-based IDs in the expected format."""
        description = "A test scenario description"
        
        with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
            # Call initiate_creation
            result = await ScenarioService.initiate_creation(description)
            
            # Verify the ID format matches scen_YYYYMMDD_HHMMSS
            assert result.id is not None
            assert re.match(r'^scen_\d{8}_\d{6}$', result.id), f"ID format incorrect: {result.id}"
            
            # Verify the filename matches the ID with .md extension
            assert result.name == f"{result.id}.md"
            
            # Verify the initial title is "Generating..."
            assert result.title == "Generating..."
            
            # Verify the status is "creating"
            assert result.status == "creating"
            
            # Verify the file was created in the scenarios directory
            file_path = os.path.join(str(tmp_path), "scenarios", result.name)
            assert os.path.exists(file_path)
            
            # Verify the file content has the expected frontmatter
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert f"id: {result.id}" in content
                assert "title: Generating..." in content
                assert "status: creating" in content

    @pytest.mark.asyncio
    async def test_initiate_creation_file_already_exists(self, tmp_path):
        """Test that initiate_creation raises FileExistsError if file already exists."""
        description = "A test scenario description"
        
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        with patch('back.services.scenario_service.get_data_dir', return_value=str(tmp_path)):
            # Mock datetime to ensure consistent filename
            fixed_datetime = datetime(2024, 1, 15, 10, 30, 45)
            with patch('back.services.scenario_service.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_datetime
                
                # Create the file first
                expected_filename = "scen_20240115_103045.md"
                (scenarios_dir / expected_filename).write_text("existing content")
                
                # Attempt to create again should raise FileExistsError
                with pytest.raises(FileExistsError, match="already exists"):
                    await ScenarioService.initiate_creation(description)
