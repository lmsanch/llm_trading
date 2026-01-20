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


class TestSaveConversation:
    """Test suite for save_conversation function."""

    def test_persists_changes_to_conversation(self, tmp_path, monkeypatch):
        """Test that save_conversation persists changes to file."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-save"
        conv = create_conversation(conversation_id)

        # Modify the conversation
        conv["title"] = "Updated Title"
        conv["messages"].append({"role": "user", "content": "Test message"})

        # Save it
        save_conversation(conv)

        # Retrieve it to verify changes were saved
        retrieved = get_conversation(conversation_id)

        assert retrieved["title"] == "Updated Title"
        assert len(retrieved["messages"]) == 1
        assert retrieved["messages"][0]["content"] == "Test message"

    def test_saves_to_correct_file_path(self, tmp_path, monkeypatch):
        """Test that save_conversation saves to correct file path."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-path"
        conv = create_conversation(conversation_id)
        conv["title"] = "Modified"

        # Save it
        save_conversation(conv)

        # Verify file exists at correct path
        file_path = tmp_path / f"{conversation_id}.json"
        assert file_path.exists()

        # Verify file contains updated data
        with open(file_path, "r") as f:
            data = json.load(f)

        assert data["title"] == "Modified"

    def test_overwrites_existing_file(self, tmp_path, monkeypatch):
        """Test that save_conversation overwrites existing file."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-overwrite"
        conv = create_conversation(conversation_id)

        # Modify and save multiple times
        conv["title"] = "Title 1"
        save_conversation(conv)

        conv["title"] = "Title 2"
        save_conversation(conv)

        conv["title"] = "Title 3"
        save_conversation(conv)

        # Retrieve to verify only the last save persists
        retrieved = get_conversation(conversation_id)
        assert retrieved["title"] == "Title 3"

    def test_saves_with_proper_json_formatting(self, tmp_path, monkeypatch):
        """Test that saved JSON is properly formatted."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create and save a conversation
        conversation_id = "test-conv-format"
        conv = create_conversation(conversation_id)
        conv["title"] = "Formatted"
        save_conversation(conv)

        # Read raw file content
        file_path = tmp_path / f"{conversation_id}.json"
        with open(file_path, "r") as f:
            content = f.read()

        # Verify proper formatting (indented)
        assert "\n" in content
        assert "  " in content  # 2-space indentation

    def test_saves_all_conversation_fields(self, tmp_path, monkeypatch):
        """Test that all conversation fields are saved."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation with all fields
        conversation_id = "test-conv-fields"
        conv = create_conversation(conversation_id)
        conv["title"] = "Test Title"
        conv["messages"] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "stage1": [], "stage2": [], "stage3": {}},
        ]

        # Save it
        save_conversation(conv)

        # Retrieve and verify all fields
        retrieved = get_conversation(conversation_id)

        assert retrieved["id"] == conversation_id
        assert retrieved["title"] == "Test Title"
        assert "created_at" in retrieved
        assert len(retrieved["messages"]) == 2

    def test_saves_messages_array_correctly(self, tmp_path, monkeypatch):
        """Test that messages array is saved correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with multiple messages
        conversation_id = "test-conv-messages"
        conv = create_conversation(conversation_id)

        # Add multiple messages
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "stage1": [], "stage2": [], "stage3": {}},
            {"role": "user", "content": "Message 2"},
        ]
        conv["messages"] = messages

        save_conversation(conv)

        # Retrieve and verify messages
        retrieved = get_conversation(conversation_id)
        assert len(retrieved["messages"]) == 3
        assert retrieved["messages"][0]["content"] == "Message 1"
        assert retrieved["messages"][2]["content"] == "Message 2"

    def test_saves_unicode_content(self, tmp_path, monkeypatch):
        """Test that unicode content is saved correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with unicode
        conversation_id = "test-conv-unicode"
        conv = create_conversation(conversation_id)
        conv["title"] = "Unicode test: 日本語 🚀 émoji"

        save_conversation(conv)

        # Retrieve and verify unicode preserved
        retrieved = get_conversation(conversation_id)
        assert retrieved["title"] == "Unicode test: 日本語 🚀 émoji"

    def test_creates_data_directory_if_missing(self, tmp_path, monkeypatch):
        """Test that save_conversation creates data directory if missing."""
        # Create a subdirectory that doesn't exist
        data_dir = tmp_path / "new_dir"
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", data_dir)

        # Create conversation (which saves it)
        conv = create_conversation("test-conv")

        # Manually delete the directory
        import shutil
        shutil.rmtree(data_dir)

        assert not data_dir.exists()

        # Modify and save should recreate directory
        conv["title"] = "After dir deletion"
        save_conversation(conv)

        assert data_dir.exists()
        assert (data_dir / "test-conv.json").exists()

    def test_save_with_extra_fields(self, tmp_path, monkeypatch):
        """Test that extra fields are saved correctly."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation and add extra fields
        conversation_id = "test-conv-extra"
        conv = create_conversation(conversation_id)
        conv["extra_field"] = "extra_value"
        conv["metadata"] = {"key": "value"}

        save_conversation(conv)

        # Retrieve and verify extra fields
        retrieved = get_conversation(conversation_id)
        assert retrieved["extra_field"] == "extra_value"
        assert retrieved["metadata"]["key"] == "value"

    def test_save_preserves_created_at(self, tmp_path, monkeypatch):
        """Test that save_conversation preserves original created_at timestamp."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-timestamp"
        conv = create_conversation(conversation_id)
        original_timestamp = conv["created_at"]

        # Wait and save again
        import time
        time.sleep(0.01)

        conv["title"] = "Modified"
        save_conversation(conv)

        # Verify timestamp unchanged
        retrieved = get_conversation(conversation_id)
        assert retrieved["created_at"] == original_timestamp

    def test_save_empty_messages_array(self, tmp_path, monkeypatch):
        """Test saving conversation with empty messages array."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with empty messages
        conversation_id = "test-conv-empty-messages"
        conv = create_conversation(conversation_id)

        save_conversation(conv)

        # Verify empty messages array preserved
        retrieved = get_conversation(conversation_id)
        assert retrieved["messages"] == []

    def test_save_multiple_conversations_independently(self, tmp_path, monkeypatch):
        """Test that saving one conversation doesn't affect others."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create multiple conversations
        conv1 = create_conversation("conv-1")
        conv2 = create_conversation("conv-2")
        conv3 = create_conversation("conv-3")

        # Modify and save one
        conv2["title"] = "Modified"
        save_conversation(conv2)

        # Verify others unchanged
        retrieved1 = get_conversation("conv-1")
        retrieved3 = get_conversation("conv-3")

        assert retrieved1["title"] == "New Conversation"
        assert retrieved3["title"] == "New Conversation"

        # Verify modified one changed
        retrieved2 = get_conversation("conv-2")
        assert retrieved2["title"] == "Modified"


class TestAddUserMessage:
    """Test suite for add_user_message function."""

    def test_appends_message_to_array(self, tmp_path, monkeypatch):
        """Test that add_user_message appends to messages array."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-user-msg"
        create_conversation(conversation_id)

        # Add a user message
        add_user_message(conversation_id, "Hello, assistant!")

        # Verify message was added
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello, assistant!"

    def test_adds_multiple_messages_sequentially(self, tmp_path, monkeypatch):
        """Test adding multiple user messages in sequence."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-multiple-user"
        create_conversation(conversation_id)

        # Add multiple messages
        add_user_message(conversation_id, "First message")
        add_user_message(conversation_id, "Second message")
        add_user_message(conversation_id, "Third message")

        # Verify all messages added in order
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 3
        assert conv["messages"][0]["content"] == "First message"
        assert conv["messages"][1]["content"] == "Second message"
        assert conv["messages"][2]["content"] == "Third message"

    def test_message_has_correct_structure(self, tmp_path, monkeypatch):
        """Test that user message has correct structure."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-structure"
        create_conversation(conversation_id)

        # Add a user message
        add_user_message(conversation_id, "Test content")

        # Verify message structure
        conv = get_conversation(conversation_id)
        message = conv["messages"][0]

        assert "role" in message
        assert "content" in message
        assert message["role"] == "user"
        assert message["content"] == "Test content"

    def test_persists_to_file(self, tmp_path, monkeypatch):
        """Test that add_user_message persists changes to file."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-persist"
        create_conversation(conversation_id)

        # Add a user message
        add_user_message(conversation_id, "Persisted message")

        # Read directly from file to verify persistence
        file_path = tmp_path / f"{conversation_id}.json"
        with open(file_path, "r") as f:
            data = json.load(f)

        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Persisted message"

    def test_raises_error_for_nonexistent_conversation(self, tmp_path, monkeypatch):
        """Test that add_user_message raises error for non-existent conversation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Try to add message to non-existent conversation
        with pytest.raises(ValueError, match="Conversation nonexistent not found"):
            add_user_message("nonexistent", "This should fail")

    def test_handles_empty_content(self, tmp_path, monkeypatch):
        """Test adding user message with empty content."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-empty"
        create_conversation(conversation_id)

        # Add message with empty content
        add_user_message(conversation_id, "")

        # Verify message added with empty content
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["content"] == ""

    def test_handles_long_content(self, tmp_path, monkeypatch):
        """Test adding user message with very long content."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-long"
        create_conversation(conversation_id)

        # Add message with long content
        long_content = "x" * 10000
        add_user_message(conversation_id, long_content)

        # Verify message added correctly
        conv = get_conversation(conversation_id)
        assert conv["messages"][0]["content"] == long_content

    def test_handles_unicode_content(self, tmp_path, monkeypatch):
        """Test adding user message with unicode content."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-unicode"
        create_conversation(conversation_id)

        # Add message with unicode
        unicode_content = "Hello 日本語 🚀 émoji"
        add_user_message(conversation_id, unicode_content)

        # Verify unicode preserved
        conv = get_conversation(conversation_id)
        assert conv["messages"][0]["content"] == unicode_content

    def test_handles_special_characters(self, tmp_path, monkeypatch):
        """Test adding user message with special characters."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-special"
        create_conversation(conversation_id)

        # Add message with special characters
        special_content = 'Message with "quotes", \\backslashes\\, and\nnewlines'
        add_user_message(conversation_id, special_content)

        # Verify special characters preserved
        conv = get_conversation(conversation_id)
        assert conv["messages"][0]["content"] == special_content

    def test_preserves_existing_messages(self, tmp_path, monkeypatch):
        """Test that add_user_message preserves existing messages."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation with existing messages
        conversation_id = "test-conv-preserve"
        conv = create_conversation(conversation_id)
        conv["messages"].append({"role": "user", "content": "Existing message"})
        save_conversation(conv)

        # Add new message
        add_user_message(conversation_id, "New message")

        # Verify both messages present
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 2
        assert conv["messages"][0]["content"] == "Existing message"
        assert conv["messages"][1]["content"] == "New message"

    def test_preserves_other_conversation_fields(self, tmp_path, monkeypatch):
        """Test that add_user_message doesn't modify other fields."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-fields"
        conv = create_conversation(conversation_id)
        original_title = conv["title"]
        original_created_at = conv["created_at"]

        # Add user message
        add_user_message(conversation_id, "Test message")

        # Verify other fields unchanged
        conv = get_conversation(conversation_id)
        assert conv["title"] == original_title
        assert conv["created_at"] == original_created_at

    def test_works_with_conversation_id_special_chars(self, tmp_path, monkeypatch):
        """Test add_user_message with special characters in conversation ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with special chars in ID
        conversation_id = "test-conv_2024-01-01"
        create_conversation(conversation_id)

        # Add user message
        add_user_message(conversation_id, "Test message")

        # Verify message added
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 1


class TestAddAssistantMessage:
    """Test suite for add_assistant_message function."""

    def test_adds_assistant_message_with_all_stages(self, tmp_path, monkeypatch):
        """Test that add_assistant_message stores all 3 stages."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-assistant"
        create_conversation(conversation_id)

        # Add assistant message with all stages
        stage1 = [{"model": "gpt-4", "content": "Response 1"}]
        stage2 = [{"model": "gpt-4", "ranking": "A > B > C"}]
        stage3 = {"model": "gpt-4", "synthesis": "Final answer"}

        add_assistant_message(conversation_id, stage1, stage2, stage3)

        # Verify message structure
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 1

        message = conv["messages"][0]
        assert message["role"] == "assistant"
        assert "stage1" in message
        assert "stage2" in message
        assert "stage3" in message
        assert message["stage1"] == stage1
        assert message["stage2"] == stage2
        assert message["stage3"] == stage3

    def test_appends_to_existing_messages(self, tmp_path, monkeypatch):
        """Test that assistant message is appended to messages array."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with existing message
        conversation_id = "test-conv-append"
        conv = create_conversation(conversation_id)
        conv["messages"].append({"role": "user", "content": "User message"})
        save_conversation(conv)

        # Add assistant message
        stage1 = [{"model": "gpt-4", "content": "Response"}]
        stage2 = []
        stage3 = {}

        add_assistant_message(conversation_id, stage1, stage2, stage3)

        # Verify message appended
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 2
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][1]["role"] == "assistant"

    def test_persists_to_file(self, tmp_path, monkeypatch):
        """Test that add_assistant_message persists to file."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-persist"
        create_conversation(conversation_id)

        # Add assistant message
        stage1 = [{"model": "gpt-4", "content": "Test"}]
        stage2 = []
        stage3 = {}

        add_assistant_message(conversation_id, stage1, stage2, stage3)

        # Read directly from file
        file_path = tmp_path / f"{conversation_id}.json"
        with open(file_path, "r") as f:
            data = json.load(f)

        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "assistant"

    def test_raises_error_for_nonexistent_conversation(self, tmp_path, monkeypatch):
        """Test that add_assistant_message raises error for non-existent conversation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Try to add message to non-existent conversation
        with pytest.raises(ValueError, match="Conversation nonexistent not found"):
            add_assistant_message("nonexistent", [], [], {})

    def test_handles_empty_stages(self, tmp_path, monkeypatch):
        """Test adding assistant message with empty stages."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-empty-stages"
        create_conversation(conversation_id)

        # Add message with empty stages
        add_assistant_message(conversation_id, [], [], {})

        # Verify message added with empty stages
        conv = get_conversation(conversation_id)
        message = conv["messages"][0]

        assert message["stage1"] == []
        assert message["stage2"] == []
        assert message["stage3"] == {}

    def test_handles_complex_stage_data(self, tmp_path, monkeypatch):
        """Test adding assistant message with complex stage data."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-complex"
        create_conversation(conversation_id)

        # Add message with complex stages
        stage1 = [
            {"model": "gpt-4", "content": "Response 1", "metadata": {"key": "value"}},
            {"model": "claude", "content": "Response 2"},
        ]
        stage2 = [
            {"model": "gpt-4", "ranking": "A > B", "scores": [1, 2, 3]},
        ]
        stage3 = {
            "model": "gpt-4",
            "synthesis": "Final answer",
            "aggregate_rankings": {"A": 1.5, "B": 2.0},
        }

        add_assistant_message(conversation_id, stage1, stage2, stage3)

        # Verify complex data preserved
        conv = get_conversation(conversation_id)
        message = conv["messages"][0]

        assert len(message["stage1"]) == 2
        assert message["stage1"][0]["metadata"]["key"] == "value"
        assert message["stage2"][0]["scores"] == [1, 2, 3]
        assert message["stage3"]["aggregate_rankings"]["A"] == 1.5

    def test_handles_unicode_in_stages(self, tmp_path, monkeypatch):
        """Test adding assistant message with unicode in stage data."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-unicode"
        create_conversation(conversation_id)

        # Add message with unicode
        stage1 = [{"model": "gpt-4", "content": "Response with 日本語 🚀"}]
        stage2 = []
        stage3 = {"synthesis": "émoji test"}

        add_assistant_message(conversation_id, stage1, stage2, stage3)

        # Verify unicode preserved
        conv = get_conversation(conversation_id)
        message = conv["messages"][0]

        assert message["stage1"][0]["content"] == "Response with 日本語 🚀"
        assert message["stage3"]["synthesis"] == "émoji test"

    def test_multiple_assistant_messages(self, tmp_path, monkeypatch):
        """Test adding multiple assistant messages in sequence."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-multiple"
        create_conversation(conversation_id)

        # Add multiple assistant messages
        add_assistant_message(
            conversation_id,
            [{"content": "First"}],
            [],
            {"synthesis": "First synthesis"},
        )
        add_assistant_message(
            conversation_id,
            [{"content": "Second"}],
            [],
            {"synthesis": "Second synthesis"},
        )

        # Verify both messages added
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 2
        assert conv["messages"][0]["stage1"][0]["content"] == "First"
        assert conv["messages"][1]["stage1"][0]["content"] == "Second"

    def test_preserves_other_conversation_fields(self, tmp_path, monkeypatch):
        """Test that add_assistant_message doesn't modify other fields."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-fields"
        conv = create_conversation(conversation_id)
        original_title = conv["title"]
        original_created_at = conv["created_at"]

        # Add assistant message
        add_assistant_message(conversation_id, [], [], {})

        # Verify other fields unchanged
        conv = get_conversation(conversation_id)
        assert conv["title"] == original_title
        assert conv["created_at"] == original_created_at

    def test_message_structure_has_only_expected_fields(self, tmp_path, monkeypatch):
        """Test that assistant message has only role, stage1, stage2, stage3 fields."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-fields-only"
        create_conversation(conversation_id)

        # Add assistant message
        add_assistant_message(conversation_id, [], [], {})

        # Verify message structure
        conv = get_conversation(conversation_id)
        message = conv["messages"][0]

        expected_fields = {"role", "stage1", "stage2", "stage3"}
        assert set(message.keys()) == expected_fields


class TestUpdateConversationTitle:
    """Test suite for update_conversation_title function."""

    def test_updates_title(self, tmp_path, monkeypatch):
        """Test that update_conversation_title changes the title."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-title"
        create_conversation(conversation_id)

        # Update title
        new_title = "Updated Title"
        update_conversation_title(conversation_id, new_title)

        # Verify title updated
        conv = get_conversation(conversation_id)
        assert conv["title"] == new_title

    def test_persists_to_file(self, tmp_path, monkeypatch):
        """Test that title update persists to file."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-persist"
        create_conversation(conversation_id)

        # Update title
        update_conversation_title(conversation_id, "Persisted Title")

        # Read directly from file
        file_path = tmp_path / f"{conversation_id}.json"
        with open(file_path, "r") as f:
            data = json.load(f)

        assert data["title"] == "Persisted Title"

    def test_raises_error_for_nonexistent_conversation(self, tmp_path, monkeypatch):
        """Test that update_conversation_title raises error for non-existent conversation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Try to update title for non-existent conversation
        with pytest.raises(ValueError, match="Conversation nonexistent not found"):
            update_conversation_title("nonexistent", "New Title")

    def test_replaces_previous_title(self, tmp_path, monkeypatch):
        """Test that update replaces previous title completely."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-replace"
        create_conversation(conversation_id)

        # Update title multiple times
        update_conversation_title(conversation_id, "Title 1")
        update_conversation_title(conversation_id, "Title 2")
        update_conversation_title(conversation_id, "Final Title")

        # Verify only the last title persists
        conv = get_conversation(conversation_id)
        assert conv["title"] == "Final Title"

    def test_handles_empty_title(self, tmp_path, monkeypatch):
        """Test updating title to empty string."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-empty"
        create_conversation(conversation_id)

        # Update to empty title
        update_conversation_title(conversation_id, "")

        # Verify empty title set
        conv = get_conversation(conversation_id)
        assert conv["title"] == ""

    def test_handles_long_title(self, tmp_path, monkeypatch):
        """Test updating title to very long string."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-long"
        create_conversation(conversation_id)

        # Update to long title
        long_title = "x" * 1000
        update_conversation_title(conversation_id, long_title)

        # Verify long title set
        conv = get_conversation(conversation_id)
        assert conv["title"] == long_title

    def test_handles_unicode_title(self, tmp_path, monkeypatch):
        """Test updating title with unicode characters."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-unicode"
        create_conversation(conversation_id)

        # Update to unicode title
        unicode_title = "Title with 日本語 🚀 émoji"
        update_conversation_title(conversation_id, unicode_title)

        # Verify unicode title preserved
        conv = get_conversation(conversation_id)
        assert conv["title"] == unicode_title

    def test_handles_special_characters_in_title(self, tmp_path, monkeypatch):
        """Test updating title with special characters."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation
        conversation_id = "test-conv-special"
        create_conversation(conversation_id)

        # Update to title with special chars
        special_title = 'Title with "quotes", \\backslashes\\, and\nnewlines'
        update_conversation_title(conversation_id, special_title)

        # Verify special characters preserved
        conv = get_conversation(conversation_id)
        assert conv["title"] == special_title

    def test_preserves_other_conversation_fields(self, tmp_path, monkeypatch):
        """Test that update_conversation_title doesn't modify other fields."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with messages
        conversation_id = "test-conv-preserve"
        conv = create_conversation(conversation_id)
        original_id = conv["id"]
        original_created_at = conv["created_at"]
        conv["messages"].append({"role": "user", "content": "Test"})
        save_conversation(conv)

        # Update title
        update_conversation_title(conversation_id, "New Title")

        # Verify other fields unchanged
        conv = get_conversation(conversation_id)
        assert conv["id"] == original_id
        assert conv["created_at"] == original_created_at
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["content"] == "Test"

    def test_preserves_messages_array(self, tmp_path, monkeypatch):
        """Test that title update preserves messages array."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with multiple messages
        conversation_id = "test-conv-messages"
        conv = create_conversation(conversation_id)
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "stage1": [], "stage2": [], "stage3": {}},
            {"role": "user", "content": "Message 2"},
        ]
        conv["messages"] = messages
        save_conversation(conv)

        # Update title
        update_conversation_title(conversation_id, "New Title")

        # Verify messages unchanged
        conv = get_conversation(conversation_id)
        assert len(conv["messages"]) == 3
        assert conv["messages"][0]["content"] == "Message 1"
        assert conv["messages"][2]["content"] == "Message 2"

    def test_works_with_conversation_id_special_chars(self, tmp_path, monkeypatch):
        """Test update_conversation_title with special characters in conversation ID."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with special chars in ID
        conversation_id = "test-conv_2024-01-01"
        create_conversation(conversation_id)

        # Update title
        update_conversation_title(conversation_id, "Updated Title")

        # Verify title updated
        conv = get_conversation(conversation_id)
        assert conv["title"] == "Updated Title"


