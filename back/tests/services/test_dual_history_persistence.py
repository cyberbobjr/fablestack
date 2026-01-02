import pytest
import os
from unittest.mock import MagicMock, patch
from back.services.game_session_service import GameSessionService, HISTORY_NARRATIVE
from pydantic_ai.messages import ModelMessage, UserPromptPart, ModelRequest

@pytest.fixture
def mock_data_dir(tmp_path):
    with patch("back.services.game_session_service.get_data_dir", return_value=str(tmp_path)):
        yield tmp_path

@pytest.fixture
def service(mock_data_dir):
    # Create session dir
    session_id = "test-session"
    (mock_data_dir / "sessions" / session_id).mkdir(parents=True)
    (mock_data_dir / "sessions" / session_id / "character.txt").write_text("char1")
    (mock_data_dir / "sessions" / session_id / "scenario.txt").write_text("scen1")
    
    with patch("back.services.game_session_service.GameSessionService._initialize_services"):
        svc = GameSessionService(session_id)
        return svc

@pytest.mark.asyncio
async def test_dual_history_persistence(service, mock_data_dir):
    messages_ui = [ModelRequest(parts=[UserPromptPart(content="UI Message")])]
    messages_llm = [ModelRequest(parts=[UserPromptPart(content="LLM Message")])]
    
    # Save UI history
    await service.save_history(HISTORY_NARRATIVE, messages_ui)
    
    # Save LLM history
    await service.save_history_llm(HISTORY_NARRATIVE, messages_llm)
    
    # Verify files
    session_dir = mock_data_dir / "sessions" / service.session_id
    ui_file = session_dir / f"history_{HISTORY_NARRATIVE}.jsonl"
    llm_file = session_dir / f"history_{HISTORY_NARRATIVE}_llm.jsonl"
    
    assert ui_file.exists()
    assert llm_file.exists()
    
    # Check content (simplified check)
    assert "UI Message" in ui_file.read_text()
    assert "LLM Message" in llm_file.read_text()
    assert "LLM Message" not in ui_file.read_text()
    assert "UI Message" not in llm_file.read_text()

@pytest.mark.asyncio
async def test_load_history_llm(service, mock_data_dir):
    messages = [ModelRequest(parts=[UserPromptPart(content="Test Load")])]
    await service.save_history_llm(HISTORY_NARRATIVE, messages)
    
    loaded = await service.load_history_llm(HISTORY_NARRATIVE)
    assert len(loaded) == 1
    assert loaded[0].parts[0].content == "Test Load"
