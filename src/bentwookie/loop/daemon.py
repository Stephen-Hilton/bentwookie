"""BentWookie daemon for continuous request processing."""

import asyncio
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

from ..constants import DAEMON_POLL_INTERVAL
from ..db import init_db, queries
from ..logging_util import get_logger, init_logger
from ..models import DaemonStatus
from ..settings import get_max_iterations, get_poll_interval, is_loop_paused
from .phases import cleanup_old_docs
from .processor import get_rate_limit_wait, is_rate_limited, process_request


class BentWookieDaemon:
    """Main daemon class for processing requests."""

    def __init__(
        self,
        poll_interval: int = DAEMON_POLL_INTERVAL,
        log_path: str | None = None,
        loop_name: str = "bwloop",
        debug: bool = False,
    ):
        """Initialize the daemon.

        Args:
            poll_interval: Seconds between polling for new requests.
            log_path: Path pattern for log file.
            loop_name: Name identifier for this loop instance.
            debug: If True, enable debug-level logging.
        """
        import logging
        self.poll_interval = poll_interval
        self.loop_name = loop_name
        self.running = False
        self.status = DaemonStatus()

        # Initialize logging with appropriate level
        log_level = logging.DEBUG if debug else logging.INFO
        init_logger(log_path=log_path, loop_name=loop_name, level=log_level)
        self.logger = get_logger()

        # Log startup info
        self.logger.info(f"Initializing daemon (debug={debug})")

    async def run(self) -> None:
        """Run the main daemon loop."""
        self.running = True
        self.status.running = True
        self.status.started_at = datetime.now()

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown)

        self.logger.info(f"BentWookie daemon started (loop: {self.loop_name})")
        self.logger.info(f"Poll interval: {self.poll_interval}s")
        self.logger.info(f"Working directory: {os.getcwd()}")
        self.logger.info(f"PID: {os.getpid()}")

        # Ensure database is initialized
        try:
            init_db()
            self.logger.info("Database initialized")
        except Exception as e:
            self.logger.exception(f"Failed to initialize database: {e}")
            raise

        # Clean up old docs at startup
        try:
            cleanup_old_docs()
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old docs: {e}")

        # Check if Claude Agent SDK is available
        try:
            from claude_agent_sdk import query  # noqa: F401
            self.logger.info("Claude Agent SDK available")
        except ImportError:
            self.logger.error(
                "Claude Agent SDK not installed! "
                "Install with: pip install claude-agent-sdk"
            )
            # Continue anyway - processor will handle this gracefully

        while self.running:
            try:
                # Reload poll interval dynamically from settings
                current_poll = get_poll_interval()
                if current_poll != self.poll_interval:
                    self.logger.info(f"Poll interval changed: {self.poll_interval}s -> {current_poll}s")
                    self.poll_interval = current_poll

                # Check if loop is paused
                if is_loop_paused():
                    if not self.status.paused:
                        self.logger.info("Loop paused")
                        self.status.paused = True
                    await asyncio.sleep(self.poll_interval)
                    continue
                elif self.status.paused:
                    self.logger.info("Loop resumed")
                    self.status.paused = False

                # Check max iterations
                max_iter = get_max_iterations()
                if max_iter > 0 and self.status.iteration_count >= max_iter:
                    self.logger.info(f"Max iterations ({max_iter}) reached. Stopping daemon.")
                    break

                # Check if rate limited
                if is_rate_limited():
                    wait_time = get_rate_limit_wait()
                    self.logger.info(f"Rate limited. Waiting {wait_time:.0f}s before next request...")
                    await asyncio.sleep(min(wait_time, self.poll_interval))
                    continue

                # Get next request to process
                request = queries.get_next_request()

                if request:
                    self.status.current_request_id = request["reqid"]
                    self.status.current_phase = request["reqphase"]
                    self.status.last_activity = datetime.now()

                    self.logger.info(
                        f"Processing request {request['reqid']}: "
                        f"{request['reqname']} ({request['reqphase']})"
                    )

                    success = await process_request(request)

                    # Track iteration count
                    self.status.iteration_count += 1

                    if success:
                        self.status.requests_processed += 1
                    else:
                        self.status.errors_count += 1

                    self.status.current_request_id = None
                    self.status.current_phase = None

                else:
                    # No requests pending, sleep
                    self.logger.debug("No pending requests, sleeping...")
                    await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                self.logger.info("Daemon cancelled")
                break

            except Exception as e:
                self.logger.exception(f"Error in daemon loop: {e}")
                self.status.errors_count += 1
                # Sleep before retrying to avoid tight error loops
                await asyncio.sleep(self.poll_interval)

        self._cleanup()

    def _shutdown(self) -> None:
        """Handle shutdown signal."""
        self.logger.info("Shutdown signal received")
        self.running = False
        self.status.running = False

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        self._shutdown()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self.logger.info(
            f"Daemon stopped. Processed: {self.status.requests_processed}, "
            f"Errors: {self.status.errors_count}"
        )

    def get_status(self) -> DaemonStatus:
        """Get current daemon status.

        Returns:
            DaemonStatus object.
        """
        return self.status


