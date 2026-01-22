"""Tests for logging_util module."""

import pytest
import logging
from pathlib import Path
import tempfile
from datetime import datetime

from bentwookie import logging_util


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset the global logger before each test."""
    logging_util.reset_logger()
    yield
    logging_util.reset_logger()


class TestBWLogger:
    """Tests for BWLogger class."""

    def test_create_logger(self):
        """Test creating a logger."""
        logger = logging_util.BWLogger(name="test")
        assert logger is not None

    def test_logger_with_log_path(self):
        """Test creating a logger with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = logging_util.BWLogger(name="file_test", log_path=str(log_file))

            logger.info("Test message")

            # Force flush
            for handler in logger._logger.handlers:
                handler.flush()

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content

    def test_logger_creates_directory(self):
        """Test logger creates log directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir" / "test.log"
            logger = logging_util.BWLogger(name="dir_test", log_path=str(log_path))

            logger.info("Test")

            for handler in logger._logger.handlers:
                handler.flush()

            assert log_path.parent.exists()

    def test_logger_with_directory_path(self):
        """Test logger with directory path generates filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = logging_util.BWLogger(name="auto_name", log_path=tmpdir + "/")

            logger.info("Test")

            for handler in logger._logger.handlers:
                handler.flush()

            # Should have created a file with timestamp
            log_files = list(Path(tmpdir).glob("*.log"))
            assert len(log_files) == 1
            assert "bentwookie_" in log_files[0].name


class TestPlaceholders:
    """Tests for placeholder substitution."""

    def test_substitute_today(self):
        """Test {today} placeholder."""
        logger = logging_util.BWLogger()
        result = logger.substitute_placeholders("{today}")

        today = datetime.now().strftime("%Y-%m-%d")
        assert result == today

    def test_substitute_loopname(self):
        """Test {loopname} placeholder."""
        logger = logging_util.BWLogger(loop_name="myloop")
        result = logger.substitute_placeholders("{loopname}")

        assert result == "myloop"

    def test_substitute_multiple(self):
        """Test multiple placeholders."""
        logger = logging_util.BWLogger(loop_name="test")
        result = logger.substitute_placeholders("Loop: {loopname}, Date: {today}")

        assert "Loop: test" in result
        assert datetime.now().strftime("%Y-%m-%d") in result

    def test_substitute_extra_placeholders(self):
        """Test extra placeholders."""
        logger = logging_util.BWLogger()
        result = logger.substitute_placeholders("{custom}", extra={"custom": "value"})

        assert result == "value"

    def test_substitute_unknown_unchanged(self):
        """Test unknown placeholders are left unchanged."""
        logger = logging_util.BWLogger()
        result = logger.substitute_placeholders("{unknown}")

        assert result == "{unknown}"

    def test_get_placeholders(self):
        """Test _get_placeholders returns expected keys."""
        logger = logging_util.BWLogger(loop_name="test")
        placeholders = logger._get_placeholders()

        assert "today" in placeholders
        assert "loopname" in placeholders
        assert "datetime" in placeholders
        assert "year" in placeholders
        assert "month" in placeholders
        assert "day" in placeholders


class TestLoggingMethods:
    """Tests for logging methods."""

    def test_debug_method(self):
        """Test debug logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "debug.log"
            logger = logging_util.BWLogger(
                name="debug_test",
                log_path=str(log_file),
                level=logging.DEBUG
            )

            logger.debug("Debug message")

            for handler in logger._logger.handlers:
                handler.flush()

            content = log_file.read_text()
            assert "Debug message" in content

    def test_info_method(self):
        """Test info logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "info.log"
            logger = logging_util.BWLogger(name="info_test", log_path=str(log_file))

            logger.info("Info message")

            for handler in logger._logger.handlers:
                handler.flush()

            content = log_file.read_text()
            assert "Info message" in content

    def test_warning_method(self):
        """Test warning logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "warning.log"
            logger = logging_util.BWLogger(name="warn_test", log_path=str(log_file))

            logger.warning("Warning message")

            for handler in logger._logger.handlers:
                handler.flush()

            content = log_file.read_text()
            assert "Warning message" in content

    def test_error_method(self):
        """Test error logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "error.log"
            logger = logging_util.BWLogger(name="error_test", log_path=str(log_file))

            logger.error("Error message")

            for handler in logger._logger.handlers:
                handler.flush()

            content = log_file.read_text()
            assert "Error message" in content

    def test_critical_method(self):
        """Test critical logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "critical.log"
            logger = logging_util.BWLogger(name="crit_test", log_path=str(log_file))

            logger.critical("Critical message")

            for handler in logger._logger.handlers:
                handler.flush()

            content = log_file.read_text()
            assert "Critical message" in content


class TestLoggerConfiguration:
    """Tests for logger configuration methods."""

    def test_set_loop_name(self):
        """Test setting loop name."""
        logger = logging_util.BWLogger(loop_name="original")
        assert logger._loop_name == "original"

        logger.set_loop_name("updated")
        assert logger._loop_name == "updated"

    def test_set_log_path(self):
        """Test setting log path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = logging_util.BWLogger(name="path_change")

            new_path = Path(tmpdir) / "new.log"
            logger.set_log_path(str(new_path))

            logger.info("After path change")

            for handler in logger._logger.handlers:
                handler.flush()

            assert new_path.exists()


class TestGlobalLogger:
    """Tests for global logger functions."""

    def test_get_logger_creates_default(self):
        """Test get_logger creates a default logger."""
        logger = logging_util.get_logger()
        assert logger is not None

    def test_get_logger_returns_same_instance(self):
        """Test get_logger returns the same instance."""
        logger1 = logging_util.get_logger()
        logger2 = logging_util.get_logger()
        assert logger1 is logger2

    def test_init_logger(self):
        """Test init_logger creates a configured logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "init.log"
            logger = logging_util.init_logger(
                name="init_test",
                log_path=str(log_path),
                loop_name="myloop"
            )

            assert logger._loop_name == "myloop"

    def test_init_logger_replaces_global(self):
        """Test init_logger replaces the global logger."""
        logger1 = logging_util.get_logger()

        with tempfile.TemporaryDirectory() as tmpdir:
            logger2 = logging_util.init_logger(
                name="replacement",
                log_path=str(Path(tmpdir) / "log.log")
            )

            logger3 = logging_util.get_logger()

            assert logger3 is logger2
            assert logger3 is not logger1

    def test_reset_logger(self):
        """Test reset_logger clears global logger."""
        logging_util.get_logger()  # Create a logger
        logging_util.reset_logger()

        # After reset, get_logger should create a new one
        assert logging_util._logger is None
