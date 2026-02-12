"""Docker container lifecycle management for BentWookie."""

import logging
import subprocess
from dataclasses import dataclass
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


def image_exists(image_name: str) -> bool:
    """Check if a Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log.warning("Docker timed out checking image '%s' — is Docker running?", image_name)
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
    timeout: int = 3600,
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
    claude_cmd = f'''set -e
LOG="{log_file}"
WIP="{wip_file}"
FLAGS="{flags}"
SNIPPETS="{snippets_file}"

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
        image_name,
        "-c", claude_cmd,
    ]

    log.info("Running container for workitem: %s", wip_filename)
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
