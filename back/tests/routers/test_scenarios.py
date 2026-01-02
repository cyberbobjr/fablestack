# Test file for scenarios.py router endpoints
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from back.app import app
from back.models.api.game import ScenarioList, ScenarioStatus

client = TestClient(app)

# Mock data for scenarios
MOCK_SCENARIOS_DATA = ScenarioList(
    scenarios=[
        ScenarioStatus(
            id="scen_pierres_passe",
            title="Les Pierres du Passé",
            name="Les_Pierres_du_Passe.md",
            status="available",
            session_id=None,
            scenario_name=None,
            character_name=None
        ),
        ScenarioStatus(
            name="Les_Pierres_du_Passe.md - Aragorn",
            status="in_progress",
            session_id=uuid4(),
            scenario_name="Les_Pierres_du_Passe.md",
            character_name="Aragorn"
        )
    ]
)

MOCK_SCENARIO_CONTENT = """# Scenario: The Stones of the Past

## Context
The story takes place in the year 2955 of the Third Age...

## 1. Locations
### Esgalbar Village
- **Description**: Small wooden houses village...
"""

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_list_scenarios_success(mock_scenario_service):
    """
    Test successful listing of scenarios.
    """
    # Create an async mock specifically for list_scenarios
    mock_scenario_service.list_scenarios = AsyncMock(return_value=MOCK_SCENARIOS_DATA)

    response = client.get("/api/scenarios/")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == 2
    assert data["scenarios"][0]["status"] == "available"
    assert data["scenarios"][0]["id"] == "scen_pierres_passe"
    assert data["scenarios"][0]["title"] == "Les Pierres du Passé"
    assert data["scenarios"][1]["status"] == "in_progress"
    assert data["scenarios"][1]["character_name"] == "Aragorn"

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_list_scenarios_empty(mock_scenario_service):
    """
    Test listing scenarios when no scenarios are available.
    """
    mock_scenario_service.list_scenarios = AsyncMock(return_value=ScenarioList(scenarios=[]))

    response = client.get("/api/scenarios/")
    assert response.status_code == 200
    data = response.json()
    assert data["scenarios"] == []

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_list_scenarios_only_available(mock_scenario_service):
    """
    Test listing scenarios with only available scenarios.
    """
    available_only = ScenarioList(
        scenarios=[
            ScenarioStatus(
                name="Scenario1.md",
                status="available",
                session_id=None,
                scenario_name=None,
                character_name=None
            ),
            ScenarioStatus(
                name="Scenario2.md",
                status="available",
                session_id=None,
                scenario_name=None,
                character_name=None
            )
        ]
    )
    mock_scenario_service.list_scenarios = AsyncMock(return_value=available_only)

    response = client.get("/api/scenarios/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) == 2
    for scenario in data["scenarios"]:
        assert scenario["status"] == "available"
        assert scenario["session_id"] is None
        assert scenario["character_name"] is None

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_list_scenarios_only_in_progress(mock_scenario_service):
    """
    Test listing scenarios with only in-progress scenarios.
    """
    in_progress_only = ScenarioList(
        scenarios=[
            ScenarioStatus(
                name="Scenario1.md - Character1",
                status="in_progress",
                session_id=uuid4(),
                scenario_name="Scenario1.md",
                character_name="Character1"
            )
        ]
    )
    mock_scenario_service.list_scenarios = AsyncMock(return_value=in_progress_only)

    response = client.get("/api/scenarios/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) == 1
    scenario = data["scenarios"][0]
    assert scenario["status"] == "in_progress"
    assert scenario["session_id"] is not None
    assert scenario["character_name"] == "Character1"

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_success(mock_scenario_service):
    """
    Test successful retrieval of scenario content.
    """
    mock_scenario_service.get_scenario_details = AsyncMock(return_value=MOCK_SCENARIO_CONTENT)

    response = client.get("/api/scenarios/Les_Pierres_du_Passe.md")
    assert response.status_code == 200
    content = response.text
    assert "# Scenario: The Stones of the Past" in content
    assert "## Context" in content

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_file_not_found(mock_scenario_service):
    """
    Test retrieval of scenario content when file does not exist.
    """
    mock_scenario_service.get_scenario_details = AsyncMock(side_effect=FileNotFoundError("Scenario 'nonexistent.md' not found."))

    response = client.get("/api/scenarios/nonexistent.md")
    assert response.status_code == 404
    assert "Scenario 'nonexistent.md' not found" in response.json()["detail"]

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_empty_content(mock_scenario_service):
    """
    Test retrieval of scenario content when file is empty.
    """
    mock_scenario_service.get_scenario_details = AsyncMock(return_value="")

    response = client.get("/api/scenarios/empty.md")
    assert response.status_code == 200
    # FastAPI returns strings as JSON, so empty string is '""'
    assert response.json() == ""

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_large_content(mock_scenario_service):
    """
    Test retrieval of scenario content with large content.
    """
    large_content = "# Large Scenario\n" + "\n".join([f"## Section {i}\nContent {i}" for i in range(1000)])
    mock_scenario_service.get_scenario_details = AsyncMock(return_value=large_content)

    response = client.get("/api/scenarios/large.md")
    assert response.status_code == 200
    assert len(response.text) > 10000  # Ensure large content is returned
    assert "Large Scenario" in response.text

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_special_characters(mock_scenario_service):
    """
    Test retrieval of scenario content with special characters and unicode.
    """
    content_with_special_chars = "# Scénario avec caractères spéciaux\n\nÉléments: àâäéèêëïîôöùûüÿ\n\nSymbols: ©®™€£¥"
    mock_scenario_service.get_scenario_details = AsyncMock(return_value=content_with_special_chars)

    response = client.get("/api/scenarios/special.md")
    assert response.status_code == 200
    assert "Scénario avec caractères spéciaux" in response.text
    assert "Éléments" in response.text


@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_filename_with_spaces(mock_scenario_service):
    """
    Test retrieval with filename containing spaces.
    """
    mock_scenario_service.get_scenario_details = AsyncMock(return_value="# Scenario with spaces\nContent")

    response = client.get("/api/scenarios/scenario%20with%20spaces.md")
    assert response.status_code == 200
    assert "Scenario with spaces" in response.text

@patch('back.routers.scenarios.ScenarioService')
@pytest.mark.asyncio
async def test_get_scenario_details_filename_with_dots(mock_scenario_service):
    """
    Test retrieval with filename containing multiple dots.
    """
    mock_scenario_service.get_scenario_details = AsyncMock(return_value="# Scenario.test.md\nContent")

    response = client.get("/api/scenarios/scenario.test.md")
    assert response.status_code == 200
    assert "Scenario.test.md" in response.text