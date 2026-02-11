"""Notification logic for BentWookie (stub implementation)."""

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)


def send_notification(message: str) -> dict:
    """Send a notification. Currently a stub that logs the message.

    Returns a dict with delivery status.
    """
    log.info("Notification (stub): %s", message[:200])
    return {"delivered": True, "type": "stub"}


def extract_notification_from_workitem(path: Path) -> str | None:
    """Parse a workitem file and extract the # NOTIFICATION section content.

    Returns the notification text, or None if no section found.
    """
    if not path.exists():
        return None

    text = path.read_text()
    # Match from '# NOTIFICATION' to the next top-level heading or EOF
    match = re.search(
        r"^# NOTIFICATION\s*\n(.*?)(?=^# |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return None
