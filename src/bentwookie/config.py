"""Configuration management for BentWookie."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .constants import (
    DEFAULT_LOGS_PATTERN,
    DEFAULT_TASKS_SUBDIR,
    ENV_KEYS,
    GLOBAL_DIR,
    SETTINGS_FILE,
)
from .exceptions import ConfigurationError


class BWConfig:
    """Configuration manager for BentWookie.

    Handles environment variable loading, settings.yaml management,
    and path resolution.
    """

    def __init__(
        self,
        env_path: str | Path | None = None,
        tasks_path: str | Path | None = None,
        logs_path: str | Path | None = None,
        test_mode: bool = False,
    ):
        """Initialize configuration.

        Args:
            env_path: Path to .env file (optional)
            tasks_path: Path to tasks directory (optional)
            logs_path: Log file path pattern (optional)
            test_mode: If True, disables stage movement
        """
        self._env_path = Path(env_path) if env_path else None
        self._tasks_path = Path(tasks_path) if tasks_path else None
        self._logs_path = logs_path
        self._test_mode = test_mode
        self._settings: dict[str, Any] | None = None

        # Load environment variables
        self._load_env()

    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        if self._env_path and self._env_path.exists():
            load_dotenv(self._env_path)
        else:
            # Try default locations
            for default_path in [".env", ".bwenv"]:
                if Path(default_path).exists():
                    load_dotenv(default_path)
                    break

    @property
    def test_mode(self) -> bool:
        """Return whether test mode is enabled."""
        return self._test_mode

    @property
    def env_path(self) -> Path | None:
        """Return the environment file path."""
        return self._env_path

    @property
    def tasks_path(self) -> Path:
        """Return the tasks directory path.

        Resolution order:
        1. Explicitly set path
        2. BW_TASKS_PATH environment variable
        3. Default: ./tasks
        """
        if self._tasks_path:
            return self._tasks_path

        env_tasks = os.getenv(ENV_KEYS["TASKS_PATH"])
        if env_tasks:
            return Path(env_tasks)

        return Path(DEFAULT_TASKS_SUBDIR)

    @property
    def logs_path(self) -> str:
        """Return the logs path pattern.

        Resolution order:
        1. Explicitly set path
        2. BW_LOGS_PATH environment variable
        3. Default pattern: logs/{loopname}_{today}.log
        """
        if self._logs_path:
            return self._logs_path

        env_logs = os.getenv(ENV_KEYS["LOGS_PATH"])
        if env_logs:
            return env_logs

        return DEFAULT_LOGS_PATTERN

    @property
    def global_dir(self) -> Path:
        """Return the global settings directory path."""
        return self.tasks_path / GLOBAL_DIR

    @property
    def settings_file(self) -> Path:
        """Return the settings.yaml file path."""
        return self.global_dir / SETTINGS_FILE

    def get_env(self, key: str, default: str | None = None) -> str | None:
        """Get an environment variable.

        Args:
            key: Short key name (e.g., 'LLM_PROVIDER')
            default: Default value if not set

        Returns:
            Environment variable value or default
        """
        env_key = ENV_KEYS.get(key, key)
        return os.getenv(env_key, default)

    def load_settings(self) -> dict[str, Any]:
        """Load settings from settings.yaml.

        Returns:
            Settings dictionary

        Raises:
            ConfigurationError: If settings file cannot be loaded
        """
        if self._settings is not None:
            return self._settings

        if not self.settings_file.exists():
            self._settings = {}
            return self._settings

        try:
            with open(self.settings_file, encoding="utf-8") as f:
                self._settings = yaml.safe_load(f) or {}
                return self._settings
        except yaml.YAMLError as e:
            raise ConfigurationError(
                "settings.yaml",
                f"Failed to parse YAML: {e}",
            )
        except OSError as e:
            raise ConfigurationError(
                "settings.yaml",
                f"Failed to read file: {e}",
            )

    def save_settings(self, settings: dict[str, Any]) -> None:
        """Save settings to settings.yaml.

        Args:
            settings: Settings dictionary to save

        Raises:
            ConfigurationError: If settings cannot be saved
        """
        try:
            self.global_dir.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                yaml.dump(settings, f, default_flow_style=False, allow_unicode=True)
            self._settings = settings
        except OSError as e:
            raise ConfigurationError(
                "settings.yaml",
                f"Failed to write file: {e}",
            )

    def update_setting(self, key: str, value: Any) -> None:
        """Update a single setting and save.

        Args:
            key: Setting key (supports dot notation for nested keys)
            value: New value
        """
        settings = self.load_settings()
        keys = key.split(".")

        # Navigate to the nested location
        current = settings
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value
        self.save_settings(settings)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key (supports dot notation for nested keys)
            default: Default value if not found

        Returns:
            Setting value or default
        """
        settings = self.load_settings()
        keys = key.split(".")

        current = settings
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return default
            current = current[k]

        return current

    def get_last_selected(self, key: str, default: Any = None) -> Any:
        """Get a last-selected value from settings.

        Args:
            key: Setting key within last_selected
            default: Default value if not found

        Returns:
            Last selected value or default
        """
        settings = self.load_settings()
        last_selected = settings.get("last_selected", [])

        # Handle list format from settings.yaml
        if isinstance(last_selected, list):
            for item in last_selected:
                if isinstance(item, dict) and key in item:
                    return item[key]
        elif isinstance(last_selected, dict):
            return last_selected.get(key, default)

        return default

    def set_last_selected(self, key: str, value: Any) -> None:
        """Set a last-selected value in settings.

        Args:
            key: Setting key within last_selected
            value: Value to set
        """
        settings = self.load_settings()
        last_selected = settings.get("last_selected", [])

        # Convert to dict format if needed
        if isinstance(last_selected, list):
            new_last_selected = {}
            for item in last_selected:
                if isinstance(item, dict):
                    new_last_selected.update(item)
            last_selected = new_last_selected

        if not isinstance(last_selected, dict):
            last_selected = {}

        last_selected[key] = value
        settings["last_selected"] = last_selected
        self.save_settings(settings)

    def get_infrastructure_options(self, category: str) -> list[str]:
        """Get infrastructure options for a category.

        Args:
            category: One of 'compute', 'storage', 'queue', 'access'

        Returns:
            List of options
        """
        settings = self.load_settings()
        infra = settings.get("infrastructure", {})
        return infra.get(category, [])

    def get_stage_path(self, stage: str) -> Path:
        """Get the path for a specific stage directory.

        Args:
            stage: Stage name (e.g., '1plan', '2dev')

        Returns:
            Path to the stage directory
        """
        return self.tasks_path / stage

    def get_resources_path(self, stage: str) -> Path:
        """Get the .resources path for a specific stage.

        Args:
            stage: Stage name

        Returns:
            Path to the .resources directory
        """
        return self.get_stage_path(stage) / ".resources"

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the tasks directory.

        Args:
            path: Path to resolve

        Returns:
            Resolved absolute path
        """
        p = Path(path)
        if p.is_absolute():
            return p
        return self.tasks_path / p


# Global configuration instance
_config: BWConfig | None = None


def get_config() -> BWConfig:
    """Get the global configuration instance.

    Returns:
        Global BWConfig instance

    Raises:
        ConfigurationError: If configuration not initialized
    """
    global _config
    if _config is None:
        _config = BWConfig()
    return _config


def init_config(
    env_path: str | Path | None = None,
    tasks_path: str | Path | None = None,
    logs_path: str | Path | None = None,
    test_mode: bool = False,
) -> BWConfig:
    """Initialize the global configuration.

    Args:
        env_path: Path to .env file
        tasks_path: Path to tasks directory
        logs_path: Log file path pattern
        test_mode: If True, disables stage movement

    Returns:
        Initialized BWConfig instance
    """
    global _config
    _config = BWConfig(
        env_path=env_path,
        tasks_path=tasks_path,
        logs_path=logs_path,
        test_mode=test_mode,
    )
    return _config


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None
