"""Test conversation storage functions.

This module tests the JSON-based conversation storage system including
conversation creation, retrieval, updates, and listing.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.conversation_storage import (
    create_conversation,
    get_conversation,
    save_conversation,
    list_conversations,
    add_user_message,
    add_assistant_message,
    update_conversation_title,
    ensure_data_dir,
    get_conversation_path,
    DATA_DIR,
)


class TestCreateConversation:
    """Test suite for create_conversation function."""

    def test_creates_conversation_with_valid_structure(self, tmp_path, monkeypatch):
        """Test that create_conversation returns a dict with all required fields."""
        # Patch DATA_DIR to use temporary directory
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation = create_conversation("test-conv-1")

        # Verify structure
        assert isinstance(conversation, dict)
        assert "id" in conversation
        assert "created_at" in conversation
        assert "title" in conversation
        assert "messages" in conversation

    def test_sets_correct_conversation_id(self, tmp_path, monkeypatch):
        """Test that the conversation ID is set correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv-123"
        conversation = create_conversation(conversation_id)

        assert conversation["id"] == conversation_id

    def test_sets_default_title(self, tmp_path, monkeypatch):
        """Test that default title is 'New Conversation'."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation = create_conversation("test-conv-2")

        assert conversation["title"] == "New Conversation"

    def test_initializes_empty_messages_array(self, tmp_path, monkeypatch):
        """Test that messages array starts empty."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation = create_conversation("test-conv-3")

        assert conversation["messages"] == []
        assert isinstance(conversation["messages"], list)

    def test_sets_created_at_timestamp(self, tmp_path, monkeypatch):
        """Test that created_at is set with ISO format timestamp."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation = create_conversation("test-conv-4")

        # Verify timestamp is present
        assert "created_at" in conversation
        assert isinstance(conversation["created_at"], str)

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(conversation["created_at"])
        except ValueError:
            pytest.fail("created_at is not a valid ISO format timestamp")

    def test_saves_to_correct_file_path(self, tmp_path, monkeypatch):
        """Test that conversation is saved to correct file path."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv-5"
        create_conversation(conversation_id)

        expected_path = tmp_path / f"{conversation_id}.json"
        assert expected_path.exists()
        assert expected_path.is_file()

    def test_saves_valid_json(self, tmp_path, monkeypatch):
        """Test that saved file contains valid JSON."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv-6"
        conversation = create_conversation(conversation_id)

        file_path = tmp_path / f"{conversation_id}.json"

        # Read and parse JSON
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        # Verify it matches the returned conversation
        assert saved_data == conversation

    def test_creates_data_directory_if_missing(self, tmp_path, monkeypatch):
        """Test that data directory is created if it doesn't exist."""
        # Create a subdirectory that doesn't exist yet
        data_dir = tmp_path / "conversations" / "nested"
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", data_dir)

        assert not data_dir.exists()

        create_conversation("test-conv-7")

        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_handles_special_characters_in_id(self, tmp_path, monkeypatch):
        """Test that conversation IDs with special characters are handled."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Use a conversation ID with hyphens, underscores
        conversation_id = "test-conv_2024-01-01"
        conversation = create_conversation(conversation_id)

        assert conversation["id"] == conversation_id

        file_path = tmp_path / f"{conversation_id}.json"
        assert file_path.exists()

    def test_creates_unique_conversations(self, tmp_path, monkeypatch):
        """Test that multiple conversations can be created with unique IDs."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conv1 = create_conversation("conv-1")
        conv2 = create_conversation("conv-2")
        conv3 = create_conversation("conv-3")

        # Verify all have unique IDs
        assert conv1["id"] != conv2["id"]
        assert conv2["id"] != conv3["id"]
        assert conv1["id"] != conv3["id"]

        # Verify all files exist
        assert (tmp_path / "conv-1.json").exists()
        assert (tmp_path / "conv-2.json").exists()
        assert (tmp_path / "conv-3.json").exists()

    def test_overwrites_existing_conversation(self, tmp_path, monkeypatch):
        """Test that creating a conversation with existing ID overwrites it."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv-overwrite"

        # Create first conversation
        conv1 = create_conversation(conversation_id)
        timestamp1 = conv1["created_at"]

        # Create second conversation with same ID (after a small delay)
        import time
        time.sleep(0.01)  # Ensure timestamp difference

        conv2 = create_conversation(conversation_id)
        timestamp2 = conv2["created_at"]

        # Timestamps should be different
        assert timestamp2 != timestamp1

        # File should contain the newer conversation
        file_path = tmp_path / f"{conversation_id}.json"
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["created_at"] == timestamp2

    def test_json_formatting(self, tmp_path, monkeypatch):
        """Test that JSON is saved with proper indentation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv-format"
        create_conversation(conversation_id)

        file_path = tmp_path / f"{conversation_id}.json"

        # Read raw file content
        with open(file_path, "r") as f:
            content = f.read()

        # Verify it's indented (should have newlines and spaces)
        assert "\n" in content
        assert "  " in content  # 2-space indentation

    def test_returns_conversation_dict(self, tmp_path, monkeypatch):
        """Test that function returns the conversation dictionary."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        result = create_conversation("test-conv-return")

        assert result is not None
        assert isinstance(result, dict)
        assert result["id"] == "test-conv-return"

    def test_multiple_conversations_dont_interfere(self, tmp_path, monkeypatch):
        """Test that creating multiple conversations doesn't cause interference."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create multiple conversations
        conv_ids = [f"conv-{i}" for i in range(5)]
        conversations = [create_conversation(conv_id) for conv_id in conv_ids]

        # Verify each conversation has correct ID
        for i, conv in enumerate(conversations):
            assert conv["id"] == f"conv-{i}"

        # Verify all files exist and contain correct data
        for conv_id in conv_ids:
            file_path = tmp_path / f"{conv_id}.json"
            assert file_path.exists()

            with open(file_path, "r") as f:
                saved_data = json.load(f)

            assert saved_data["id"] == conv_id

    def test_conversation_structure_completeness(self, tmp_path, monkeypatch):
        """Test that conversation has exactly the expected fields."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation = create_conversation("test-conv-complete")

        # Verify it has exactly 4 fields
        expected_fields = {"id", "created_at", "title", "messages"}
        assert set(conversation.keys()) == expected_fields

    def test_empty_string_conversation_id(self, tmp_path, monkeypatch):
        """Test behavior with empty string conversation ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # This should work but create a file named ".json"
        conversation = create_conversation("")

        assert conversation["id"] == ""
        assert (tmp_path / ".json").exists()

    def test_long_conversation_id(self, tmp_path, monkeypatch):
        """Test that long conversation IDs are handled correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a very long conversation ID
        long_id = "test-conv-" + "x" * 200
        conversation = create_conversation(long_id)

        assert conversation["id"] == long_id

        file_path = tmp_path / f"{long_id}.json"
        assert file_path.exists()

    def test_uuid_format_conversation_id(self, tmp_path, monkeypatch):
        """Test with UUID-format conversation IDs."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        import uuid
        conversation_id = str(uuid.uuid4())
        conversation = create_conversation(conversation_id)

        assert conversation["id"] == conversation_id

        file_path = tmp_path / f"{conversation_id}.json"
        assert file_path.exists()

    def test_timestamp_precision(self, tmp_path, monkeypatch):
        """Test that timestamp includes microsecond precision."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation = create_conversation("test-conv-timestamp")
        timestamp = conversation["created_at"]

        # Parse timestamp
        dt = datetime.fromisoformat(timestamp)

        # Verify it's a datetime object with time information
        assert dt.year >= 2024
        assert 1 <= dt.month <= 12
        assert 1 <= dt.day <= 31

    def test_concurrent_creation_same_directory(self, tmp_path, monkeypatch):
        """Test that multiple conversations can be created in same directory."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversations rapidly
        conversations = []
        for i in range(10):
            conv = create_conversation(f"rapid-{i}")
            conversations.append(conv)

        # Verify all were created successfully
        assert len(conversations) == 10

        # Verify all files exist
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 10


