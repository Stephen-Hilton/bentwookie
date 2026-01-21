"""Settings management for BentWookie."""

import json
from pathlib import Path
from typing import Any

# Default settings file location
DEFAULT_SETTINGS_PATH = Path("data/settings.json")

# Auth modes
AUTH_MODE_API = "api"      # Uses ANTHROPIC_API_KEY environment variable
AUTH_MODE_MAX = "max"      # Uses Claude Max subscription (web auth via CLI)

VALID_AUTH_MODES = [AUTH_MODE_API, AUTH_MODE_MAX]

# Default settings
DEFAULT_SETTINGS = {
    "auth_mode": AUTH_MODE_MAX,  # Default to Max since it's simpler
    "model": "claude-sonnet-4-20250514",
    "max_turns": 50,
    "poll_interval": 30,
}


def get_settings_path() -> Path:
    """Get the path to the settings file."""
    return DEFAULT_SETTINGS_PATH


def load_settings() -> dict[str, Any]:
    """Load settings from file.

    Returns:
        Settings dict, with defaults for missing keys.
    """
    settings = DEFAULT_SETTINGS.copy()

    path = get_settings_path()
    if path.exists():
        try:
            with open(path) as f:
                saved = json.load(f)
                settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass

    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings to file.

    Args:
        settings: Settings dict to save.
    """
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(settings, f, indent=2)


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value.

    Args:
        key: Setting key.
        default: Default value if key not found.

    Returns:
        Setting value.
    """
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Set a single setting value.

    Args:
        key: Setting key.
        value: Value to set.
    """
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def get_auth_mode() -> str:
    """Get the current auth mode.

    Returns:
        'api' or 'max'
    """
    return get_setting("auth_mode", AUTH_MODE_MAX)


def set_auth_mode(mode: str) -> None:
    """Set the auth mode.

    Args:
        mode: 'api' or 'max'

    Raises:
        ValueError: If mode is invalid.
    """
    if mode not in VALID_AUTH_MODES:
        raise ValueError(f"Invalid auth mode: {mode}. Must be one of: {VALID_AUTH_MODES}")
    set_setting("auth_mode", mode)