# Global daemon instance for signal handling
_daemon: BentWookieDaemon | None = None


def start_daemon(
    poll_interval: int = DAEMON_POLL_INTERVAL,
    log_path: str | None = None,
    loop_name: str = "bwloop",
    foreground: bool = True,
    debug: bool = False,
) -> bool:
    """Start the BentWookie daemon.

    Args:
        poll_interval: Seconds between polling for requests.
        log_path: Path pattern for log file.
        loop_name: Name identifier for this loop.
        foreground: If True, run in foreground; if False, daemonize.
        debug: If True, enable debug logging.

    Returns:
        True if daemon started successfully, False if already running.
    """
    global _daemon

    # Check if daemon is already running (must be BEFORE writing PID file)
    if is_daemon_running():
        pid = read_pid_file()
        print(f"Daemon is already running with PID {pid}")
        return False

    # Use default log path if not specified
    if log_path is None:
        log_path = "logs/{loopname}_{today}.log"

    if not foreground:
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent process - write child PID
            PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            PID_FILE.write_text(str(pid))
            print(f"Daemon started with PID {pid}")
            sys.exit(0)
        # Child process continues

        # Create new session
        os.setsid()

        # Second fork to prevent zombie processes
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        with open("/dev/null") as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())
    else:
        # Foreground mode - write current PID
        write_pid_file()

    try:
        # Create and run daemon
        _daemon = BentWookieDaemon(
            poll_interval=poll_interval,
            log_path=log_path,
            loop_name=loop_name,
            debug=debug,
        )

        asyncio.run(_daemon.run())
        return True
    except Exception as e:
        print(f"Daemon failed to start: {e}")
        remove_pid_file()
        raise
    finally:
        # Clean up PID file when daemon exits
        remove_pid_file()


def stop_daemon() -> bool:
    """Stop the running daemon.

    Returns:
        True if daemon was stopped, False if not running.
    """
    global _daemon

    # Check if we have a local daemon instance
    if _daemon:
        _daemon._shutdown()
        return True

    # Check if external daemon process is running
    if not is_daemon_running():
        return False

    pid = read_pid_file()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            remove_pid_file()
            return True
        except OSError:
            return False

    return False


def get_daemon_status() -> DaemonStatus | None:
    """Get the current daemon status.

    Returns:
        DaemonStatus if daemon is running, None otherwise.
    """
    if _daemon:
        return _daemon.get_status()
    return None


# PID file management for external process control
PID_FILE = Path("data/bentwookie.pid")


def write_pid_file() -> None:
    """Write current PID to file."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def read_pid_file() -> int | None:
    """Read PID from file.

    Returns:
        PID if file exists, None otherwise.
    """
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def remove_pid_file() -> None:
    """Remove PID file."""
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_daemon_running() -> bool:
    """Check if daemon is running.

    Returns:
        True if daemon process is running.
    """
    pid = read_pid_file()
    if pid is None:
        return False

    try:
        os.kill(pid, 0)  # Check if process exists
        return True
    except OSError:
        # Process doesn't exist, clean up stale PID file
        remove_pid_file()
        return False
