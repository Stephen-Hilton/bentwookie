"""Tests for loop/daemon module."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
import os

from bentwookie.loop import daemon
from bentwookie.db import connection


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    connection.set_db_path(db_path)
    connection.init_db()

    yield db_path

    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def temp_pid_file(monkeypatch):
    """Create a temporary directory for PID file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pid_path = Path(tmpdir) / "daemon.pid"
        monkeypatch.setattr(daemon, "PID_FILE", pid_path)
        yield pid_path


class TestPidFileOperations:
    """Tests for PID file operations."""

    def test_write_pid_file(self, temp_pid_file):
        """Test writing PID to file."""
        daemon.write_pid_file()

        assert temp_pid_file.exists()
        pid = int(temp_pid_file.read_text().strip())
        assert pid == os.getpid()

    def test_read_pid_file(self, temp_pid_file):
        """Test reading PID from file."""
        temp_pid_file.write_text("12345")

        pid = daemon.read_pid_file()
        assert pid == 12345

    def test_read_pid_file_not_exists(self, temp_pid_file):
        """Test reading PID when file doesn't exist."""
        pid = daemon.read_pid_file()
        assert pid is None

    def test_read_pid_file_invalid(self, temp_pid_file):
        """Test reading PID when file contains invalid content."""
        temp_pid_file.write_text("not a number")

        pid = daemon.read_pid_file()
        assert pid is None

    def test_remove_pid_file(self, temp_pid_file):
        """Test removing PID file."""
        temp_pid_file.write_text("12345")

        daemon.remove_pid_file()
        assert not temp_pid_file.exists()

    def test_remove_pid_file_not_exists(self, temp_pid_file):
        """Test removing PID file when it doesn't exist."""
        # Should not raise
        daemon.remove_pid_file()


class TestIsDaemonRunning:
    """Tests for is_daemon_running function."""

    def test_daemon_not_running_no_pid_file(self, temp_pid_file):
        """Test daemon not running when no PID file."""
        result = daemon.is_daemon_running()
        assert result is False

    def test_daemon_not_running_stale_pid(self, temp_pid_file):
        """Test daemon not running with stale PID."""
        # Write a PID that definitely doesn't exist
        temp_pid_file.write_text("999999999")

        result = daemon.is_daemon_running()
        assert result is False

    def test_daemon_running_valid_pid(self, temp_pid_file):
        """Test daemon running with valid PID (current process)."""
        temp_pid_file.write_text(str(os.getpid()))

        result = daemon.is_daemon_running()
        assert result is True


class TestBentWookieDaemon:
    """Tests for BentWookieDaemon class."""

    def test_daemon_init(self, temp_db, temp_pid_file):
        """Test daemon initialization."""
        d = daemon.BentWookieDaemon()
        assert d is not None

    def test_daemon_init_with_options(self, temp_db, temp_pid_file):
        """Test daemon initialization with options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "daemon.log"
            d = daemon.BentWookieDaemon(
                log_path=str(log_path),
                loop_name="test_loop",
                poll_interval=10,
            )
            assert d.poll_interval == 10
            assert d.loop_name == "test_loop"

    def test_daemon_run_initialization(self, temp_db, temp_pid_file, monkeypatch):
        """Test daemon run initialization (without actually running the loop)."""
        from bentwookie import settings
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            monkeypatch.setattr(settings, "DEFAULT_SETTINGS_PATH", settings_path)

            d = daemon.BentWookieDaemon()
            # We can't fully run the daemon without more mocking,
            # but we can test initialization
            assert d.running is False
            assert d.poll_interval > 0

    def test_daemon_stop(self, temp_db, temp_pid_file):
        """Test daemon stop method."""
        d = daemon.BentWookieDaemon()
        d.running = True

        d.stop()
        assert d.running is False


class TestStartDaemon:
    """Tests for start_daemon function."""

    def test_start_daemon_already_running(self, temp_pid_file, monkeypatch):
        """Test start_daemon when daemon is already running."""
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: True)
        monkeypatch.setattr(daemon, "read_pid_file", lambda: 12345)

        result = daemon.start_daemon()
        assert result is False

    @patch("os.fork")
    def test_start_daemon_background(self, mock_fork, temp_pid_file, temp_db, monkeypatch):
        """Test start_daemon in background mode."""
        # Simulate parent process
        mock_fork.return_value = 12345

        monkeypatch.setattr(daemon, "is_daemon_running", lambda: False)

        # Parent process exits after forking
        with pytest.raises(SystemExit) as exc_info:
            daemon.start_daemon(foreground=False)
        assert exc_info.value.code == 0


class TestStopDaemon:
    """Tests for stop_daemon function."""

    def test_stop_daemon_not_running(self, temp_pid_file, monkeypatch):
        """Test stop_daemon when daemon is not running."""
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: False)

        result = daemon.stop_daemon()
        assert result is False

    @patch("os.kill")
    def test_stop_daemon_running(self, mock_kill, temp_pid_file, monkeypatch):
        """Test stop_daemon when daemon is running."""
        temp_pid_file.write_text("12345")
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: True)
        monkeypatch.setattr(daemon, "read_pid_file", lambda: 12345)

        result = daemon.stop_daemon()
        assert result is True
        mock_kill.assert_called()
