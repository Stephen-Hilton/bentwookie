"""Prompt templates for BentWookie agents.

All prompt text lives in sibling ``.md`` files and is loaded on demand
via :func:`load_prompt`.
"""

from .loader import load_prompt

__all__ = ["load_prompt"]
