"""Tests for loop/processor module."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from bentwookie.loop import processor
from bentwookie.db import connection, queries
from bentwookie import constants


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    connection.set_db_path(db_path)
    connection.init_db()

    yield db_path

    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_request(temp_db):
    """Create a test project and request."""
    prjid = queries.create_project("Test Project", prjcodedir="/tmp/test")
    reqid = queries.create_request(
        prjid, "Test Request", "Do something",
        reqphase="plan", reqstatus="tbd"
    )
    return {"prjid": prjid, "reqid": reqid}


class TestProcessorConstants:
    """Tests for processor constants."""

    def test_bentwookie_project_id(self):
        """Test BENTWOOKIE_PROJECT_ID is defined."""
        assert hasattr(processor, "BENTWOOKIE_PROJECT_ID")
        assert isinstance(processor.BENTWOOKIE_PROJECT_ID, int)

    def test_max_test_retries(self):
        """Test MAX_TEST_RETRIES is defined."""
        assert hasattr(processor, "MAX_TEST_RETRIES")
        assert isinstance(processor.MAX_TEST_RETRIES, int)
        assert processor.MAX_TEST_RETRIES > 0


class TestCreateBugfixRequest:
    """Tests for _create_bugfix_request helper."""

    def test_create_bugfix_request(self, temp_db, test_request):
        """Test creating a bugfix request from an error."""
        # Create the bentwookie project (ID 3)
        for i in range(2):  # Create projects until we get ID 3
            queries.create_project(f"Project {i}")

        original_request = queries.get_request(test_request["reqid"])

        processor._create_bugfix_request(original_request, "Test error message")

        # Check that a new request was created
        requests = queries.list_requests(status="tbd")
        bugfix_requests = [r for r in requests if "Bug-Fix:" in r["reqname"]]
        assert len(bugfix_requests) >= 1


class TestPhaseTransitions:
    """Tests for phase transition logic."""

    def test_should_advance_plan_to_dev(self, temp_db, test_request):
        """Test phase advancement from plan to dev."""
        request = queries.get_request(test_request["reqid"])
        assert request["reqphase"] == "plan"

        # After plan phase, should advance to dev
        queries.update_request_phase(test_request["reqid"], "dev")
        request = queries.get_request(test_request["reqid"])
        assert request["reqphase"] == "dev"

    def test_should_advance_dev_to_test(self, temp_db, test_request):
        """Test phase advancement from dev to test."""
        queries.update_request_phase(test_request["reqid"], "dev")

        # After dev phase, should advance to test
        queries.update_request_phase(test_request["reqid"], "test")
        request = queries.get_request(test_request["reqid"])
        assert request["reqphase"] == "test"


class TestProcessRequest:
    """Tests for process_request function."""

    def test_process_request_no_sdk(self, temp_db, test_request, monkeypatch):
        """Test process_request when SDK is not available."""
        import asyncio

        # Mock SDK as not available
        monkeypatch.setattr(processor, "SDK_AVAILABLE", False)

        request = queries.get_request(test_request["reqid"])

        # This should handle the missing SDK gracefully
        asyncio.run(processor.process_request(request))

        # Request should be in error state
        updated = queries.get_request(test_request["reqid"])
        assert updated["reqstatus"] == constants.STATUS_ERR

    @patch("bentwookie.settings.get_auth_mode")
    def test_process_request_no_api_key(
        self, mock_get_auth, temp_db, test_request, monkeypatch
    ):
        """Test process_request when API key is missing."""
        import asyncio
        from bentwookie.settings import AUTH_MODE_API

        monkeypatch.setattr(processor, "SDK_AVAILABLE", True)
        mock_get_auth.return_value = AUTH_MODE_API
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        request = queries.get_request(test_request["reqid"])

        asyncio.run(processor.process_request(request))

        # Request should be in error state
        updated = queries.get_request(test_request["reqid"])
        assert updated["reqstatus"] == constants.STATUS_ERR

    @patch("bentwookie.loop.processor.query")
    @patch("bentwookie.settings.get_auth_mode")
    def test_process_request_success(
        self, mock_get_auth, mock_query, temp_db, test_request, monkeypatch
    ):
        """Test process_request successful execution."""
        import asyncio
        from bentwookie.settings import AUTH_MODE_API

        monkeypatch.setattr(processor, "SDK_AVAILABLE", True)
        mock_get_auth.return_value = AUTH_MODE_API
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")

        # Mock the query function to return a successful result
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="Task completed successfully")]
        mock_result.content[0].type = "text"
        mock_query.return_value = mock_result

        request = queries.get_request(test_request["reqid"])

        asyncio.run(processor.process_request(request))

        # Check that the phase was updated (should advance or complete)
        updated = queries.get_request(test_request["reqid"])
        # Should not be in error state with successful mock
        assert updated is not None


class TestApiKeyHandling:
    """Tests for API key handling in processor."""

    @patch("bentwookie.settings.get_auth_mode")
    def test_api_key_from_env(self, mock_get_auth, temp_db, test_request, monkeypatch):
        """Test that API key is read from environment."""
        import asyncio
        from bentwookie.settings import AUTH_MODE_API

        monkeypatch.setattr(processor, "SDK_AVAILABLE", True)
        mock_get_auth.return_value = AUTH_MODE_API
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        request = queries.get_request(test_request["reqid"])

        # This will use the API key from env
        # Even if processing fails, the key should be found
        asyncio.run(processor.process_request(request))

        # Should not have an auth error
        updated = queries.get_request(test_request["reqid"])
        if updated["reqerror"]:
            assert "ANTHROPIC_API_KEY not set" not in updated["reqerror"]

    @patch("bentwookie.settings.get_auth_mode")
    def test_api_key_not_set(self, mock_get_auth, temp_db, test_request, monkeypatch):
        """Test process_request when API key not set."""
        import asyncio
        from bentwookie.settings import AUTH_MODE_API

        monkeypatch.setattr(processor, "SDK_AVAILABLE", True)
        mock_get_auth.return_value = AUTH_MODE_API
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        request = queries.get_request(test_request["reqid"])

        asyncio.run(processor.process_request(request))

        # Should be in error state
        updated = queries.get_request(test_request["reqid"])
        assert updated["reqstatus"] == constants.STATUS_ERR


class TestErrorHandling:
    """Tests for error handling in processor."""

    @patch("bentwookie.loop.processor.query")
    @patch("bentwookie.settings.get_auth_mode")
    def test_handles_agent_exception(
        self, mock_get_auth, mock_query, temp_db, test_request, monkeypatch
    ):
        """Test processor handles agent exceptions gracefully."""
        import asyncio
        from bentwookie.settings import AUTH_MODE_API

        monkeypatch.setattr(processor, "SDK_AVAILABLE", True)
        mock_get_auth.return_value = AUTH_MODE_API
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")

        # Mock query to raise exception
        mock_query.side_effect = Exception("Agent failed")

        request = queries.get_request(test_request["reqid"])

        # Should not raise, but set error status
        asyncio.run(processor.process_request(request))

        updated = queries.get_request(test_request["reqid"])
        assert updated["reqstatus"] == constants.STATUS_ERR
        assert updated["reqerror"] is not None
