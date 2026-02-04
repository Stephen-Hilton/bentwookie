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


class TestPidOperations:
    """Tests for PID database operations."""

    def test_write_pid(self, temp_db):
        """Test writing PID to database."""
        daemon.write_pid("test_loop")

        pid = daemon.read_pid()
        assert pid == os.getpid()

    def test_read_pid(self, temp_db):
        """Test reading PID from database."""
        from bentwookie.db import set_daemon_pid
        set_daemon_pid(12345, "test_loop")

        pid = daemon.read_pid()
        assert pid == 12345

    def test_read_pid_not_set(self, temp_db):
        """Test reading PID when not set."""
        pid = daemon.read_pid()
        assert pid is None

    def test_clear_pid(self, temp_db):
        """Test clearing PID from database."""
        daemon.write_pid("test_loop")
        assert daemon.read_pid() is not None

        daemon.clear_pid()
        assert daemon.read_pid() is None

    def test_legacy_aliases(self, temp_db):
        """Test legacy function aliases work."""
        daemon.write_pid_file()
        assert daemon.read_pid_file() == os.getpid()

        daemon.remove_pid_file()
        assert daemon.read_pid_file() is None


class TestIsDaemonRunning:
    """Tests for is_daemon_running function."""

    def test_daemon_not_running_no_pid(self, temp_db):
        """Test daemon not running when no PID set."""
        result = daemon.is_daemon_running()
        assert result is False

    def test_daemon_not_running_stale_pid(self, temp_db):
        """Test daemon not running with stale PID."""
        from bentwookie.db import set_daemon_pid
        # Write a PID that definitely doesn't exist
        set_daemon_pid(999999999, "test_loop")

        result = daemon.is_daemon_running()
        assert result is False

    def test_daemon_running_valid_pid(self, temp_db):
        """Test daemon running with valid PID (current process)."""
        from bentwookie.db import set_daemon_pid
        set_daemon_pid(os.getpid(), "test_loop")

        result = daemon.is_daemon_running()
        assert result is True


class TestBentWookieDaemon:
    """Tests for BentWookieDaemon class."""

    def test_daemon_init(self, temp_db):
        """Test daemon initialization."""
        d = daemon.BentWookieDaemon()
        assert d is not None

    def test_daemon_init_with_options(self, temp_db):
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

    def test_daemon_run_initialization(self, temp_db, monkeypatch):
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

    def test_daemon_stop(self, temp_db):
        """Test daemon stop method."""
        d = daemon.BentWookieDaemon()
        d.running = True

        d.stop()
        assert d.running is False


class TestStartDaemon:
    """Tests for start_daemon function."""

    def test_start_daemon_already_running(self, temp_db, monkeypatch):
        """Test start_daemon when daemon is already running."""
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: True)
        monkeypatch.setattr(daemon, "read_pid", lambda: 12345)

        result = daemon.start_daemon()
        assert result is False

    @patch("os.fork")
    def test_start_daemon_background(self, mock_fork, temp_db, monkeypatch):
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

    def test_stop_daemon_not_running(self, temp_db, monkeypatch):
        """Test stop_daemon when daemon is not running."""
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: False)

        result = daemon.stop_daemon()
        assert result is False

    @patch("os.kill")
    def test_stop_daemon_running(self, mock_kill, temp_db, monkeypatch):
        """Test stop_daemon when daemon is running."""
        from bentwookie.db import set_daemon_pid
        set_daemon_pid(12345, "test_loop")
        monkeypatch.setattr(daemon, "is_daemon_running", lambda: True)
        monkeypatch.setattr(daemon, "read_pid", lambda: 12345)

        result = daemon.stop_daemon()
        assert result is True
        mock_kill.assert_called()
