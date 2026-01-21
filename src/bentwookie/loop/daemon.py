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
from .processor import process_request


class BentWookieDaemon:
    """Main daemon class for processing requests."""

    def __init__(
        self,
        poll_interval: int = DAEMON_POLL_INTERVAL,
        log_path: str | None = None,
        loop_name: str = "bwloop",
    ):
        """Initialize the daemon.

        Args:
            poll_interval: Seconds between polling for new requests.
            log_path: Path pattern for log file.
            loop_name: Name identifier for this loop instance.
        """
        self.poll_interval = poll_interval
        self.loop_name = loop_name
        self.running = False
        self.status = DaemonStatus()

        # Initialize logging
        if log_path:
            init_logger(log_path=log_path, loop_name=loop_name)
        self.logger = get_logger()

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

        # Ensure database is initialized
        init_db()

        while self.running:
            try:
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
) -> None:
    """Start the BentWookie daemon.

    Args:
        poll_interval: Seconds between polling for requests.
        log_path: Path pattern for log file.
        loop_name: Name identifier for this loop.
        foreground: If True, run in foreground; if False, daemonize.
    """
    global _daemon

    if not foreground:
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent process
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

    # Create and run daemon
    _daemon = BentWookieDaemon(
        poll_interval=poll_interval,
        log_path=log_path,
        loop_name=loop_name,
    )

    asyncio.run(_daemon.run())


def stop_daemon() -> None:
    """Stop the running daemon."""
    global _daemon
    if _daemon:
        _daemon._shutdown()


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
