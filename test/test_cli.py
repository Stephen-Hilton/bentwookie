"""Tests for CLI interface."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from bentwookie.cli import main
from bentwookie.config import reset_config


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def reset_config_fixture():
    """Reset config before and after each test."""
    reset_config()
    yield
    reset_config()


class TestMainHelp:
    """Tests for main help output."""

    def test_help_option(self, runner):
        """Test --help shows usage."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "BentWookie" in result.output
        assert "--init" in result.output
        assert "--plan" in result.output
        assert "--next_prompt" in result.output

    def test_no_args_shows_help(self, runner):
        """Test no arguments shows help."""
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "BentWookie" in result.output


class TestInitCommand:
    """Tests for --init command."""

    def test_init_creates_templates(self, runner, temp_dir):
        """Test --init copies templates."""
        result = runner.invoke(main, ["--init", str(temp_dir)])

        if result.exit_code != 0:
            # If templates don't exist in dev mode, that's expected
            assert "Templates not found" in result.output
        else:
            assert "Templates copied" in result.output
            assert (temp_dir / "tasks").exists()


class TestListCommand:
    """Tests for list subcommand."""

    def test_list_no_tasks(self, runner, temp_dir):
        """Test list with no tasks."""
        # Create minimal task structure
        tasks_path = temp_dir / "tasks"
        tasks_path.mkdir()
        for stage in ["1plan", "2dev", "3test", "4deploy", "5validate", "9done"]:
            (tasks_path / stage).mkdir()
        (tasks_path / "global").mkdir()

        result = runner.invoke(main, ["--tasks", str(tasks_path), "list"])

        assert result.exit_code == 0
        assert "No tasks found" in result.output


class TestMoveStageCommand:
    """Tests for move-stage subcommand."""

    def test_move_stage_requires_task(self, runner):
        """Test move-stage requires --task option."""
        result = runner.invoke(main, ["move-stage"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestUpdateStatusCommand:
    """Tests for update-status subcommand."""

    def test_update_status_requires_task(self, runner):
        """Test update-status requires --task option."""
        result = runner.invoke(main, ["update-status"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_update_status_requires_status(self, runner, temp_dir):
        """Test update-status requires --status option."""
        # Create a dummy file
        task_file = temp_dir / "test.md"
        task_file.write_text("test")

        result = runner.invoke(main, ["update-status", "--task", str(task_file)])
        assert result.exit_code != 0