class TestListConversations:
    """Test suite for list_conversations function."""

    def test_returns_all_conversations(self, tmp_path, monkeypatch):
        """Test that list_conversations returns all conversations."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create multiple conversations
        create_conversation("conv-1")
        create_conversation("conv-2")
        create_conversation("conv-3")

        # List conversations
        conversations = list_conversations()

        # Verify all conversations returned
        assert len(conversations) == 3
        conv_ids = {conv["id"] for conv in conversations}
        assert conv_ids == {"conv-1", "conv-2", "conv-3"}

    def test_includes_only_metadata_fields(self, tmp_path, monkeypatch):
        """Test that list_conversations includes only metadata (id, created_at, title, message_count)."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conversation_id = "test-conv-metadata"
        create_conversation(conversation_id)

        # List conversations
        conversations = list_conversations()

        # Verify metadata fields
        assert len(conversations) == 1
        conv = conversations[0]

        # Should have exactly these 4 fields
        expected_fields = {"id", "created_at", "title", "message_count"}
        assert set(conv.keys()) == expected_fields

        # Should NOT have messages field
        assert "messages" not in conv

    def test_message_count_field(self, tmp_path, monkeypatch):
        """Test that message_count field is correct."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with no messages
        conversation_id = "test-conv-count"
        create_conversation(conversation_id)

        # List conversations
        conversations = list_conversations()
        assert conversations[0]["message_count"] == 0

        # Add messages
        add_user_message(conversation_id, "Message 1")
        add_user_message(conversation_id, "Message 2")
        add_assistant_message(conversation_id, [], [], {})

        # List again
        conversations = list_conversations()
        assert conversations[0]["message_count"] == 3

    def test_sorted_by_created_at_descending(self, tmp_path, monkeypatch):
        """Test that conversations are sorted by created_at descending (newest first)."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        import time

        # Create conversations with small delays to ensure different timestamps
        conv1 = create_conversation("conv-1")
        time.sleep(0.01)
        conv2 = create_conversation("conv-2")
        time.sleep(0.01)
        conv3 = create_conversation("conv-3")

        # List conversations
        conversations = list_conversations()

        # Verify sorted by created_at descending (newest first)
        assert len(conversations) == 3
        assert conversations[0]["id"] == "conv-3"  # Most recent
        assert conversations[1]["id"] == "conv-2"
        assert conversations[2]["id"] == "conv-1"  # Oldest

        # Verify timestamps are in descending order
        assert conversations[0]["created_at"] >= conversations[1]["created_at"]
        assert conversations[1]["created_at"] >= conversations[2]["created_at"]

    def test_handles_empty_storage_directory(self, tmp_path, monkeypatch):
        """Test that list_conversations handles empty storage directory."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # List conversations in empty directory
        conversations = list_conversations()

        # Should return empty list
        assert conversations == []
        assert isinstance(conversations, list)

    def test_includes_conversation_title(self, tmp_path, monkeypatch):
        """Test that list_conversations includes conversation titles."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with default title
        create_conversation("conv-1")

        # Create conversation with custom title
        conversation_id = "conv-2"
        create_conversation(conversation_id)
        update_conversation_title(conversation_id, "Custom Title")

        # List conversations
        conversations = list_conversations()

        # Find each conversation
        conv1 = next(c for c in conversations if c["id"] == "conv-1")
        conv2 = next(c for c in conversations if c["id"] == "conv-2")

        # Verify titles
        assert conv1["title"] == "New Conversation"
        assert conv2["title"] == "Custom Title"

    def test_includes_created_at_timestamp(self, tmp_path, monkeypatch):
        """Test that list_conversations includes created_at timestamps."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        conv = create_conversation("test-conv")

        # List conversations
        conversations = list_conversations()

        # Verify timestamp present and matches
        assert len(conversations) == 1
        assert "created_at" in conversations[0]
        assert conversations[0]["created_at"] == conv["created_at"]

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(conversations[0]["created_at"])
        except ValueError:
            pytest.fail("created_at is not a valid ISO format timestamp")

    def test_ignores_non_json_files(self, tmp_path, monkeypatch):
        """Test that list_conversations ignores non-JSON files."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        create_conversation("conv-1")

        # Create non-JSON files in the directory
        (tmp_path / "readme.txt").write_text("This is not a conversation")
        (tmp_path / "data.csv").write_text("id,title\n1,Test")
        (tmp_path / ".hidden").write_text("hidden file")

        # List conversations
        conversations = list_conversations()

        # Should only return the one JSON conversation
        assert len(conversations) == 1
        assert conversations[0]["id"] == "conv-1"

    def test_handles_conversations_with_messages(self, tmp_path, monkeypatch):
        """Test that list_conversations correctly counts messages."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with multiple messages
        conversation_id = "conv-with-messages"
        create_conversation(conversation_id)

        add_user_message(conversation_id, "First message")
        add_assistant_message(conversation_id, [], [], {})
        add_user_message(conversation_id, "Second message")
        add_assistant_message(conversation_id, [], [], {})
        add_user_message(conversation_id, "Third message")

        # List conversations
        conversations = list_conversations()

        # Verify message count
        assert len(conversations) == 1
        assert conversations[0]["message_count"] == 5

    def test_multiple_conversations_with_different_counts(self, tmp_path, monkeypatch):
        """Test multiple conversations with different message counts."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversations with different message counts
        create_conversation("conv-empty")

        conversation_id_1 = "conv-one-msg"
        create_conversation(conversation_id_1)
        add_user_message(conversation_id_1, "Message")

        conversation_id_3 = "conv-three-msgs"
        create_conversation(conversation_id_3)
        add_user_message(conversation_id_3, "Message 1")
        add_user_message(conversation_id_3, "Message 2")
        add_user_message(conversation_id_3, "Message 3")

        # List conversations
        conversations = list_conversations()

        # Find each conversation
        conv_empty = next(c for c in conversations if c["id"] == "conv-empty")
        conv_one = next(c for c in conversations if c["id"] == "conv-one-msg")
        conv_three = next(c for c in conversations if c["id"] == "conv-three-msgs")

        # Verify message counts
        assert conv_empty["message_count"] == 0
        assert conv_one["message_count"] == 1
        assert conv_three["message_count"] == 3

    def test_returns_new_list_each_time(self, tmp_path, monkeypatch):
        """Test that list_conversations returns a new list each time."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create a conversation
        create_conversation("conv-1")

        # List conversations twice
        list1 = list_conversations()
        list2 = list_conversations()

        # Should be equal but not the same object
        assert list1 == list2
        assert list1 is not list2

        # Modifying one shouldn't affect the other
        list1.append({"id": "fake", "created_at": "2024-01-01", "title": "Fake", "message_count": 0})
        assert len(list1) == 2
        assert len(list2) == 1

    def test_handles_missing_title_field(self, tmp_path, monkeypatch):
        """Test that list_conversations handles missing title field gracefully."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation and manually remove title
        conversation_id = "conv-no-title"
        conv = create_conversation(conversation_id)

        # Manually edit file to remove title
        path = tmp_path / f"{conversation_id}.json"
        del conv["title"]
        with open(path, "w") as f:
            json.dump(conv, f, indent=2)

        # List conversations
        conversations = list_conversations()

        # Should use default title
        assert len(conversations) == 1
        assert conversations[0]["title"] == "New Conversation"

    def test_sorting_with_same_timestamp(self, tmp_path, monkeypatch):
        """Test sorting behavior when conversations have same timestamp."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversations
        conv1 = create_conversation("conv-1")
        conv2 = create_conversation("conv-2")

        # Manually set same timestamp
        same_timestamp = "2024-01-01T12:00:00.000000"
        conv1["created_at"] = same_timestamp
        conv2["created_at"] = same_timestamp
        save_conversation(conv1)
        save_conversation(conv2)

        # List conversations
        conversations = list_conversations()

        # Both should be returned (order may vary but both present)
        assert len(conversations) == 2
        conv_ids = {conv["id"] for conv in conversations}
        assert conv_ids == {"conv-1", "conv-2"}

        # Both should have same timestamp
        assert conversations[0]["created_at"] == same_timestamp
        assert conversations[1]["created_at"] == same_timestamp

    def test_handles_unicode_in_title(self, tmp_path, monkeypatch):
        """Test that list_conversations handles unicode in titles."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with unicode title
        conversation_id = "conv-unicode"
        create_conversation(conversation_id)
        update_conversation_title(conversation_id, "Unicode test: 日本語 🚀 émoji")

        # List conversations
        conversations = list_conversations()

        # Verify unicode preserved
        assert len(conversations) == 1
        assert conversations[0]["title"] == "Unicode test: 日本語 🚀 émoji"

    def test_returns_empty_list_not_none(self, tmp_path, monkeypatch):
        """Test that list_conversations returns empty list, not None."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # List conversations in empty directory
        conversations = list_conversations()

        # Should be empty list, not None
        assert conversations is not None
        assert conversations == []
        assert isinstance(conversations, list)

    def test_creates_data_directory_if_missing(self, tmp_path, monkeypatch):
        """Test that list_conversations creates data directory if missing."""
        # Use a subdirectory that doesn't exist
        data_dir = tmp_path / "new_data_dir"
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", data_dir)

        # Directory shouldn't exist yet
        assert not data_dir.exists()

        # List conversations should create it
        conversations = list_conversations()

        # Directory should now exist
        assert data_dir.exists()
        assert data_dir.is_dir()

        # And return empty list
        assert conversations == []

    def test_large_number_of_conversations(self, tmp_path, monkeypatch):
        """Test listing a large number of conversations."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        import time

        # Create many conversations
        num_conversations = 50
        for i in range(num_conversations):
            create_conversation(f"conv-{i:03d}")
            # Small delay to ensure different timestamps
            if i % 10 == 0:
                time.sleep(0.01)

        # List conversations
        conversations = list_conversations()

        # Verify all returned
        assert len(conversations) == num_conversations

        # Verify all have required fields
        for conv in conversations:
            assert "id" in conv
            assert "created_at" in conv
            assert "title" in conv
            assert "message_count" in conv

        # Verify sorted (newest first - higher indices should come first)
        # Since we created conv-000, conv-001, ..., conv-049 in order,
        # the newest should be conv-049
        first_id = conversations[0]["id"]
        last_id = conversations[-1]["id"]

        # Extract numbers from IDs
        first_num = int(first_id.split("-")[1])
        last_num = int(last_id.split("-")[1])

        # First should have higher number than last (newer)
        assert first_num > last_num

    def test_conversations_with_special_characters_in_id(self, tmp_path, monkeypatch):
        """Test listing conversations with special characters in IDs."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversations with special characters
        create_conversation("conv-with-hyphens")
        create_conversation("conv_with_underscores")
        create_conversation("conv.with.dots")

        # List conversations
        conversations = list_conversations()

        # Verify all returned
        assert len(conversations) == 3
        conv_ids = {conv["id"] for conv in conversations}
        assert "conv-with-hyphens" in conv_ids
        assert "conv_with_underscores" in conv_ids
        assert "conv.with.dots" in conv_ids

    def test_metadata_matches_full_conversation(self, tmp_path, monkeypatch):
        """Test that metadata from list_conversations matches full conversation."""
        monkeypatch.setattr("backend.conversation_storage.DATA_DIR", tmp_path)

        # Create conversation with messages and custom title
        conversation_id = "conv-match"
        conv = create_conversation(conversation_id)
        update_conversation_title(conversation_id, "Custom Title")
        add_user_message(conversation_id, "Message 1")
        add_user_message(conversation_id, "Message 2")

        # Get full conversation
        full_conv = get_conversation(conversation_id)

        # Get metadata from list
        conversations = list_conversations()
        metadata = conversations[0]

        # Verify metadata matches full conversation
        assert metadata["id"] == full_conv["id"]
        assert metadata["created_at"] == full_conv["created_at"]
        assert metadata["title"] == full_conv["title"]
        assert metadata["message_count"] == len(full_conv["messages"])
