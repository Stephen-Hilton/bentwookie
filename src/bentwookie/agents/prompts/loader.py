"""Prompt template loader for BentWookie agents.

Reads ``.md`` files from the user's data/prompts directory first,
falling back to this package directory.  Optionally substitutes
``{placeholder}`` variables via :meth:`str.format_map`.
"""

from functools import lru_cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


class _SafeDict(dict):
    """Returns ``'{key}'`` for missing keys instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _get_user_prompt_dir() -> Path | None:
    """Return the user-facing prompts directory if it exists."""
    from ...db.connection import get_db_path

    data_dir = get_db_path().parent
    user_dir = data_dir / "prompts"
    if user_dir.is_dir():
        return user_dir
    return None


@lru_cache(maxsize=64)
def _read_prompt(name: str) -> str:
    """Read a prompt template from disk (cached).

    Checks user data/prompts/ first, falls back to package directory.
    """
    user_dir = _get_user_prompt_dir()
    if user_dir:
        user_path = user_dir / f"{name}.md"
        if user_path.exists():
            return user_path.read_text(encoding="utf-8")

    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def load_prompt(name: str, **kwargs: str) -> str:
    """Load a prompt template and optionally substitute variables.

    Args:
        name: Filename stem (without ``.md``) of the template.
        **kwargs: Variables to substitute into the template.

    Returns:
        The rendered prompt string.
    """
    template = _read_prompt(name)
    if kwargs:
        return template.format_map(_SafeDict(kwargs))
    return template
