"""Settings management for BentWookie."""

import json
from pathlib import Path
from typing import Any

# Default settings file location
DEFAULT_SETTINGS_PATH = Path("data/settings.json")
_settings_path: Path | None = None

# Auth modes
AUTH_MODE_API = "api"      # Uses ANTHROPIC_API_KEY environment variable
AUTH_MODE_MAX = "max"      # Uses Claude Max subscription (web auth via CLI)

VALID_AUTH_MODES = [AUTH_MODE_API, AUTH_MODE_MAX]

# Default settings
DEFAULT_SETTINGS = {
    "auth_mode": AUTH_MODE_MAX,  # Default to Max since it's simpler
    "model": "claude-opus-4-5",
    "max_turns": 50,
    "poll_interval": 30,
    "loop_paused": False,
    "max_iterations": 0,  # 0 = unlimited
    "doc_retention_days": 30,  # Auto-cleanup docs older than this (0 = disabled)
    "commit_enabled": True,  # Enable commit phase by default
    "commit_branch_mode": "current",  # "current" or "other"
    "commit_branch_name": None,  # Branch name when mode="other"
    "web_host": "127.0.0.1",  # Default web server host
    "web_port": 5000,  # Default web server port
    # V2 settings
    "max_concurrent_agents": 5,  # Max agents running simultaneously
    "agent_timeout": 30,  # Agent task timeout in minutes
    "define_timeout": 30,  # Define phase timeout in minutes
    "design_timeout": 120,  # Design phase timeout in minutes
    "validate_timeout": 60,  # Validate phase timeout in minutes
    "build_timeout": 240,  # Build phase timeout in minutes
    "voice_enabled": True,  # Enable voice input in interviews
    "sse_enabled": True,  # Enable server-sent events
    # Per-type agent limits
    "max_enterprise_architect": 1,
    "max_business_architect": 1,
    "max_service_engineer": 5,
    "max_coding_agent": 10,
    "max_testing_agent": 5,
    # Task queue settings
    "safe_word": "KAMILI",
    "max_task_retries": 3,
    "orchestrator_poll_interval": 2,
    "agent_permission_mode": "dangerously-skip-permissions",
}


def get_settings_path() -> Path:
    """Get the path to the settings file."""
    return _settings_path or DEFAULT_SETTINGS_PATH


def set_settings_path(path: str | Path) -> None:
    """Set a custom path for the settings file."""
    global _settings_path
    _settings_path = Path(path)


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


def get_model() -> str:
    """Get the model to use for Claude API calls.

    Returns:
        Model identifier string (e.g., 'claude-opus-4-5').
    """
    return get_setting("model", DEFAULT_SETTINGS["model"])


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


def get_max_turns() -> int:
    """Get the maximum turns per phase.

    Returns:
        Max turns setting (default: 50).
    """
    return get_setting("max_turns", 50)


def set_max_turns(turns: int) -> None:
    """Set the maximum turns per phase.

    Args:
        turns: Max turns per phase (minimum: 1).
    """
    set_setting("max_turns", max(1, turns))