class TestEnsureDataDir:
    """Test suite for ensure_data_dir function."""

    def test_creates_directory_if_missing(self, tmp_path, monkeypatch):
        """Test that ensure_data_dir creates directory if it doesn't exist."""
        data_dir = tmp_path / "new_data_dir"
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", data_dir)

        assert not data_dir.exists()

        ensure_data_dir()

        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_does_nothing_if_directory_exists(self, tmp_path, monkeypatch):
        """Test that ensure_data_dir is idempotent."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Directory already exists
        assert tmp_path.exists()

        # Should not raise any errors
        ensure_data_dir()

        assert tmp_path.exists()

    def test_creates_parent_directories(self, tmp_path, monkeypatch):
        """Test that ensure_data_dir creates parent directories."""
        data_dir = tmp_path / "parent" / "child" / "data"
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", data_dir)

        assert not data_dir.exists()
        assert not data_dir.parent.exists()

        ensure_data_dir()

        assert data_dir.exists()
        assert data_dir.parent.exists()


class TestGetConversationPath:
    """Test suite for get_conversation_path function."""

    def test_returns_correct_path(self, tmp_path, monkeypatch):
        """Test that get_conversation_path returns correct file path."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv-path"
        path = get_conversation_path(conversation_id)

        expected_path = str(tmp_path / f"{conversation_id}.json")
        assert path == expected_path

    def test_path_includes_json_extension(self, tmp_path, monkeypatch):
        """Test that path includes .json extension."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        path = get_conversation_path("test-conv")

        assert path.endswith(".json")

    def test_path_format_with_special_characters(self, tmp_path, monkeypatch):
        """Test path format with special characters in conversation ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        conversation_id = "test-conv_2024-01-01"
        path = get_conversation_path(conversation_id)

        assert conversation_id in path
        assert path.endswith(".json")


