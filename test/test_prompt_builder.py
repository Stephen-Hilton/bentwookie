"""Tests for prompt building utilities."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from bentwookie.config import init_config, reset_config
from bentwookie.core import create_task_file
from bentwookie.prompt_builder import (
    generate_loop_name,
    sanitize_loop_name,
    substitute_placeholders,
)


@pytest.fixture
def temp_tasks_dir():
    """Create a temporary tasks directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_path = Path(tmpdir) / "tasks"
        tasks_path.mkdir()

        # Create stage directories
        for stage in ["1plan", "2dev", "3test", "4deploy", "5validate", "9done"]:
            (tasks_path / stage).mkdir()
            resources = tasks_path / stage / ".resources"
            resources.mkdir()

        # Create global directory
        global_dir = tasks_path / "global"
        global_dir.mkdir()

        # Initialize config with temp directory
        reset_config()
        init_config(tasks_path=tasks_path, test_mode=True)

        yield tasks_path

        reset_config()


@pytest.fixture
def sample_task(temp_tasks_dir):
    """Create a sample task."""
    return {
        "name": "Test Feature",
        "status": "Ready",
        "change_type": "New Feature",
        "project_phase": "MVP",
        "priority": 5,
        "stage": "1plan",
        "last_updated": "2024-01-15T10:30:00",
        "file_paths": {
            "project_root": "./",
            "tasks": str(temp_tasks_dir),
            "task": str(temp_tasks_dir / "1plan" / "test-feature.md"),
        },
        "infrastructure": {
            "compute": "AWS Lambda",
            "storage": "AWS DynamoDB",
            "queue": "AWS Kinesis",
            "access": "API Gateway",
        },
        "errors": [],
        "body": "Test body content",
        "file_path": str(temp_tasks_dir / "1plan" / "test-feature.md"),
    }


class TestSubstitutePlaceholders:
    """Tests for substitute_placeholders function."""

    def test_simple_placeholders(self, sample_task):
        """Test substituting simple placeholders."""
        text = "Task: {name}, Status: {status}"
        result = substitute_placeholders(text, sample_task)

        assert "Task: Test Feature" in result
        assert "Status: Ready" in result

    def test_nested_placeholders(self, sample_task):
        """Test substituting nested placeholders."""
        text = "Compute: {infrastructure.compute}, Root: {file_paths.project_root}"
        result = substitute_placeholders(text, sample_task)

        assert "Compute: AWS Lambda" in result
        assert "Root: ./" in result

    def test_date_placeholders(self, sample_task):
        """Test date/time placeholders."""
        text = "Date: {today}, Time: {now}"
        result = substitute_placeholders(text, sample_task)

        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result

    def test_extra_placeholders(self, sample_task):
        """Test extra placeholder values."""
        text = "Loop: {loopname}, Custom: {custom_key}"
        result = substitute_placeholders(
            text,
            sample_task,
            extra={"loopname": "myloop", "custom_key": "custom_value"},
        )

        assert "Loop: myloop" in result
        assert "Custom: custom_value" in result

    def test_empty_text(self, sample_task):
        """Test with empty text."""
        result = substitute_placeholders("", sample_task)
        assert result == ""

    def test_no_placeholders(self, sample_task):
        """Test text without placeholders."""
        text = "No placeholders here"
        result = substitute_placeholders(text, sample_task)
        assert result == "No placeholders here"

    def test_unknown_placeholder(self, sample_task):
        """Test that unknown placeholders are left as-is."""
        text = "Unknown: {nonexistent_key}"
        result = substitute_placeholders(text, sample_task)
        assert "{nonexistent_key}" in result


class TestGenerateLoopName:
    """Tests for generate_loop_name function."""

    def test_generates_12_chars(self):
        """Test that generated name is 12 characters."""
        name = generate_loop_name()
        assert len(name) == 12

    def test_alphanumeric_only(self):
        """Test that generated name is alphanumeric."""
        name = generate_loop_name()
        assert name.isalnum()

    def test_unique_names(self):
        """Test that generated names are unique."""
        names = [generate_loop_name() for _ in range(100)]
        assert len(set(names)) == 100


class TestSanitizeLoopName:
    """Tests for sanitize_loop_name function."""

    def test_valid_name_unchanged(self):
        """Test that valid names are unchanged."""
        assert sanitize_loop_name("myloop") == "myloop"
        assert sanitize_loop_name("my_loop") == "my_loop"
        assert sanitize_loop_name("my-loop") == "my-loop"
        assert sanitize_loop_name("loop123") == "loop123"

    def test_removes_special_chars(self):
        """Test that special characters are removed."""
        assert sanitize_loop_name("my loop!") == "myloop"
        assert sanitize_loop_name("loop@#$%") == "loop"
        assert sanitize_loop_name("test/path") == "testpath"

    def test_empty_generates_new(self):
        """Test that empty name generates a new one."""
        result = sanitize_loop_name("")
        assert len(result) == 12
        assert result.isalnum()

    def test_all_special_generates_new(self):
        """Test that all-special-char name generates a new one."""
        result = sanitize_loop_name("!@#$%")
        assert len(result) == 12
        assert result.isalnum()


class TestWhitespacePrompt:
    """Tests for whitespace_prompt function."""

    @pytest.mark.skip(reason="whitespace functions may call subprocesses that hang in CI")
    def test_whitespace_prompt_returns_string(self):
        """Test whitespace_prompt returns a string."""
        from bentwookie.prompt_builder import whitespace_prompt

        result = whitespace_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skip(reason="whitespace functions may call subprocesses that hang in CI")
    def test_whitespace_prompt_contains_results(self):
        """Test whitespace_prompt includes function results."""
        from bentwookie.prompt_builder import whitespace_prompt

        result = whitespace_prompt()
        # Should contain some indication of what was run
        assert len(result) > 10


class TestBuildFinalPrompt:
    """Tests for build_final_prompt function."""

    def test_build_final_prompt_with_task(self, temp_tasks_dir, sample_task):
        """Test building prompt from task dict."""
        from bentwookie.prompt_builder import build_final_prompt
        from bentwookie.core import create_task_file

        # Create a task file
        task_path = create_task_file("Test Feature", stage="1plan")
        task = {"name": "Test Feature", "stage": "1plan", "file_path": task_path}

        result = build_final_prompt(task)
        assert isinstance(result, str)

    def test_build_final_prompt_with_path(self, temp_tasks_dir):
        """Test building prompt from file path."""
        from bentwookie.prompt_builder import build_final_prompt
        from bentwookie.core import create_task_file

        # Create a task file
        task_path = create_task_file("Path Test", stage="1plan")

        result = build_final_prompt(task_path)
        assert isinstance(result, str)

    def test_build_final_prompt_with_string_path(self, temp_tasks_dir):
        """Test building prompt from string path."""
        from bentwookie.prompt_builder import build_final_prompt
        from bentwookie.core import create_task_file

        # Create a task file
        task_path = create_task_file("String Path Test", stage="1plan")

        result = build_final_prompt(str(task_path))
        assert isinstance(result, str)


class TestNextPrompt:
    """Tests for next_prompt function."""

    def test_next_prompt_returns_string(self, temp_tasks_dir):
        """Test next_prompt returns a string."""
        from bentwookie.prompt_builder import next_prompt

        # Without any tasks, should return whitespace prompt
        result = next_prompt()
        assert isinstance(result, str)

    def test_next_prompt_with_loop_name(self, temp_tasks_dir):
        """Test next_prompt with loop name."""
        from bentwookie.prompt_builder import next_prompt

        result = next_prompt(loop_name="test_loop")
        assert isinstance(result, str)
