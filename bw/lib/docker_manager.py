"""Docker container lifecycle management for BentWookie."""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bw.lib.config import ContainerConfig

log = logging.getLogger(__name__)


@dataclass
class ContainerResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


def build_image(dockerfile_path: Path, image_name: str = "bw:0.3.0", timeout: int = 60) -> bool:
    """Build the Docker image from the Dockerfile.

    Streams output to the console so the user can see progress.
    Returns True on success.
    """
    context = dockerfile_path.parent
    log.info("Building Docker image '%s' from %s", image_name, dockerfile_path)
    try:
        result = subprocess.run(
            ["docker", "build", "--progress=plain", "-t", image_name,
             "-f", str(dockerfile_path), "."],
            cwd=context,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            log.error("Docker build failed (exit code %d)", result.returncode)
            return False
        log.info("Docker image '%s' built successfully", image_name)
        return True
    except subprocess.TimeoutExpired:
        log.error("Docker build timed out after %ds — aborting", timeout)
        return False


def image_exists(image_name: str, retries: int = 3, delay: float = 5.0) -> bool:
    """Check if a Docker image exists locally.

    Retries a few times to handle transient Docker Desktop flakiness
    (e.g. after a long container run finishes).
    """
    import time as _time

    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_name],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return True
            if attempt < retries - 1:
                log.debug("Image '%s' not found (attempt %d/%d), retrying in %.0fs...",
                          image_name, attempt + 1, retries, delay)
                _time.sleep(delay)
        except subprocess.TimeoutExpired:
            log.warning("Docker timed out checking image '%s' (attempt %d/%d)",
                        image_name, attempt + 1, retries)
            if attempt < retries - 1:
                _time.sleep(delay)
    return False


def get_credential_volume_name(container_name: str) -> str:
    """Return the Docker volume name for a container's Claude credentials."""
    return f"bw-creds-{container_name}"


