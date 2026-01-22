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
    "loop_paused": False,
    "max_iterations": 0,  # 0 = unlimited
    "doc_retention_days": 30,  # Auto-cleanup docs older than this (0 = disabled)
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


# =============================================================================
# Loop Control Settings
# =============================================================================


def is_loop_paused() -> bool:
    """Check if the loop is paused.

    Returns:
        True if paused, False otherwise.
    """
    return get_setting("loop_paused", False)


def set_loop_paused(paused: bool) -> None:
    """Set the loop paused state.

    Args:
        paused: True to pause, False to resume.
    """
    set_setting("loop_paused", paused)


def pause_loop() -> None:
    """Pause the loop."""
    set_loop_paused(True)


def resume_loop() -> None:
    """Resume the loop."""
    set_loop_paused(False)


def get_max_iterations() -> int:
    """Get the maximum number of iterations (0 = unlimited).

    Returns:
        Max iterations setting.
    """
    return get_setting("max_iterations", 0)


def set_max_iterations(max_iter: int) -> None:
    """Set the maximum number of iterations.

    Args:
        max_iter: Max iterations (0 = unlimited).
    """
    set_setting("max_iterations", max(0, max_iter))


def get_poll_interval() -> int:
    """Get the poll interval in seconds.

    Returns:
        Poll interval in seconds.
    """
    return get_setting("poll_interval", 30)


def set_poll_interval(interval: int) -> None:
    """Set the poll interval.

    Args:
        interval: Poll interval in seconds.
    """
    set_setting("poll_interval", max(1, interval))


def get_loop_settings() -> dict:
    """Get all loop-related settings.

    Returns:
        Dict with loop settings.
    """
    return {
        "loop_paused": is_loop_paused(),
        "max_iterations": get_max_iterations(),
        "poll_interval": get_poll_interval(),
    }


def update_loop_settings(
    paused: bool | None = None,
    max_iterations: int | None = None,
    poll_interval: int | None = None,
) -> dict:
    """Update loop settings.

    Args:
        paused: New paused state (optional).
        max_iterations: New max iterations (optional).
        poll_interval: New poll interval (optional).

    Returns:
        Updated loop settings dict.
    """
    if paused is not None:
        set_loop_paused(paused)
    if max_iterations is not None:
        set_max_iterations(max_iterations)
    if poll_interval is not None:
        set_poll_interval(poll_interval)

    return get_loop_settings()


# =============================================================================
# Document Retention Settings
# =============================================================================


def get_doc_retention_days() -> int:
    """Get the document retention period in days.

    Returns:
        Number of days to retain docs (0 = disabled/keep forever).
    """
    return get_setting("doc_retention_days", 30)


def set_doc_retention_days(days: int) -> None:
    """Set the document retention period.

    Args:
        days: Number of days to retain docs (0 = disabled/keep forever).
    """
    set_setting("doc_retention_days", max(0, days))
