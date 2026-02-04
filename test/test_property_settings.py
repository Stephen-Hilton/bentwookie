"""Property-based tests for loop settings round-trip persistence.

Feature: bentwookie-web-ui-enhancements
Property 4: Settings Round-Trip Persistence
Property 5: Settings Input Validation

Validates: Requirements 3.2, 3.3, 3.4
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from bentwookie.settings import (
    get_commit_branch_mode,
    get_commit_branch_name,
    get_commit_enabled,
    get_doc_retention_days,
    get_max_iterations,
    get_max_turns,
    get_poll_interval,
    is_loop_paused,
    set_commit_branch_mode,
    set_commit_branch_name,
    set_commit_enabled,
    set_doc_retention_days,
    set_max_iterations,
    set_max_turns,
    set_poll_interval,
    set_loop_paused,
)


class TestPropertySettingsRoundTrip:
    """Property 4: Settings Round-Trip Persistence.

    For any valid loop control setting value, updating the setting via the
    settings module and then reading it back SHALL return the same value
    that was set.

    **Validates: Requirements 3.2, 3.3**
    """

    @settings(max_examples=25)
    @given(st.integers(min_value=1, max_value=3600))
    def test_poll_interval_round_trip(self, value: int):
        """Poll interval values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_poll_interval(value)
                result = get_poll_interval()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.integers(min_value=0, max_value=10000))
    def test_max_iterations_round_trip(self, value: int):
        """Max iterations values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_max_iterations(value)
                result = get_max_iterations()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.integers(min_value=1, max_value=500))
    def test_max_turns_round_trip(self, value: int):
        """Max turns values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_max_turns(value)
                result = get_max_turns()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.integers(min_value=0, max_value=365))
    def test_doc_retention_days_round_trip(self, value: int):
        """Doc retention days values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_doc_retention_days(value)
                result = get_doc_retention_days()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.booleans())
    def test_loop_paused_round_trip(self, value: bool):
        """Loop paused boolean values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_loop_paused(value)
                result = is_loop_paused()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.booleans())
    def test_commit_enabled_round_trip(self, value: bool):
        """Commit enabled boolean values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_commit_enabled(value)
                result = get_commit_enabled()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.sampled_from(["current", "other"]))
    def test_commit_branch_mode_round_trip(self, value: str):
        """Commit branch mode values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_commit_branch_mode(value)
                result = get_commit_branch_mode()
                assert result == value, f"Expected {value}, got {result}"

    @settings(max_examples=25)
    @given(st.one_of(
        st.none(),
        st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
    ))
    def test_commit_branch_name_round_trip(self, value: str | None):
        """Commit branch name values round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_commit_branch_name(value)
                result = get_commit_branch_name()
                assert result == value, f"Expected {value}, got {result}"


class TestPropertySettingsValidation:
    """Property 5: Settings Input Validation.

    For any loop control setting with a defined valid range, attempting to
    set a value outside that range SHALL be rejected or clamped to the
    valid range.

    **Validates: Requirements 3.4**
    """

    @settings(max_examples=25)
    @given(st.integers(min_value=-1000, max_value=0))
    def test_poll_interval_clamps_to_minimum(self, value: int):
        """Poll interval values below 1 are clamped to 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_poll_interval(value)
                result = get_poll_interval()
                assert result >= 1, f"Expected >= 1, got {result}"

    @settings(max_examples=25)
    @given(st.integers(min_value=-1000, max_value=-1))
    def test_max_iterations_clamps_to_minimum(self, value: int):
        """Max iterations values below 0 are clamped to 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_max_iterations(value)
                result = get_max_iterations()
                assert result >= 0, f"Expected >= 0, got {result}"

    @settings(max_examples=25)
    @given(st.integers(min_value=-1000, max_value=0))
    def test_max_turns_clamps_to_minimum(self, value: int):
        """Max turns values below 1 are clamped to 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_max_turns(value)
                result = get_max_turns()
                assert result >= 1, f"Expected >= 1, got {result}"

    @settings(max_examples=25)
    @given(st.integers(min_value=-1000, max_value=-1))
    def test_doc_retention_days_clamps_to_minimum(self, value: int):
        """Doc retention days values below 0 are clamped to 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                set_doc_retention_days(value)
                result = get_doc_retention_days()
                assert result >= 0, f"Expected >= 0, got {result}"

    @settings(max_examples=25)
    @given(st.text(min_size=1, max_size=50).filter(lambda x: x not in ["current", "other"]))
    def test_commit_branch_mode_rejects_invalid(self, value: str):
        """Commit branch mode rejects invalid values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch("bentwookie.settings.get_settings_path", return_value=settings_path):
                try:
                    set_commit_branch_mode(value)
                    # If no exception, the value should still be valid (current or other)
                    result = get_commit_branch_mode()
                    assert result in ["current", "other"], f"Invalid mode accepted: {value}"
                except ValueError:
                    # Expected behavior - invalid mode rejected
                    pass
