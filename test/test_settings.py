"""Tests for settings module."""

import json
import pytest
from pathlib import Path
import tempfile

from bentwookie import settings


@pytest.fixture
def temp_settings_dir(monkeypatch):
    """Create a temporary directory for settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.json"
        monkeypatch.setattr(settings, "DEFAULT_SETTINGS_PATH", settings_path)
        yield settings_path


class TestSettingsBasics:
    """Tests for basic settings operations."""

    def test_get_settings_path(self, temp_settings_dir):
        """Test getting settings path."""
        path = settings.get_settings_path()
        assert path == temp_settings_dir

    def test_load_settings_defaults(self, temp_settings_dir):
        """Test loading settings returns defaults when no file exists."""
        s = settings.load_settings()

        assert "auth_mode" in s
        assert "model" in s
        assert "max_turns" in s
        assert "poll_interval" in s
        assert "doc_retention_days" in s

    def test_load_settings_from_file(self, temp_settings_dir):
        """Test loading settings from existing file."""
        temp_settings_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_settings_dir.write_text(json.dumps({"auth_mode": "api", "custom": "value"}))

        s = settings.load_settings()
        assert s["auth_mode"] == "api"
        assert s["custom"] == "value"
        # Defaults should still be present
        assert "model" in s

    def test_load_settings_invalid_json(self, temp_settings_dir):
        """Test loading settings with invalid JSON returns defaults."""
        temp_settings_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_settings_dir.write_text("not valid json")

        s = settings.load_settings()
        assert s == settings.DEFAULT_SETTINGS

    def test_save_settings(self, temp_settings_dir):
        """Test saving settings to file."""
        settings.save_settings({"auth_mode": "api", "test": True})

        assert temp_settings_dir.exists()
        saved = json.loads(temp_settings_dir.read_text())
        assert saved["auth_mode"] == "api"
        assert saved["test"] is True

    def test_save_settings_creates_directory(self, temp_settings_dir):
        """Test save_settings creates parent directory if needed."""
        # Remove the parent directory
        if temp_settings_dir.parent.exists():
            temp_settings_dir.parent.rmdir()

        settings.save_settings({"test": "value"})
        assert temp_settings_dir.exists()

    def test_get_setting(self, temp_settings_dir):
        """Test getting a single setting."""
        settings.save_settings({"my_key": "my_value"})

        value = settings.get_setting("my_key")
        assert value == "my_value"

    def test_get_setting_default(self, temp_settings_dir):
        """Test getting a setting with default value."""
        value = settings.get_setting("nonexistent", "default_value")
        assert value == "default_value"

    def test_set_setting(self, temp_settings_dir):
        """Test setting a single value."""
        settings.set_setting("new_key", "new_value")

        s = settings.load_settings()
        assert s["new_key"] == "new_value"


class TestAuthMode:
    """Tests for auth mode settings."""

    def test_get_auth_mode_default(self, temp_settings_dir):
        """Test getting default auth mode."""
        mode = settings.get_auth_mode()
        assert mode == settings.AUTH_MODE_MAX

    def test_get_auth_mode_saved(self, temp_settings_dir):
        """Test getting saved auth mode."""
        settings.save_settings({"auth_mode": "api"})
        mode = settings.get_auth_mode()
        assert mode == "api"

    def test_set_auth_mode_valid(self, temp_settings_dir):
        """Test setting valid auth mode."""
        settings.set_auth_mode("api")
        assert settings.get_auth_mode() == "api"

        settings.set_auth_mode("max")
        assert settings.get_auth_mode() == "max"

    def test_set_auth_mode_invalid(self, temp_settings_dir):
        """Test setting invalid auth mode raises error."""
        with pytest.raises(ValueError) as exc:
            settings.set_auth_mode("invalid")

        assert "Invalid auth mode" in str(exc.value)


class TestLoopSettings:
    """Tests for loop control settings."""

    def test_is_loop_paused_default(self, temp_settings_dir):
        """Test default loop paused state."""
        assert settings.is_loop_paused() is False

    def test_set_loop_paused(self, temp_settings_dir):
        """Test setting loop paused state."""
        settings.set_loop_paused(True)
        assert settings.is_loop_paused() is True

        settings.set_loop_paused(False)
        assert settings.is_loop_paused() is False

    def test_pause_loop(self, temp_settings_dir):
        """Test pause_loop helper."""
        settings.pause_loop()
        assert settings.is_loop_paused() is True

    def test_resume_loop(self, temp_settings_dir):
        """Test resume_loop helper."""
        settings.pause_loop()
        settings.resume_loop()
        assert settings.is_loop_paused() is False

    def test_get_max_iterations_default(self, temp_settings_dir):
        """Test default max iterations."""
        assert settings.get_max_iterations() == 0

    def test_set_max_iterations(self, temp_settings_dir):
        """Test setting max iterations."""
        settings.set_max_iterations(10)
        assert settings.get_max_iterations() == 10

    def test_set_max_iterations_negative(self, temp_settings_dir):
        """Test setting negative max iterations clamps to 0."""
        settings.set_max_iterations(-5)
        assert settings.get_max_iterations() == 0

    def test_get_poll_interval_default(self, temp_settings_dir):
        """Test default poll interval."""
        assert settings.get_poll_interval() == 30

    def test_set_poll_interval(self, temp_settings_dir):
        """Test setting poll interval."""
        settings.set_poll_interval(60)
        assert settings.get_poll_interval() == 60

    def test_set_poll_interval_minimum(self, temp_settings_dir):
        """Test poll interval has minimum of 1."""
        settings.set_poll_interval(0)
        assert settings.get_poll_interval() == 1

    def test_get_loop_settings(self, temp_settings_dir):
        """Test getting all loop settings."""
        settings.set_loop_paused(True)
        settings.set_max_iterations(5)
        settings.set_poll_interval(45)

        loop_settings = settings.get_loop_settings()

        assert loop_settings["loop_paused"] is True
        assert loop_settings["max_iterations"] == 5
        assert loop_settings["poll_interval"] == 45

    def test_update_loop_settings(self, temp_settings_dir):
        """Test updating multiple loop settings at once."""
        result = settings.update_loop_settings(
            paused=True,
            max_iterations=10,
            poll_interval=120,
        )

        assert result["loop_paused"] is True
        assert result["max_iterations"] == 10
        assert result["poll_interval"] == 120

    def test_update_loop_settings_partial(self, temp_settings_dir):
        """Test updating only some loop settings."""
        settings.set_poll_interval(30)

        result = settings.update_loop_settings(paused=True)

        assert result["loop_paused"] is True
        assert result["poll_interval"] == 30  # Unchanged


class TestDocRetentionSettings:
    """Tests for document retention settings."""

    def test_get_doc_retention_days_default(self, temp_settings_dir):
        """Test default doc retention days."""
        days = settings.get_doc_retention_days()
        assert days == 30

    def test_set_doc_retention_days(self, temp_settings_dir):
        """Test setting doc retention days."""
        settings.set_doc_retention_days(60)
        assert settings.get_doc_retention_days() == 60

    def test_set_doc_retention_days_zero(self, temp_settings_dir):
        """Test setting doc retention to 0 (disabled)."""
        settings.set_doc_retention_days(0)
        assert settings.get_doc_retention_days() == 0

    def test_set_doc_retention_days_negative(self, temp_settings_dir):
        """Test setting negative retention clamps to 0."""
        settings.set_doc_retention_days(-10)
        assert settings.get_doc_retention_days() == 0
