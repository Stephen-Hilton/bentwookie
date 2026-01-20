"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from bentwookie.config import BWConfig, get_config, init_config, reset_config
from bentwookie.constants import DEFAULT_LOGS_PATTERN, DEFAULT_TASKS_SUBDIR


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def reset_config_fixture():
    """Reset config before and after each test."""
    reset_config()
    yield
    reset_config()


class TestBWConfig:
    """Tests for BWConfig class."""

    def test_default_tasks_path(self, temp_dir, reset_config_fixture):
        """Test default tasks path."""
        config = BWConfig()
        assert config.tasks_path == Path(DEFAULT_TASKS_SUBDIR)

    def test_explicit_tasks_path(self, temp_dir, reset_config_fixture):
        """Test explicit tasks path."""
        tasks_path = temp_dir / "my_tasks"
        config = BWConfig(tasks_path=tasks_path)
        assert config.tasks_path == tasks_path

    def test_env_tasks_path(self, temp_dir, reset_config_fixture, monkeypatch):
        """Test tasks path from environment variable."""
        env_path = str(temp_dir / "env_tasks")
        monkeypatch.setenv("BW_TASKS_PATH", env_path)

        config = BWConfig()
        assert str(config.tasks_path) == env_path

    def test_default_logs_path(self, reset_config_fixture):
        """Test default logs path pattern."""
        config = BWConfig()
        assert config.logs_path == DEFAULT_LOGS_PATTERN

    def test_explicit_logs_path(self, reset_config_fixture):
        """Test explicit logs path."""
        logs_path = "custom/logs/{today}.log"
        config = BWConfig(logs_path=logs_path)
        assert config.logs_path == logs_path

    def test_test_mode(self, reset_config_fixture):
        """Test test mode setting."""
        config = BWConfig(test_mode=True)
        assert config.test_mode is True

        config2 = BWConfig(test_mode=False)
        assert config2.test_mode is False

    def test_global_dir(self, temp_dir, reset_config_fixture):
        """Test global directory path."""
        tasks_path = temp_dir / "tasks"
        config = BWConfig(tasks_path=tasks_path)
        assert config.global_dir == tasks_path / "global"

    def test_settings_file(self, temp_dir, reset_config_fixture):
        """Test settings file path."""
        tasks_path = temp_dir / "tasks"
        config = BWConfig(tasks_path=tasks_path)
        assert config.settings_file == tasks_path / "global" / "settings.yaml"

    def test_stage_path(self, temp_dir, reset_config_fixture):
        """Test stage path resolution."""
        tasks_path = temp_dir / "tasks"
        config = BWConfig(tasks_path=tasks_path)

        assert config.get_stage_path("1plan") == tasks_path / "1plan"
        assert config.get_stage_path("2dev") == tasks_path / "2dev"

    def test_resources_path(self, temp_dir, reset_config_fixture):
        """Test resources path resolution."""
        tasks_path = temp_dir / "tasks"
        config = BWConfig(tasks_path=tasks_path)

        assert config.get_resources_path("1plan") == tasks_path / "1plan" / ".resources"


class TestSettingsManagement:
    """Tests for settings.yaml management."""

    def test_load_settings_empty(self, temp_dir, reset_config_fixture):
        """Test loading settings when file doesn't exist."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        config = BWConfig(tasks_path=tasks_path)
        settings = config.load_settings()

        assert settings == {}

    def test_load_settings_existing(self, temp_dir, reset_config_fixture):
        """Test loading existing settings."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        global_dir = tasks_path / "global"
        global_dir.mkdir()

        settings_content = {
            "envfile": "./.bwenv",
            "last_selected": {"phase": "MVP", "priority": 5},
        }
        with open(global_dir / "settings.yaml", "w") as f:
            yaml.dump(settings_content, f)

        config = BWConfig(tasks_path=tasks_path)
        settings = config.load_settings()

        assert settings["envfile"] == "./.bwenv"
        assert settings["last_selected"]["phase"] == "MVP"

    def test_save_settings(self, temp_dir, reset_config_fixture):
        """Test saving settings."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        config = BWConfig(tasks_path=tasks_path)
        settings = {"test_key": "test_value", "nested": {"key": "value"}}

        config.save_settings(settings)

        # Verify by reloading
        loaded = config.load_settings()
        assert loaded["test_key"] == "test_value"
        assert loaded["nested"]["key"] == "value"

    def test_update_setting(self, temp_dir, reset_config_fixture):
        """Test updating a single setting."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        config = BWConfig(tasks_path=tasks_path)
        config.save_settings({"existing": "value"})

        config.update_setting("new_key", "new_value")
        config.update_setting("nested.deep.key", "deep_value")

        settings = config.load_settings()
        assert settings["new_key"] == "new_value"
        assert settings["nested"]["deep"]["key"] == "deep_value"
        assert settings["existing"] == "value"

    def test_get_setting(self, temp_dir, reset_config_fixture):
        """Test getting a setting value."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        config = BWConfig(tasks_path=tasks_path)
        config.save_settings({
            "simple": "value",
            "nested": {"deep": {"key": "nested_value"}},
        })

        assert config.get_setting("simple") == "value"
        assert config.get_setting("nested.deep.key") == "nested_value"
        assert config.get_setting("nonexistent") is None
        assert config.get_setting("nonexistent", "default") == "default"


class TestLastSelected:
    """Tests for last_selected management."""

    def test_get_last_selected_dict_format(self, temp_dir, reset_config_fixture):
        """Test getting last selected with dict format."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        config = BWConfig(tasks_path=tasks_path)
        config.save_settings({
            "last_selected": {"phase": "V1.0", "priority": 7},
        })

        assert config.get_last_selected("phase") == "V1.0"
        assert config.get_last_selected("priority") == 7
        assert config.get_last_selected("nonexistent") is None

    def test_get_last_selected_list_format(self, temp_dir, reset_config_fixture):
        """Test getting last selected with list format (from settings.yaml)."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        # This mimics the format in the actual settings.yaml
        config = BWConfig(tasks_path=tasks_path)
        config.save_settings({
            "last_selected": [
                {"phase": "MVP"},
                {"priority": 5},
                {"change_type": "New Feature"},
            ],
        })

        assert config.get_last_selected("phase") == "MVP"
        assert config.get_last_selected("priority") == 5

    def test_set_last_selected(self, temp_dir, reset_config_fixture):
        """Test setting last selected values."""
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        (tasks_path / "global").mkdir()

        config = BWConfig(tasks_path=tasks_path)
        config.set_last_selected("phase", "POC")
        config.set_last_selected("priority", 9)

        assert config.get_last_selected("phase") == "POC"
        assert config.get_last_selected("priority") == 9


class TestGlobalConfig:
    """Tests for global configuration functions."""

    def test_init_config(self, temp_dir, reset_config_fixture):
        """Test initializing global config."""
        config = init_config(
            tasks_path=temp_dir / "tasks",
            logs_path="test/logs.log",
            test_mode=True,
        )

        assert config.tasks_path == temp_dir / "tasks"
        assert config.logs_path == "test/logs.log"
        assert config.test_mode is True

    def test_get_config(self, temp_dir, reset_config_fixture):
        """Test getting global config."""
        init_config(tasks_path=temp_dir / "tasks")

        config = get_config()
        assert config.tasks_path == temp_dir / "tasks"

    def test_get_config_auto_creates(self, reset_config_fixture):
        """Test that get_config creates config if not initialized."""
        config = get_config()
        assert config is not None
        assert config.tasks_path == Path(DEFAULT_TASKS_SUBDIR)
