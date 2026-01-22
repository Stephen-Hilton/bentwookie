"""Tests for CLI interface (v2)."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from bentwookie.cli import main
from bentwookie.db.connection import set_db_path, get_db_path


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir):
    """Set up a temporary database."""
    db_path = temp_dir / "test.db"
    original_path = get_db_path()
    set_db_path(db_path)
    yield db_path
    set_db_path(original_path)


class TestMainHelp:
    """Tests for main help output."""

    def test_help_option(self, runner):
        """Test --help shows usage."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "BentWookie" in result.output
        assert "init" in result.output
        assert "project" in result.output
        assert "request" in result.output
        assert "loop" in result.output

    def test_no_args_shows_help(self, runner):
        """Test no arguments shows help."""
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "BentWookie" in result.output


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_database(self, runner, temp_dir):
        """Test init creates database and directories."""
        db_path = temp_dir / "data" / "bw.db"
        result = runner.invoke(main, ["init", "--db-path", str(db_path), "--auth", "max"])

        assert result.exit_code == 0
        assert "Database initialized" in result.output


class TestProjectCommands:
    """Tests for project subcommands."""

    def test_project_create(self, runner, temp_db):
        """Test project create command."""
        # Initialize DB first
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        result = runner.invoke(main, ["project", "create", "testproject", "-d", "Test desc"])
        assert result.exit_code == 0
        assert "Project created" in result.output
        assert "testproject" in result.output

    def test_project_list_empty(self, runner, temp_db):
        """Test project list with no projects."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        result = runner.invoke(main, ["project", "list"])
        assert result.exit_code == 0
        assert "No projects found" in result.output

    def test_project_list_with_projects(self, runner, temp_db):
        """Test project list with projects."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])

        result = runner.invoke(main, ["project", "list"])
        assert result.exit_code == 0
        assert "testproject" in result.output

    def test_project_show(self, runner, temp_db):
        """Test project show command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject", "-d", "My test project"])

        result = runner.invoke(main, ["project", "show", "testproject"])
        assert result.exit_code == 0
        assert "testproject" in result.output
        assert "My test project" in result.output

    def test_project_show_not_found(self, runner, temp_db):
        """Test project show with non-existent project."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        result = runner.invoke(main, ["project", "show", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_project_delete(self, runner, temp_db):
        """Test project delete command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])

        result = runner.invoke(main, ["project", "delete", "testproject", "--force"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()

    def test_project_create_duplicate(self, runner, temp_db):
        """Test creating duplicate project fails."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])

        result = runner.invoke(main, ["project", "create", "testproject"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestRequestCommands:
    """Tests for request subcommands."""

    def test_request_create(self, runner, temp_db):
        """Test request create command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])

        result = runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "Test Request",
            "-m", "Implement something cool"
        ])
        assert result.exit_code == 0
        assert "Request created" in result.output
        assert "plan" in result.output.lower()
        assert "tbd" in result.output

    def test_request_create_no_project(self, runner, temp_db):
        """Test request create with non-existent project."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        result = runner.invoke(main, [
            "request", "create", "nonexistent",
            "-n", "Test Request",
            "-m", "Implement something"
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_request_list_empty(self, runner, temp_db):
        """Test request list with no requests."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        result = runner.invoke(main, ["request", "list"])
        assert result.exit_code == 0
        assert "No requests found" in result.output

    def test_request_list_with_requests(self, runner, temp_db):
        """Test request list with requests."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])
        runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "My Request",
            "-m", "Do something"
        ])

        result = runner.invoke(main, ["request", "list"])
        assert result.exit_code == 0
        assert "My Request" in result.output

    def test_request_show(self, runner, temp_db):
        """Test request show command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])
        runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "My Request",
            "-m", "Do something amazing"
        ])

        result = runner.invoke(main, ["request", "show", "1"])
        assert result.exit_code == 0
        assert "My Request" in result.output
        assert "Do something amazing" in result.output

    def test_request_update_status(self, runner, temp_db):
        """Test request update status command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])
        runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "My Request",
            "-m", "Do something"
        ])

        result = runner.invoke(main, ["request", "update", "1", "--status", "wip"])
        assert result.exit_code == 0
        assert "In Progress" in result.output or "wip" in result.output.lower()

    def test_request_update_phase(self, runner, temp_db):
        """Test request update phase command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])
        runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "My Request",
            "-m", "Do something"
        ])

        result = runner.invoke(main, ["request", "update", "1", "--phase", "dev"])
        assert result.exit_code == 0
        assert "Development" in result.output or "dev" in result.output.lower()

    def test_request_delete(self, runner, temp_db):
        """Test request delete command."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])
        runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "My Request",
            "-m", "Do something"
        ])

        result = runner.invoke(main, ["request", "delete", "1", "--force"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


class TestStatusCommand:
    """Tests for status command."""

    def test_status_empty(self, runner, temp_db):
        """Test status with empty database."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "BentWookie Status" in result.output
        assert "Projects" in result.output
        assert "Requests" in result.output

    def test_status_with_data(self, runner, temp_db):
        """Test status with some data."""
        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])
        runner.invoke(main, ["project", "create", "testproject"])
        runner.invoke(main, [
            "request", "create", "testproject",
            "-n", "My Request",
            "-m", "Do something"
        ])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Projects:   1" in result.output
        assert "Requests:   1" in result.output


class TestLoopCommands:
    """Tests for loop subcommands."""

    def test_loop_status_not_running(self, runner, temp_db, monkeypatch):
        """Test loop status when daemon not running."""
        from bentwookie.loop import daemon

        runner.invoke(main, ["init", "--db-path", str(temp_db), "--auth", "max"])

        # Mock daemon not running
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: False)
        monkeypatch.setattr(daemon, "read_pid_file", lambda: None)

        result = runner.invoke(main, ["loop", "status"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()
