"""Custom logging utilities for BentWookie."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class BWLogger:
    """Custom logger with placeholder substitution support.

    Supports placeholders like {today}, {now}, {loopname} in log messages
    and log file paths.
    """

    def __init__(
        self,
        name: str = "bentwookie",
        level: int = logging.INFO,
        log_path: str | None = None,
        loop_name: str | None = None,
    ):
        """Initialize the logger.

        Args:
            name: Logger name
            level: Logging level
            log_path: Path pattern for log file (supports placeholders)
            loop_name: Name of the current loop (for {loopname} placeholder)
        """
        self._name = name
        self._level = level
        self._log_path_pattern = log_path
        self._loop_name = loop_name or "default"
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._file_handler: logging.FileHandler | None = None

        # Set up console handler
        if not self._logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

        # Set up file handler if path provided
        if log_path:
            self._setup_file_handler(log_path)

    def _get_placeholders(self) -> dict[str, str]:
        """Get current placeholder values.

        Returns:
            Dictionary of placeholder names to values
        """
        now = datetime.now()
        return {
            "today": now.strftime("%Y-%m-%d"),
            "now": now.strftime("%Y-%m-%d_%H-%M-%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H-%M-%S"),
            "datetime": now.strftime("%Y-%m-%d_%H-%M-%S"),
            "year": now.strftime("%Y"),
            "month": now.strftime("%m"),
            "day": now.strftime("%d"),
            "hour": now.strftime("%H"),
            "minute": now.strftime("%M"),
            "loopname": self._loop_name,
            "loop_name": self._loop_name,
        }

    def substitute_placeholders(self, text: str, extra: dict[str, Any] | None = None) -> str:
        """Substitute placeholders in text.

        Args:
            text: Text containing {placeholder} patterns
            extra: Additional placeholder values

        Returns:
            Text with placeholders substituted
        """
        placeholders = self._get_placeholders()
        if extra:
            placeholders.update({str(k): str(v) for k, v in extra.items()})

        result = text
        for key, value in placeholders.items():
            result = result.replace(f"{{{key}}}", value)

        return result

    def _setup_file_handler(self, log_path: str) -> None:
        """Set up file handler with placeholder substitution.

        Args:
            log_path: Path pattern for log file or directory
        """
        # Remove existing file handler
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()

        # Substitute placeholders in path
        resolved_path = self.substitute_placeholders(log_path)
        log_file = Path(resolved_path)

        # If path is a directory (or ends with /), generate a log filename
        if log_file.is_dir() or str(log_path).endswith("/"):
            log_file.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = log_file / f"bentwookie_{timestamp}.log"
        else:
            # Create parent directories
            log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler
        self._file_handler = logging.FileHandler(log_file, encoding="utf-8")
        self._file_handler.setLevel(self._level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)

    def set_loop_name(self, loop_name: str) -> None:
        """Update the loop name.

        Args:
            loop_name: New loop name
        """
        self._loop_name = loop_name
        # Re-setup file handler with new loop name
        if self._log_path_pattern:
            self._setup_file_handler(self._log_path_pattern)

    def set_log_path(self, log_path: str) -> None:
        """Update the log file path.

        Args:
            log_path: New log path pattern
        """
        self._log_path_pattern = log_path
        self._setup_file_handler(log_path)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with placeholder substitution."""
        self._logger.debug(self.substitute_placeholders(msg), *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with placeholder substitution."""
        self._logger.info(self.substitute_placeholders(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with placeholder substitution."""
        self._logger.warning(self.substitute_placeholders(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with placeholder substitution."""
        self._logger.error(self.substitute_placeholders(msg), *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message with placeholder substitution."""
        self._logger.critical(self.substitute_placeholders(msg), *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception message with placeholder substitution."""
        self._logger.exception(self.substitute_placeholders(msg), *args, **kwargs)


# Global logger instance
_logger: BWLogger | None = None


def get_logger() -> BWLogger:
    """Get the global logger instance.

    Returns:
        Global BWLogger instance
    """
    global _logger
    if _logger is None:
        _logger = BWLogger()
    return _logger


def init_logger(
    name: str = "bentwookie",
    level: int = logging.INFO,
    log_path: str | None = None,
    loop_name: str | None = None,
) -> BWLogger:
    """Initialize the global logger.

    Args:
        name: Logger name
        level: Logging level
        log_path: Path pattern for log file
        loop_name: Name of the current loop

    Returns:
        Initialized BWLogger instance
    """
    global _logger
    _logger = BWLogger(
        name=name,
        level=level,
        log_path=log_path,
        loop_name=loop_name,
    )
    return _logger


def reset_logger() -> None:
    """Reset the global logger (mainly for testing)."""
    global _logger
    _logger = None
