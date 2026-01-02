from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from back.app import app
from back.models.api.game import TimelineEvent
from back.models.enums import TimelineEventType

client = TestClient(app)

def test_restore_history_by_timestamp_success():
    """
    Test successful history restoration using timestamp.
    Should remove all events >= timestamp.
    """
    mock_session_id = uuid4()
    
    # Mock Timeline (Frontend)
    # Timestamps: t1 < t2 < t3
    timeline = [
        TimelineEvent(type=TimelineEventType.NARRATIVE, timestamp="2023-01-01T10:00:00Z", content="e1"),
        TimelineEvent(type=TimelineEventType.NARRATIVE, timestamp="2023-01-01T10:01:00Z", content="e2"), # Target
        TimelineEvent(type=TimelineEventType.NARRATIVE, timestamp="2023-01-01T10:02:00Z", content="e3")
    ]
    
    # Mock LLM History (Backend)
    # Timestamps: t1 < t2 < t3
    llm_history = [
        {
            "kind": "request",
            "timestamp": "2023-01-01T10:00:00Z", 
            "parts": [{"part_kind": "user-prompt", "content": "msg1"}]
        },
        {
            "kind": "request",
            "timestamp": "2023-01-01T10:01:00Z", 
            "parts": [{"part_kind": "user-prompt", "content": "msg2"}]
        }, # Target
        {
            "kind": "request",
            "timestamp": "2023-01-01T10:02:00Z", 
            "parts": [{"part_kind": "user-prompt", "content": "msg3"}]
        },
        {
            "kind": "request",
            "timestamp": "2023-01-01T10:03:00Z", 
            "parts": [{"part_kind": "user-prompt", "content": "msg4"}]
        }  # Extra later msg
    ]

    target_timestamp = "2023-01-01T10:01:00Z" # Matches e2 and msg2

    with patch('back.routers.gamesession.GameSessionService.load', new_callable=AsyncMock) as mock_load:
        mock_session = MagicMock()
        mock_load.return_value = mock_session
        
        # Mock loading methods
        mock_session.load_timeline_events = AsyncMock(return_value=timeline)
        
        async def mock_load_history_raw(kind):
            if "narrative_llm" in kind:
                return llm_history
            return []
        mock_session.load_history_raw_json = AsyncMock(side_effect=mock_load_history_raw)
        
        # Mock saving methods
        mock_session.save_timeline_events = AsyncMock()
        mock_session.save_history_llm = AsyncMock()
        
        # ACT
        response = client.post(
            f"/api/gamesession/history/{mock_session_id}/restore",
            json={"timestamp": target_timestamp}
        )
        
        # ASSERT
        assert response.status_code == 204
        
        # Check Timeline Save
        # Should keep only items < target (e1)
        mock_session.save_timeline_events.assert_called_once()
        call_args = mock_session.save_timeline_events.call_args
        saved_timeline = call_args[0][0]
        assert call_args[1].get('overwrite') is True
        assert len(saved_timeline) == 1
        assert saved_timeline[0].timestamp == "2023-01-01T10:00:00Z"
        
        # Check LLM History Save
        # Should keep only items < target (msg1)
        mock_session.save_history_llm.assert_called_once()
        args, _ = mock_session.save_history_llm.call_args
        assert args[0] == "narrative" # kind
        saved_llm_history = args[1] # pydantic model list
        
        # We need to inspect the saved list. It will be a list of Pydantic models (Message/dict-like)
        assert len(saved_llm_history) == 1
        # Pydantic adapter returns list of models or dicts depending on schema, 
        # but here we validated raw dicts. 
        # Let's check the first item.
        # Note: ModelMessagesTypeAdapter.validate_python returns a list of Message objects usually.
        # But for simplicity here assume it works or check count.
        
def test_restore_history_nested_timestamp():
    """
    Test that timestamps hidden deep in parts are found.
    """
    mock_session_id = uuid4()
    
    # LLM History with nested timestamp
    llm_history = [
        {
            "kind": "request",
            "parts": [{"part_kind": "user-prompt", "content": "msg1", "timestamp": "2023-01-01T10:00:00Z"}]
        }, # < target
        {
            "kind": "request",
            "parts": [{"part_kind": "user-prompt", "content": "msg2", "timestamp": "2023-01-01T11:00:00Z"}]
        }  # > target
    ]
    
    # Empty timeline for simplicity
    timeline = []
    
    target_timestamp = "2023-01-01T10:30:00Z"

    with patch('back.routers.gamesession.GameSessionService.load', new_callable=AsyncMock) as mock_load:
        mock_session = MagicMock()
        mock_load.return_value = mock_session
        mock_session.load_timeline_events = AsyncMock(return_value=timeline)
        mock_session.load_history_raw_json = AsyncMock(return_value=llm_history)
        mock_session.save_timeline_events = AsyncMock()
        mock_session.save_history_llm = AsyncMock()
        
        response = client.post(
            f"/api/gamesession/history/{mock_session_id}/restore",
            json={"timestamp": target_timestamp}
        )
        
        assert response.status_code == 204
        
        # Check LLM Save
        mock_session.save_history_llm.assert_called_once()
        args, _ = mock_session.save_history_llm.call_args
        saved_llm = args[1]
        assert len(saved_llm) == 1