def get_loop_settings() -> dict:
    """Get all loop-related settings.

    Returns:
        Dict with loop settings.
    """
    return {
        "loop_paused": is_loop_paused(),
        "max_iterations": get_max_iterations(),
        "poll_interval": get_poll_interval(),
        "max_turns": get_max_turns(),
        "doc_retention_days": get_doc_retention_days(),
        "commit_enabled": get_commit_enabled(),
        "commit_branch_mode": get_commit_branch_mode(),
        "commit_branch_name": get_commit_branch_name(),
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


# =============================================================================
# Commit Phase Settings
# =============================================================================


def get_commit_enabled() -> bool:
    """Check if commit phase is enabled.

    Returns:
        True if commit phase is enabled, False otherwise.
    """
    return get_setting("commit_enabled", True)


def set_commit_enabled(enabled: bool) -> None:
    """Enable or disable the commit phase.

    Args:
        enabled: True to enable, False to disable.
    """
    set_setting("commit_enabled", enabled)


def get_commit_branch_mode() -> str:
    """Get the commit branch mode.

    Returns:
        "current" or "other"
    """
    return get_setting("commit_branch_mode", "current")


def set_commit_branch_mode(mode: str) -> None:
    """Set the commit branch mode.

    Args:
        mode: "current" to commit to current branch, "other" to commit to specific branch.

    Raises:
        ValueError: If mode is invalid.
    """
    from .constants import VALID_COMMIT_BRANCHES

    if mode not in VALID_COMMIT_BRANCHES:
        raise ValueError(f"Invalid mode: {mode}. Must be one of: {VALID_COMMIT_BRANCHES}")
    set_setting("commit_branch_mode", mode)


def get_commit_branch_name() -> str | None:
    """Get the branch name to commit to (when mode="other").

    Returns:
        Branch name or None if not set.
    """
    return get_setting("commit_branch_name")


def set_commit_branch_name(name: str | None) -> None:
    """Set the branch name to commit to.

    Args:
        name: Branch name or None to clear.
    """
    set_setting("commit_branch_name", name)


# =============================================================================
# Web Server Settings
# =============================================================================


def get_web_host() -> str:
    """Get the web server host address.

    Returns:
        Host address (default: "127.0.0.1").
    """
    return get_setting("web_host", "127.0.0.1")


def set_web_host(host: str) -> None:
    """Set the web server host address.

    Args:
        host: Host address to bind to.
    """
    set_setting("web_host", host)


def get_web_port() -> int:
    """Get the web server port.

    Returns:
        Port number (default: 5000).
    """
    return get_setting("web_port", 5000)


def set_web_port(port: int) -> None:
    """Set the web server port.

    Args:
        port: Port number to bind to.
    """
    set_setting("web_port", port)


# =============================================================================
# V2 Agent Settings
# =============================================================================


def get_max_concurrent_agents() -> int:
    """Get the maximum number of concurrent agents."""
    return get_setting("max_concurrent_agents", 5)


def set_max_concurrent_agents(count: int) -> None:
    """Set the maximum number of concurrent agents."""
    set_setting("max_concurrent_agents", max(1, count))


def get_agent_timeout() -> int:
    """Get the agent task timeout in minutes."""
    return get_setting("agent_timeout", 30)


def set_agent_timeout(minutes: int) -> None:
    """Set the agent task timeout in minutes."""
    set_setting("agent_timeout", max(1, minutes))


def get_phase_timeout(phase: str) -> int:
    """Get the timeout for a specific phase in minutes."""
    key = f"{phase}_timeout"
    defaults = {
        "define_timeout": 30,
        "design_timeout": 120,
        "validate_timeout": 60,
        "build_timeout": 240,
    }
    return get_setting(key, defaults.get(key, 60))


def set_phase_timeout(phase: str, minutes: int) -> None:
    """Set the timeout for a specific phase in minutes."""
    set_setting(f"{phase}_timeout", max(1, minutes))


def is_voice_enabled() -> bool:
    """Check if voice input is enabled."""
    return get_setting("voice_enabled", True)


def set_voice_enabled(enabled: bool) -> None:
    """Enable or disable voice input."""
    set_setting("voice_enabled", enabled)


def is_sse_enabled() -> bool:
    """Check if SSE is enabled."""
    return get_setting("sse_enabled", True)


def set_sse_enabled(enabled: bool) -> None:
    """Enable or disable SSE."""
    set_setting("sse_enabled", enabled)


# =============================================================================
# Hierarchical Settings Resolution
# =============================================================================


def resolve_setting(
    key: str,
    agent_id: int | None = None,
    agent_role: str | None = None,
) -> Any:
    """Resolve a setting using hierarchical cascade.

    Resolution order: individual agent > agent type > global setting.

    Args:
        key: Setting key to resolve.
        agent_id: Optional specific agent ID for per-agent override.
        agent_role: Optional agent role for per-type override.

    Returns:
        The resolved setting value.
    """
    from .db.queries import get_agent_setting

    # 1. Check individual agent override
    if agent_id is not None:
        value = get_agent_setting("agent", str(agent_id), key)
        if value is not None:
            return _coerce_setting_value(key, value)

    # 2. Check agent type override
    if agent_role is not None:
        value = get_agent_setting("agent_type", agent_role, key)
        if value is not None:
            return _coerce_setting_value(key, value)

    # 3. Fall back to global setting
    return get_setting(key)


# =============================================================================
# Task Queue Settings
# =============================================================================


def get_safe_word() -> str:
    """Get the safe word agents use to signal task completion."""
    return get_setting("safe_word", "KAMILI")


def set_safe_word(word: str) -> None:
    """Set the safe word for agent task completion signaling.

    Args:
        word: The safe word string.

    Raises:
        ValueError: If word is empty.
    """
    if not word or not word.strip():
        raise ValueError("Safe word must not be empty")
    set_setting("safe_word", word.strip())


def get_max_task_retries() -> int:
    """Get the maximum number of task retries before marking failed."""
    return get_setting("max_task_retries", 3)


def get_orchestrator_poll_interval() -> int:
    """Get the orchestrator poll interval in seconds."""
    return get_setting("orchestrator_poll_interval", 2)


def _coerce_setting_value(key: str, value: str) -> Any:
    """Coerce a string setting value to the appropriate type.

    Agent settings are stored as strings in the DB; this converts
    them back to the type expected by the global defaults.

    Args:
        key: Setting key (used to determine expected type).
        value: String value from the database.

    Returns:
        Coerced value.
    """
    defaults = DEFAULT_SETTINGS
    if key in defaults:
        expected_type = type(defaults[key])
        if expected_type is int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return defaults[key]
        elif expected_type is bool:
            return value.lower() in ("true", "1", "yes")
        elif expected_type is float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return defaults[key]
    return value
