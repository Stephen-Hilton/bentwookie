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


def build_image(dockerfile_path: Path, image_name: str = "bw:0.3.0") -> bool:
    """Build the Docker image from the Dockerfile.

    Returns True on success.
    """
    context = dockerfile_path.parent
    log.info("Building Docker image '%s' from %s", image_name, dockerfile_path)
    result = subprocess.run(
        ["docker", "build", "-t", image_name, "-f", str(dockerfile_path), "."],
        cwd=context,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        log.error("Docker build failed:\n%s", result.stderr)
        return False
    log.info("Docker image '%s' built successfully", image_name)
    return True


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

    Mounts:
      - code_path → /app/project
      - bw_path → /app/bw
      - credential volume → /root/.claude

    The workitem file is piped to Claude Code via stdin.
    """
    cred_vol = get_credential_volume_name(container_config.name)
    wip_filename = workitem_path.name

    # Build the claude command
    model_flag = f"--model {container_config.model}" if container_config.model else ""
    skip_flag = "--dangerously-skip-permissions" if container_config.dangerously_skip_permissions else ""
    claude_cmd = f'cat /app/bw/work/wip/{wip_filename} | claude -p "Execute these instructions" {model_flag} {skip_flag}'

    cmd = [
        "docker", "run", "--rm",
        "--label", "bentwookie",
        "--name", f"bw-{container_config.name}-{wip_filename[:20]}",
        "-v", f"{code_path.resolve()}:/app/project",
        "-v", f"{bw_path.resolve()}:/app/bw",
        "-v", f"{cred_vol}:/root/.claude",
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


def run_interactive_login(container_name: str, image_name: str = "bw:0.3.0") -> None:
    """Run an interactive container for `claude login`.

    This must be run from a terminal with TTY support.
    """
    cred_vol = get_credential_volume_name(container_name)
    ensure_credential_volume(container_name)

    cmd = [
        "docker", "run", "--rm", "-it",
        "-v", f"{cred_vol}:/root/.claude",
        image_name,
        "-c", "claude login",
    ]

    log.info("Starting interactive login for container '%s'", container_name)
    # Use os.execvp for true interactive TTY passthrough
    import os
    os.execvp("docker", cmd)
