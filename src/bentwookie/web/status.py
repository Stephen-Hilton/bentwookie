"""Web server status utilities for BentWookie."""

import socket
import urllib.request
import urllib.error
import json
from typing import Any

from ..settings import get_web_host, get_web_port


def is_web_server_running(host: str | None = None, port: int | None = None) -> bool:
    """Check if the BentWookie web server is responding on the given host and port.

    This function checks the /health endpoint to verify it's actually BentWookie
    and not some other service (like macOS AirPlay Receiver on port 5000).

    Args:
        host: Host address to check (defaults to configured web_host)
        port: Port to check (defaults to configured web_port)

    Returns:
        True if BentWookie server is responding, False otherwise
    """
    if host is None:
        host = get_web_host()
    if port is None:
        port = get_web_port()

    try:
        url = f"http://{host}:{port}/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                # Verify it's actually BentWookie
                return data.get("service") == "bentwookie"
    except (urllib.error.URLError, urllib.error.HTTPError, socket.error, OSError, json.JSONDecodeError):
        pass
    return False


def get_web_server_pid() -> int | None:
    """Get the PID of the running web server if detectable.

    Note: This is a best-effort function. The web server PID may not
    be easily detectable without additional infrastructure.

    Returns:
        PID if detectable, None otherwise
    """
    # The Flask development server doesn't provide an easy way to get its PID
    # In production, this would typically be managed by a process manager
    # For now, return None as we don't have a reliable way to detect it
    return None


def get_web_status() -> dict[str, Any]:
    """Get comprehensive web server status.

    Returns:
        Dict with keys:
        - running: bool - whether server is responding
        - host: str - configured host address
        - port: int - configured port
        - pid: int | None - server PID if detectable
        - url: str - full URL to access the server
    """
    host = get_web_host()
    port = get_web_port()
    running = is_web_server_running(host, port)
    pid = get_web_server_pid() if running else None

    # Build URL
    url = f"http://{host}:{port}"

    return {
        "running": running,
        "host": host,
        "port": port,
        "pid": pid,
        "url": url,
    }