def ensure_credential_volume(container_name: str) -> bool:
    """Create the credential volume if it doesn't exist.

    Returns True on success.
    """
    vol_name = get_credential_volume_name(container_name)
    try:
        result = subprocess.run(
            ["docker", "volume", "create", vol_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            log.info("Volume '%s' ready", vol_name)
            return True
        log.error("Failed to create volume '%s': %s", vol_name, result.stderr)
        return False
    except subprocess.TimeoutExpired:
        log.warning("Docker timed out creating volume '%s' — is Docker running?", vol_name)
        return False


def check_container_status() -> str:
    """Return a brief summary of running BW containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=bentwookie", "--format",
             "table {{.Names}}\t{{.Status}}\t{{.Image}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "No BW containers running"
    except subprocess.TimeoutExpired:
        return "Docker not responding (is it running?)"


def run_workitem(
    workitem_path: Path,
    code_path: Path,
    bw_path: Path,
    container_config: ContainerConfig,
    image_name: str = "bw:0.3.0",
) -> ContainerResult:
    """Run a workitem in an ephemeral Docker container.

    Sends three sequential prompts to Claude Code using --continue:
      1. PREAMBLE — sets context and rules
      2. INSTRUCTIONS — the actual work
      3. FINAL TASKS — post-completion steps (testing, summary, nextsteps)

    Mounts:
      - code_path → /app/project
      - bw_path → /app/bw
      - credential volume → /home/bwuser/.claude
    """
    cred_vol = get_credential_volume_name(container_config.name)
    wip_filename = workitem_path.name

    # Build the multi-step claude command
    model_flag = f"--model {container_config.model}" if container_config.model else ""
    skip_flag = "--dangerously-skip-permissions" if container_config.dangerously_skip_permissions else ""
    flags = f"{model_flag} {skip_flag}".strip()
    log_file = f"/app/bw/logs/{wip_filename}.log"
    wip_file = f"/app/bw/work/wip/{wip_filename}"
    snippets_file = "/app/bw/lib/prompt_snippets.yaml"

    # PREAMBLE and FINAL_TASKS are read from prompt_snippets.yaml at runtime.
    # The workitem file only contains frontmatter + instructions.
    # {workitem.md} in FINAL_TASKS is replaced with the actual wip path.
    max_idle = container_config.max_idle_heartbeats

    claude_cmd = f'''set -eo pipefail
LOG="{log_file}"
WIP="{wip_file}"
FLAGS="{flags}"
SNIPPETS="{snippets_file}"
MAX_IDLE={max_idle}

# Heartbeat + watchdog: monitor log activity, kill stuck claude after MAX_IDLE consecutive idle checks
_bw_heartbeat() {{
    INTERVAL=300
    IDLE_COUNT=0
    while true; do
        sleep "$INTERVAL"
        if [ -f "$LOG" ]; then
            LAST_MOD=$(stat -c %Y "$LOG" 2>/dev/null || stat -f %m "$LOG" 2>/dev/null)
            NOW=$(date +%s)
            IDLE=$(( NOW - LAST_MOD ))
            if [ "$IDLE" -ge "$INTERVAL" ]; then
                IDLE_COUNT=$((IDLE_COUNT + 1))
                if [ "$MAX_IDLE" -gt 0 ] && [ "$IDLE_COUNT" -ge "$MAX_IDLE" ]; then
                    echo "[BW WATCHDOG $(date '+%H:%M:%S')] Idle limit reached ($IDLE_COUNT/$MAX_IDLE heartbeats). Terminating claude process." >> "$LOG"
                    pkill -TERM node 2>/dev/null || true
                    sleep 5
                    pkill -9 node 2>/dev/null || true
                    break
                else
                    echo "[BW HEARTBEAT $(date '+%H:%M:%S')] Log idle for ${{IDLE}}s — container still alive ($IDLE_COUNT/$MAX_IDLE)" >> "$LOG"
                fi
            else
                IDLE_COUNT=0
            fi
        fi
    done
}}
_bw_heartbeat &
BW_HEARTBEAT_PID=$!
trap "kill $BW_HEARTBEAT_PID 2>/dev/null" EXIT

# Status hook: PostToolUse hook that asks Claude for a status update every 5 minutes
cat > /tmp/bw_status_hook.sh << 'HOOKEOF'
#!/bin/bash
NOW=$(date +%s)
LAST=$(cat /tmp/.bw_last_status 2>/dev/null || echo 0)
ELAPSED=$((NOW - LAST))
if [ "$ELAPSED" -ge 300 ]; then
    echo "$NOW" > /tmp/.bw_last_status
    LOG_FILE="__BW_LOG_FILE__"
    python3 -c "
import json, sys
msg = '[BW STATUS CHECK] 5 minutes have passed. Write a 1-sentence status summary by running: echo \\\"[STATUS] <your summary>\\\" | tee -a ' + sys.argv[1] + ''
print(json.dumps({{'hookSpecificOutput': {{'hookEventName': 'PostToolUse', 'additionalContext': msg}}}}))" "$LOG_FILE"
fi
exit 0
HOOKEOF
sed -i "s|__BW_LOG_FILE__|$LOG|g" /tmp/bw_status_hook.sh
chmod +x /tmp/bw_status_hook.sh
date +%s > /tmp/.bw_last_status

# Configure the PostToolUse hook in Claude settings
python3 << 'PYEOF'
import json, os
settings_path = os.path.expanduser("~/.claude/settings.json")
settings = {{}}
if os.path.exists(settings_path):
    try:
        settings = json.loads(open(settings_path).read())
    except Exception:
        pass
settings.setdefault("hooks", {{}})
settings["hooks"]["PostToolUse"] = [
    {{
        "matcher": ".*",
        "hooks": [
            {{
                "type": "command",
                "command": "/tmp/bw_status_hook.sh",
                "timeout": 10000
            }}
        ]
    }}
]
os.makedirs(os.path.dirname(settings_path), exist_ok=True)
open(settings_path, "w").write(json.dumps(settings, indent=2))
PYEOF

# Read PREAMBLE and FINAL_TASKS from prompt_snippets.yaml
# Uses python3 (available in container) for reliable YAML parsing
PREAMBLE=$(python3 -c "import yaml; d=yaml.safe_load(open('$SNIPPETS')); print(d.get('PREAMBLE',''))")
FINAL_TASKS=$(python3 -c "import yaml; d=yaml.safe_load(open('$SNIPPETS')); print(d.get('FINAL_TASKS','').replace('{{workitem.md}}','$WIP'))")

echo "=== STEP 1/3: PREAMBLE ===" | tee "$LOG"
echo "$PREAMBLE" | claude -p "Read this context carefully. These are your operating rules for this session. Acknowledge briefly and wait for instructions." $FLAGS 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== STEP 2/3: INSTRUCTIONS ===" | tee -a "$LOG"
cat "$WIP" | claude -p "Execute these instructions now." --continue $FLAGS 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== STEP 3/3: FINAL TASKS ===" | tee -a "$LOG"
echo "$FINAL_TASKS" | claude -p "Now perform all of these final tasks. Do not stop until every item is complete." --continue $FLAGS 2>&1 | tee -a "$LOG"
'''

    cmd = [
        "docker", "run", "--rm",
        "--label", "bentwookie",
        "--name", f"bw-{container_config.name}-{wip_filename[:20]}",
        "-v", f"{code_path.resolve()}:/app/project",
        "-v", f"{bw_path.resolve()}:/app/bw",
        "-v", f"{cred_vol}:/home/bwuser/.claude",
        "-v", f"{Path.home() / '.aws'}:/home/bwuser/.aws:ro",
        image_name,
        "-c", claude_cmd,
    ]

    timeout = container_config.timeout_seconds

    log.info("Running container for workitem: %s (timeout=%ds, idle_watchdog=%d heartbeats)",
             wip_filename, timeout, max_idle)
    log.debug("Docker command: %s", " ".join(cmd))

    timed_out = False
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ContainerResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as e:
        log.error("Container timed out after %ds for %s", timeout, wip_filename)
        timed_out = True
        # Kill the container
        container_name = f"bw-{container_config.name}-{wip_filename[:20]}"
        subprocess.run(["docker", "kill", container_name], capture_output=True, timeout=15)
        return ContainerResult(
            exit_code=-1,
            stdout=e.stdout or "" if hasattr(e, "stdout") else "",
            stderr=e.stderr or "" if hasattr(e, "stderr") else "",
            timed_out=True,
        )


def get_running_bw_container_details() -> list[dict]:
    """Return details of running BW containers: name, status, project path, and workitem."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=bentwookie", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
    except subprocess.TimeoutExpired:
        log.warning("Docker not responding when checking running containers")
        return []

    containers = []
    for name in result.stdout.strip().splitlines():
        info = {"name": name, "status": "", "project": "", "workitem": "", "elapsed": ""}
        try:
            fmt = (
                "{{.State.Status}}"
                "|{{range .Mounts}}{{if eq .Destination \"/app/project\"}}{{.Source}}{{end}}{{end}}"
                "|{{range .Mounts}}{{if eq .Destination \"/app/bw\"}}{{.Source}}{{end}}{{end}}"
                "|{{.State.StartedAt}}"
            )
            inspect = subprocess.run(
                ["docker", "inspect", name, "--format", fmt],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspect.returncode == 0:
                parts = inspect.stdout.strip().split("|")
                info["status"] = parts[0] if len(parts) > 0 else ""
                info["project"] = parts[1] if len(parts) > 1 else ""
                bw_path = parts[2] if len(parts) > 2 else ""
                if bw_path:
                    info["workitem"] = _read_wip_workitem_name(Path(bw_path))
                started_at = parts[3] if len(parts) > 3 else ""
                if started_at:
                    info["elapsed"] = _format_elapsed(started_at)
        except subprocess.TimeoutExpired:
            pass
        containers.append(info)
    return containers


def _format_elapsed(started_at: str) -> str:
    """Convert a Docker StartedAt timestamp to a human-readable elapsed time."""
    try:
        # Docker gives ISO format like 2026-02-12T16:10:35.306568333Z
        # Python can't parse nanoseconds, so truncate to microseconds
        clean = started_at.replace("Z", "+00:00")
        if "." in clean:
            dot_idx = clean.index(".")
            plus_idx = clean.index("+", dot_idx)
            frac = clean[dot_idx + 1:plus_idx][:6]
            clean = clean[:dot_idx + 1] + frac + clean[plus_idx:]
        start = datetime.fromisoformat(clean)
        elapsed = datetime.now(timezone.utc) - start
        total_secs = int(elapsed.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        mins, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}h {mins:02d}m {secs:02d}s"
        return f"{mins}m {secs:02d}s"
    except Exception:
        return ""


def _read_wip_workitem_name(bw_path: Path) -> str:
    """Read the workitem_name from the first .md file in wip/."""
    wip_dir = bw_path / "work" / "wip"
    if not wip_dir.is_dir():
        return ""
    files = sorted(wip_dir.glob("*.md"))
    if not files:
        return ""
    # Quick parse: find workitem_name in frontmatter without importing workitem module
    for line in files[0].read_text().splitlines():
        line = line.strip()
        if line == "---":
            continue
        if line.startswith("workitem_name:"):
            return line.split(":", 1)[1].strip()
    return files[0].stem


def get_running_bw_containers() -> list[str]:
    """Return a list of running BW container names (labeled 'bentwookie')."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=bentwookie", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
        return []
    except subprocess.TimeoutExpired:
        log.warning("Docker not responding when checking running containers")
        return []


def run_interactive_login(container_name: str, image_name: str = "bw:0.3.0") -> None:
    """Run an interactive container for `claude login`.

    This must be run from a terminal with TTY support.
    """
    cred_vol = get_credential_volume_name(container_name)
    ensure_credential_volume(container_name)

    cmd = [
        "docker", "run", "--rm", "-it",
        "-v", f"{cred_vol}:/home/bwuser/.claude",
        image_name,
        "-c", "claude login",
    ]

    log.info("Starting interactive login for container '%s'", container_name)
    # Use os.execvp for true interactive TTY passthrough
    import os
    os.execvp("docker", cmd)


def run_interactive_shell(container_name: str, image_name: str = "bw:0.3.0") -> None:
    """Drop into an interactive bash shell inside a container.

    Mounts the credential volume so credentials are accessible.
    This must be run from a terminal with TTY support.
    """
    cred_vol = get_credential_volume_name(container_name)
    ensure_credential_volume(container_name)

    cmd = [
        "docker", "run", "--rm", "-it",
        "-v", f"{cred_vol}:/home/bwuser/.claude",
        image_name,
    ]

    log.info("Starting interactive shell for container '%s'", container_name)
    import os
    os.execvp("docker", cmd)