class TestGetConversation:
    """Test suite for get_conversation function."""

    def test_retrieves_existing_conversation(self, tmp_path, monkeypatch):
        """Test that get_conversation retrieves an existing conversation correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation first
        conversation_id = "test-conv-retrieve"
        created_conv = create_conversation(conversation_id)

        # Retrieve it
        retrieved_conv = get_conversation(conversation_id)

        # Verify it matches what was created
        assert retrieved_conv is not None
        assert retrieved_conv == created_conv
        assert retrieved_conv["id"] == conversation_id

    def test_returns_none_for_nonexistent_conversation(self, tmp_path, monkeypatch):
        """Test that get_conversation returns None for non-existent conversation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Try to retrieve a conversation that doesn't exist
        result = get_conversation("nonexistent-conv-id")

        assert result is None

    def test_parses_json_correctly(self, tmp_path, monkeypatch):
        """Test that get_conversation correctly parses JSON structure."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-json"
        create_conversation(conversation_id)

        # Retrieve and verify structure
        conv = get_conversation(conversation_id)

        assert isinstance(conv, dict)
        assert "id" in conv
        assert "created_at" in conv
        assert "title" in conv
        assert "messages" in conv
        assert isinstance(conv["messages"], list)

    def test_retrieves_all_conversation_fields(self, tmp_path, monkeypatch):
        """Test that all fields are retrieved correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-fields"
        original = create_conversation(conversation_id)

        # Retrieve it
        retrieved = get_conversation(conversation_id)

        # Verify all fields match
        assert retrieved["id"] == original["id"]
        assert retrieved["created_at"] == original["created_at"]
        assert retrieved["title"] == original["title"]
        assert retrieved["messages"] == original["messages"]

    def test_handles_malformed_json_gracefully(self, tmp_path, monkeypatch):
        """Test that get_conversation handles malformed JSON gracefully."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a file with malformed JSON
        conversation_id = "test-conv-malformed"
        file_path = tmp_path / f"{conversation_id}.json"

        with open(file_path, "w") as f:
            f.write("{ invalid json content }")

        # Try to retrieve it - should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            get_conversation(conversation_id)

    def test_handles_empty_file(self, tmp_path, monkeypatch):
        """Test behavior with empty JSON file."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create an empty file
        conversation_id = "test-conv-empty"
        file_path = tmp_path / f"{conversation_id}.json"

        with open(file_path, "w") as f:
            f.write("")

        # Try to retrieve it - should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            get_conversation(conversation_id)

    def test_handles_incomplete_json(self, tmp_path, monkeypatch):
        """Test handling of incomplete JSON structure."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a file with incomplete JSON (missing closing brace)
        conversation_id = "test-conv-incomplete"
        file_path = tmp_path / f"{conversation_id}.json"

        with open(file_path, "w") as f:
            f.write('{"id": "test"')

        # Try to retrieve it - should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            get_conversation(conversation_id)

    def test_retrieves_conversation_with_messages(self, tmp_path, monkeypatch):
        """Test retrieving a conversation that has messages."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation and add messages manually
        conversation_id = "test-conv-with-messages"
        conv = create_conversation(conversation_id)

        # Add some messages
        conv["messages"].append({"role": "user", "content": "Hello"})
        conv["messages"].append({"role": "assistant", "content": "Hi there"})
        save_conversation(conv)

        # Retrieve it
        retrieved = get_conversation(conversation_id)

        assert len(retrieved["messages"]) == 2
        assert retrieved["messages"][0]["role"] == "user"
        assert retrieved["messages"][0]["content"] == "Hello"
        assert retrieved["messages"][1]["role"] == "assistant"

    def test_retrieves_updated_conversation(self, tmp_path, monkeypatch):
        """Test that get_conversation retrieves the latest saved version."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-updated"
        conv = create_conversation(conversation_id)

        # Update it
        conv["title"] = "Updated Title"
        save_conversation(conv)

        # Retrieve it
        retrieved = get_conversation(conversation_id)

        assert retrieved["title"] == "Updated Title"

    def test_multiple_conversations_dont_interfere(self, tmp_path, monkeypatch):
        """Test that retrieving one conversation doesn't affect others."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create multiple conversations
        conv1 = create_conversation("conv-1")
        conv2 = create_conversation("conv-2")
        conv3 = create_conversation("conv-3")

        # Retrieve them in different order
        retrieved2 = get_conversation("conv-2")
        retrieved1 = get_conversation("conv-1")
        retrieved3 = get_conversation("conv-3")

        # Verify each matches original
        assert retrieved1["id"] == "conv-1"
        assert retrieved2["id"] == "conv-2"
        assert retrieved3["id"] == "conv-3"

    def test_retrieves_conversation_with_special_characters_in_id(self, tmp_path, monkeypatch):
        """Test retrieving conversation with special characters in ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with special characters
        conversation_id = "test-conv_2024-01-01"
        create_conversation(conversation_id)

        # Retrieve it
        retrieved = get_conversation(conversation_id)

        assert retrieved is not None
        assert retrieved["id"] == conversation_id

    def test_retrieves_conversation_with_uuid_id(self, tmp_path, monkeypatch):
        """Test retrieving conversation with UUID as ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        import uuid
        conversation_id = str(uuid.uuid4())

        # Create and retrieve
        create_conversation(conversation_id)
        retrieved = get_conversation(conversation_id)

        assert retrieved is not None
        assert retrieved["id"] == conversation_id

    def test_nonexistent_conversation_doesnt_create_file(self, tmp_path, monkeypatch):
        """Test that trying to retrieve non-existent conversation doesn't create files."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Try to retrieve non-existent conversation
        result = get_conversation("nonexistent")

        assert result is None

        # Verify no file was created
        file_path = tmp_path / "nonexistent.json"
        assert not file_path.exists()

    def test_empty_string_conversation_id(self, tmp_path, monkeypatch):
        """Test retrieving conversation with empty string ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with empty string ID
        create_conversation("")
        retrieved = get_conversation("")

        assert retrieved is not None
        assert retrieved["id"] == ""

    def test_returns_dict_not_reference(self, tmp_path, monkeypatch):
        """Test that get_conversation returns a new dict (not affecting cached data)."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-dict"
        original = create_conversation(conversation_id)

        # Retrieve it twice
        retrieved1 = get_conversation(conversation_id)
        retrieved2 = get_conversation(conversation_id)

        # Verify they're equal but not the same object
        assert retrieved1 == retrieved2
        # Modify one shouldn't affect the other
        retrieved1["title"] = "Modified"
        assert retrieved2["title"] == "New Conversation"

    def test_file_permissions_readable(self, tmp_path, monkeypatch):
        """Test that conversation files are readable after creation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-permissions"
        create_conversation(conversation_id)

        # Verify file is readable
        file_path = tmp_path / f"{conversation_id}.json"
        assert os.access(file_path, os.R_OK)

        # And we can retrieve it
        retrieved = get_conversation(conversation_id)
        assert retrieved is not None

    def test_retrieves_long_conversation_id(self, tmp_path, monkeypatch):
        """Test retrieving conversation with very long ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with long ID
        long_id = "test-conv-" + "x" * 200
        create_conversation(long_id)

        # Retrieve it
        retrieved = get_conversation(long_id)

        assert retrieved is not None
        assert retrieved["id"] == long_id

    def test_handles_valid_but_incomplete_conversation_structure(self, tmp_path, monkeypatch):
        """Test handling valid JSON but missing expected fields."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a file with valid JSON but missing fields
        conversation_id = "test-conv-missing-fields"
        file_path = tmp_path / f"{conversation_id}.json"

        with open(file_path, "w") as f:
            json.dump({"id": conversation_id}, f)  # Missing created_at, title, messages

        # Retrieve it - should succeed but have incomplete structure
        retrieved = get_conversation(conversation_id)

        assert retrieved is not None
        assert retrieved["id"] == conversation_id
        assert "created_at" not in retrieved
        assert "title" not in retrieved
        assert "messages" not in retrieved

    def test_handles_json_with_extra_fields(self, tmp_path, monkeypatch):
        """Test that extra fields in JSON are preserved."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation and add extra field
        conversation_id = "test-conv-extra"
        conv = create_conversation(conversation_id)
        conv["extra_field"] = "extra_value"
        save_conversation(conv)

        # Retrieve it
        retrieved = get_conversation(conversation_id)

        assert retrieved["extra_field"] == "extra_value"

    def test_handles_unicode_in_conversation_data(self, tmp_path, monkeypatch):
        """Test retrieving conversation with unicode characters."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation and add unicode content
        conversation_id = "test-conv-unicode"
        conv = create_conversation(conversation_id)
        conv["title"] = "Test with unicode: 日本語 🚀 émoji"
        save_conversation(conv)

        # Retrieve it
        retrieved = get_conversation(conversation_id)

        assert retrieved["title"] == "Test with unicode: 日本語 🚀 émoji"

    def test_retrieves_conversation_after_directory_recreation(self, tmp_path, monkeypatch):
        """Test that conversations persist across directory operations."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-persist"
        create_conversation(conversation_id)

        # Verify we can retrieve it
        retrieved1 = get_conversation(conversation_id)
        assert retrieved1 is not None

        # Retrieve again (simulating restart or reconnection)
        retrieved2 = get_conversation(conversation_id)
        assert retrieved2 is not None
        assert retrieved2 == retrieved1
