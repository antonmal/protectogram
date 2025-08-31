"""Unit tests for Telegram parsing utilities."""

from app.integrations.telegram.parsing import compute_provider_event_id, extract_chat_id


class TestComputeProviderEventId:
    """Test provider event ID computation."""

    def test_message_update(self):
        """Test provider event ID for message update."""
        update = {"update_id": 12345}
        assert compute_provider_event_id(update) == "12345"

    def test_callback_query_update(self):
        """Test provider event ID for callback query update."""
        update = {"update_id": 12345, "callback_query": {"id": "cbq_67890"}}
        assert compute_provider_event_id(update) == "12345"

    def test_callback_query_only(self):
        """Test provider event ID when only callback query is present."""
        update = {"callback_query": {"id": "cbq_67890"}}
        assert compute_provider_event_id(update) == "cbq_67890"

    def test_no_update_id_or_callback(self):
        """Test provider event ID when neither update_id nor callback_query is present."""
        update = {"some_other_field": "value"}
        assert compute_provider_event_id(update) == "unknown"


class TestExtractChatId:
    """Test chat ID extraction."""

    def test_message_chat_id(self):
        """Test extracting chat ID from message."""
        update = {"message": {"chat": {"id": 12345}}}
        assert extract_chat_id(update) == 12345

    def test_callback_query_chat_id(self):
        """Test extracting chat ID from callback query."""
        update = {"callback_query": {"message": {"chat": {"id": 67890}}}}
        assert extract_chat_id(update) == 67890

    def test_edited_message_chat_id(self):
        """Test extracting chat ID from edited message."""
        update = {"edited_message": {"chat": {"id": 11111}}}
        assert extract_chat_id(update) == 11111

    def test_channel_post_chat_id(self):
        """Test extracting chat ID from channel post."""
        update = {"channel_post": {"chat": {"id": 22222}}}
        assert extract_chat_id(update) == 22222

    def test_no_chat_id(self):
        """Test when no chat ID is present."""
        update = {"update_id": 12345}
        assert extract_chat_id(update) is None

    def test_empty_message(self):
        """Test with empty message."""
        update = {"message": {}}
        assert extract_chat_id(update) is None

    def test_empty_callback_query(self):
        """Test with empty callback query."""
        update = {"callback_query": {}}
        assert extract_chat_id(update) is None

    def test_callback_query_no_message(self):
        """Test callback query without message."""
        update = {"callback_query": {"id": "cbq_123"}}
        assert extract_chat_id(update) is None
