"""
Unit tests for PydanticJsonlStore.
Covers all methods, normal cases, and edge cases.
"""

import pytest
import os
from pathlib import Path

from back.storage.pydantic_jsonl_store import PydanticJsonlStore
from pydantic_ai.messages import ModelMessagesTypeAdapter, TextPart, UserPromptPart


@pytest.fixture
def temp_filepath(tmp_path: Path) -> str:
    """Fixture providing a temporary file path for testing."""
    return str(tmp_path / "test_store.jsonl")


class TestPydanticJsonlStore:
    """Test suite for PydanticJsonlStore."""

    def test_init_creates_file_if_not_exists(self, temp_filepath: str) -> None:
        """Test that __init__ creates the file if it doesn't exist."""
        assert not os.path.exists(temp_filepath)
        store = PydanticJsonlStore(temp_filepath)
        assert os.path.exists(temp_filepath)
        assert os.path.getsize(temp_filepath) == 0  # Empty file

    def test_init_creates_directory_if_not_exists(self, tmp_path: Path) -> None:
        """Test that __init__ creates the directory structure if it doesn't exist."""
        subdir = tmp_path / "new_subdir"
        filepath = subdir / "store.jsonl"
        assert not subdir.exists()
        store = PydanticJsonlStore(str(filepath))
        assert subdir.exists()
        assert filepath.exists()

    def test_init_with_existing_file(self, temp_filepath: str) -> None:
        """Test that __init__ works with an existing file."""
        Path(temp_filepath).write_text("existing content")
        store = PydanticJsonlStore(temp_filepath)
        assert Path(temp_filepath).read_text() == "existing content"  # Should not overwrite

    def test_save_pydantic_history_empty_list(self, temp_filepath: str) -> None:
        """Test saving an empty list of messages."""
        store = PydanticJsonlStore(temp_filepath)
        messages = []
        store.save_pydantic_history(messages)
        loaded = store.load_pydantic_history()
        assert loaded == []

    def test_save_and_load_pydantic_history_with_messages(self, temp_filepath: str) -> None:
        """Test saving and loading a list with messages."""
        store = PydanticJsonlStore(temp_filepath)
        # Create a sample message using the adapter
        sample_data = [
            {
                "kind": "request",
                "parts": [
                    {
                        "content": "Hello",
                        "timestamp": "2025-11-19T10:00:00.000000Z",
                        "part_kind": "user-prompt"
                    }
                ]
            }
        ]
        messages = ModelMessagesTypeAdapter.validate_python(sample_data)
        store.save_pydantic_history(messages)
        loaded = store.load_pydantic_history()
        assert len(loaded) == 1
        assert loaded[0].kind == "request"
        assert isinstance(loaded[0].parts[0], UserPromptPart)
        assert loaded[0].parts[0].content == "Hello"

    def test_save_overwrites_existing_content(self, temp_filepath: str) -> None:
        """Test that saving overwrites existing content."""
        store = PydanticJsonlStore(temp_filepath)
        # Save initial messages
        initial_data = [{"kind": "request", "parts": [{"content": "Initial", "part_kind": "user-prompt"}]}]
        initial_messages = ModelMessagesTypeAdapter.validate_python(initial_data)
        store.save_pydantic_history(initial_messages)
        # Save new messages
        new_data = [{"kind": "response", "parts": [{"content": "New", "part_kind": "text"}]}]
        new_messages = ModelMessagesTypeAdapter.validate_python(new_data)
        store.save_pydantic_history(new_messages)
        loaded = store.load_pydantic_history()
        assert len(loaded) == 1
        assert loaded[0].kind == "response"
        assert isinstance(loaded[0].parts[0], TextPart)
        assert loaded[0].parts[0].content == "New"

    def test_load_pydantic_history_from_empty_file(self, temp_filepath: str) -> None:
        """Test loading from an empty file."""
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_pydantic_history()
        assert loaded == []

    def test_load_pydantic_history_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from a file that doesn't exist."""
        filepath = tmp_path / "nonexistent.jsonl"
        store = PydanticJsonlStore(str(filepath))
        # Delete the file created by __init__
        os.remove(str(filepath))
        loaded = store.load_pydantic_history()
        assert loaded == []

    def test_load_pydantic_history_invalid_json(self, temp_filepath: str) -> None:
        """Test loading when the file contains invalid JSON."""
        Path(temp_filepath).write_text("invalid json content")
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_pydantic_history()
        assert loaded == []  # Should return empty list on error

    def test_load_pydantic_history_valid_json_invalid_pydantic(self, temp_filepath: str) -> None:
        """Test loading when JSON is valid but not valid for PydanticAI."""
        Path(temp_filepath).write_text('[{"invalid": "structure"}]')
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_pydantic_history()
        assert loaded == []  # Should return empty list on validation error

    def test_load_pydantic_history_with_whitespace_only(self, temp_filepath: str) -> None:
        """Test loading from a file with only whitespace."""
        Path(temp_filepath).write_text("   \n\t  ")
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_pydantic_history()
        assert loaded == []

    def test_save_and_load_multiple_messages(self, temp_filepath: str) -> None:
        """Test saving and loading multiple messages."""
        store = PydanticJsonlStore(temp_filepath)
        sample_data = [
            {"kind": "request", "parts": [{"content": "Msg1", "part_kind": "user-prompt"}]},
            {"kind": "response", "parts": [{"content": "Reply1", "part_kind": "text"}]},
            {"kind": "request", "parts": [{"content": "Msg2", "part_kind": "user-prompt"}]}
        ]
        messages = ModelMessagesTypeAdapter.validate_python(sample_data)
        store.save_pydantic_history(messages)
        loaded = store.load_pydantic_history()
        assert len(loaded) == 3
        assert isinstance(loaded[0].parts[0], UserPromptPart)
        assert loaded[0].parts[0].content == "Msg1"
        assert isinstance(loaded[1].parts[0], TextPart)
        assert loaded[1].parts[0].content == "Reply1"
        assert isinstance(loaded[2].parts[0], UserPromptPart)
        assert loaded[2].parts[0].content == "Msg2"

    def test_filepath_with_special_characters(self, tmp_path: Path) -> None:
        """Test with filepath containing special characters."""
        special_path = tmp_path / "test-file_with.special.chars.jsonl"
        store = PydanticJsonlStore(str(special_path))
        messages = []
        store.save_pydantic_history(messages)
        loaded = store.load_pydantic_history()
        assert loaded == []
        assert special_path.exists()

    def test_very_long_filepath(self, tmp_path: Path) -> None:
        """Test with a very long filepath (edge case for path length)."""
        long_name = "a" * 200  # Long filename
        long_path = tmp_path / f"{long_name}.jsonl"
        store = PydanticJsonlStore(str(long_path))
        messages = []
        store.save_pydantic_history(messages)
        loaded = store.load_pydantic_history()
        assert loaded == []
        assert long_path.exists()

    def test_load_raw_json_history_empty_list(self, temp_filepath: str) -> None:
        """Test loading raw JSON from an empty list."""
        store = PydanticJsonlStore(temp_filepath)
        messages = []
        store.save_pydantic_history(messages)
        loaded = store.load_raw_json_history()
        assert loaded == []

    def test_load_raw_json_history_with_messages(self, temp_filepath: str) -> None:
        """Test loading raw JSON with messages."""
        store = PydanticJsonlStore(temp_filepath)
        # Create a sample message using the adapter
        sample_data = [
            {
                "kind": "request",
                "parts": [
                    {
                        "content": "Hello",
                        "timestamp": "2025-11-19T10:00:00.000000Z",
                        "part_kind": "user-prompt"
                    }
                ]
            }
        ]
        messages = ModelMessagesTypeAdapter.validate_python(sample_data)
        store.save_pydantic_history(messages)
        loaded = store.load_raw_json_history()
        assert len(loaded) == 1
        assert loaded[0]["kind"] == "request"
        assert loaded[0]["parts"][0]["content"] == "Hello"
        assert loaded[0]["parts"][0]["part_kind"] == "user-prompt"

    def test_load_raw_json_history_from_empty_file(self, temp_filepath: str) -> None:
        """Test loading raw JSON from an empty file."""
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_raw_json_history()
        assert loaded == []

    def test_load_raw_json_history_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading raw JSON from a file that doesn't exist."""
        filepath = tmp_path / "nonexistent.jsonl"
        store = PydanticJsonlStore(str(filepath))
        # Delete the file created by __init__
        os.remove(str(filepath))
        loaded = store.load_raw_json_history()
        assert loaded == []

    def test_load_raw_json_history_invalid_json(self, temp_filepath: str) -> None:
        """Test loading raw JSON when the file contains invalid JSON."""
        Path(temp_filepath).write_text("invalid json content")
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_raw_json_history()
        assert loaded == []  # Should return empty list on error

    def test_load_raw_json_history_with_whitespace_only(self, temp_filepath: str) -> None:
        """Test loading raw JSON from a file with only whitespace."""
        Path(temp_filepath).write_text("   \n\t  ")
        store = PydanticJsonlStore(temp_filepath)
        loaded = store.load_raw_json_history()
        assert loaded == []

    def test_load_raw_json_history_multiple_messages(self, temp_filepath: str) -> None:
        """Test loading raw JSON with multiple messages."""
        store = PydanticJsonlStore(temp_filepath)
        sample_data = [
            {"kind": "request", "parts": [{"content": "Msg1", "part_kind": "user-prompt"}]},
            {"kind": "response", "parts": [{"content": "Reply1", "part_kind": "text"}]},
            {"kind": "request", "parts": [{"content": "Msg2", "part_kind": "user-prompt"}]}
        ]
        messages = ModelMessagesTypeAdapter.validate_python(sample_data)
        store.save_pydantic_history(messages)
        loaded = store.load_raw_json_history()
        assert len(loaded) == 3
        assert loaded[0]["parts"][0]["content"] == "Msg1"
        assert loaded[1]["parts"][0]["content"] == "Reply1"
        assert loaded[2]["parts"][0]["content"] == "Msg2"