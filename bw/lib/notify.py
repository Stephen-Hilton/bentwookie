"""Notification logic for BentWookie."""

import json
import logging
import re
import urllib.request
from pathlib import Path

from bw.lib.config import ContainerConfig

log = logging.getLogger(__name__)


def _load_slack_webhook_url(bw_path: Path) -> str | None:
    """Read SLACK_WEBHOOK_URL from the .env file in the project root.

    Looks for .env in the parent of bw/ (i.e. the project root).
    """
    # bw_path is the bw/ directory; .env lives one level up
    env_file = bw_path.parent / ".env"
    if not env_file.exists():
        log.warning("No .env file found at %s", env_file)
        return None

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("SLACK_WEBHOOK_URL="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            return value if value else None

    log.warning("SLACK_WEBHOOK_URL not found in %s", env_file)
    return None


def _send_slack_message(webhook_url: str, text: str) -> bool:
    """Post a message to Slack via incoming webhook. Returns True on success."""
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log.error("Slack notification failed: %s", e)
        return False


def notify_started(
    workitem_name: str,
    code_path: str,
    container: ContainerConfig,
    bw_path: Path,
) -> None:
    """Send a notification that a workitem has started processing."""
    if container.notify != "slack":
        return

    webhook_url = _load_slack_webhook_url(bw_path)
    if not webhook_url:
        return

    text = f":gear: *{workitem_name}* started on `{container.name}` — {code_path}"
    if _send_slack_message(webhook_url, text):
        log.info("Slack: notified start of %s", workitem_name)


def notify_completed(
    workitem_name: str,
    notification_text: str | None,
    container: ContainerConfig,
    bw_path: Path,
) -> None:
    """Send a notification that a workitem has completed."""
    if container.notify != "slack":
        return

    webhook_url = _load_slack_webhook_url(bw_path)
    if not webhook_url:
        return

    body = notification_text or "No details provided."
    text = f":white_check_mark: *{workitem_name}* completed on `{container.name}`\n{body}"
    if _send_slack_message(webhook_url, text):
        log.info("Slack: notified completion of %s", workitem_name)


def notify_error(
    workitem_name: str,
    error_msg: str,
    container: ContainerConfig,
    bw_path: Path,
) -> None:
    """Send a notification that a workitem has errored."""
    if container.notify != "slack":
        return

    webhook_url = _load_slack_webhook_url(bw_path)
    if not webhook_url:
        return

    # Truncate error for Slack readability
    short_error = error_msg[:300]
    text = f":x: *{workitem_name}* failed on `{container.name}`\n```{short_error}```"
    if _send_slack_message(webhook_url, text):
        log.info("Slack: notified error for %s", workitem_name)


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
