"""Main processing loop for BentWookie."""

import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from bw.lib.config import BWConfig, get_package_lib_path, load_config
from bw.lib.docker_manager import (
    ContainerResult,
    build_image,
    check_container_status,
    image_exists,
    run_workitem,
)
from bw.lib.notify import (
    extract_notification_from_workitem,
    notify_completed,
    notify_error,
    notify_started,
)
from bw.lib.workitem import (
    create_next_step_workitems,
    fill_optional_frontmatter,
    parse_frontmatter,
    serialize_frontmatter,
    validate_frontmatter,
)

log = logging.getLogger(__name__)


def pick_next_workitem(queue_path: Path) -> Path | None:
    """Return the first .md file in the queue directory by filename, or None."""
    candidates = sorted(queue_path.glob("*.md"), key=lambda p: p.name)
    return candidates[0] if candidates else None


def move_workitem(path: Path, dest_dir: Path) -> Path:
    """Move a workitem file to dest_dir, handling filename collisions."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    if dest.exists():
        stem = path.stem
        suffix = path.suffix
        ts = datetime.now().strftime("%H%M%S")
        dest = dest_dir / f"{stem}_{ts}{suffix}"
    shutil.move(str(path), str(dest))
    log.info("Moved %s → %s", path.name, dest)
    return dest


def _warn_stale_wip(wip_path: Path) -> None:
    """Log warnings for any workitems stuck in wip/."""
    stale = list(wip_path.glob("*.md"))
    if stale:
        log.warning(
            "Found %d orphaned workitem(s) in wip/ — these may be from a previous crash:",
            len(stale),
        )
        for f in stale:
            log.warning("  - %s", f.name)


def _annotate_error(workitem_path: Path, error_msg: str) -> None:
    """Append an error annotation to a workitem file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    annotation = f"\n\n---\n\n# BW ERROR\n_Timestamp: {timestamp}_\n\n{error_msg}\n"
    with open(workitem_path, "a") as f:
        f.write(annotation)


def process_single_workitem(bw_path: Path, config: BWConfig) -> bool:
    """Process one workitem from the queue. Returns True if one was processed."""
    queue_path = bw_path / "work" / "queue"
    wip_path = bw_path / "work" / "wip"
    done_path = bw_path / "work" / "done"
    error_path = bw_path / "work" / "error"

    # 1. Pick from queue
    workitem = pick_next_workitem(queue_path)
    if workitem is None:
        log.debug("Queue is empty")
        return False

    log.info("Processing workitem: %s", workitem.name)

    # 2. Move to wip/
    wip_file = move_workitem(workitem, wip_path)

    # 3. Validate frontmatter
    text = wip_file.read_text()
    fm, body = parse_frontmatter(text)
    errors = validate_frontmatter(fm)
    if errors:
        error_msg = "Validation errors:\n" + "\n".join(f"  - {e}" for e in errors)
        log.error("%s: %s", wip_file.name, error_msg)
        _annotate_error(wip_file, error_msg)
        move_workitem(wip_file, error_path)
        return True

    # Fill optional fields and mark as in-progress
    container = config.get_active_container()
    fill_optional_frontmatter(fm, container.name, config.version)
    fm["status"] = "in_progress"
    fm["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wip_file.write_text(serialize_frontmatter(fm, body))

    code_path = Path(fm["code_path"])
    workitem_name = fm.get("workitem_name", wip_file.stem)

    # Notify: started
    notify_started(workitem_name, str(code_path), container, bw_path)

    # 4. Docker: check image, auto-rebuild if missing
    if not image_exists(config.image.name):
        log.warning("Docker image '%s' not found — attempting auto-rebuild...", config.image.name)
        dockerfile = get_package_lib_path() / "Dockerfile"
        if dockerfile.exists() and build_image(dockerfile, config.image.name):
            log.info("Auto-rebuild of '%s' succeeded", config.image.name)
        else:
            error_msg = f"Docker image '{config.image.name}' not found and auto-rebuild failed. Run `bw init` manually."
            log.error(error_msg)
            _annotate_error(wip_file, error_msg)
            move_workitem(wip_file, error_path)
            return True

    result: ContainerResult = run_workitem(
        workitem_path=wip_file,
        code_path=code_path,
        bw_path=bw_path,
        container_config=container,
        image_name=config.image.name,
    )

    # 6. Re-read workitem (Claude may have modified it)
    if not wip_file.exists():
        log.error("Workitem file disappeared: %s — it may have been removed by a git branch switch", wip_file)
        return True
    text = wip_file.read_text()
    fm, body = parse_frontmatter(text)

    # Check completion
    if result.timed_out:
        fm["status"] = "error"
        error_detail = "Container timed out"
        log.error("%s: %s", wip_file.name, error_detail)
        wip_file.write_text(serialize_frontmatter(fm, body))
        _annotate_error(wip_file, error_detail)
        dest = move_workitem(wip_file, error_path)
        notify_error(workitem_name, error_detail, container, bw_path)
    elif result.exit_code != 0:
        # If Claude already marked workitem complete (e.g. watchdog killed a stuck-but-done process),
        # treat as success rather than error
        if fm.get("status") == "complete" and fm.get("complete_at"):
            log.warning(
                "%s: Container exited with code %d but workitem was marked complete — treating as success",
                wip_file.name, result.exit_code,
            )
            dest = move_workitem(wip_file, done_path)
        else:
            fm["status"] = "error"
            stderr_tail = result.stderr[-2000:] if result.stderr else "(no stderr)"
            error_detail = f"Container exited with code {result.exit_code}\n\nstderr:\n{stderr_tail}"
            log.error("%s: Container failed (exit %d):\n%s", wip_file.name, result.exit_code, stderr_tail)
            wip_file.write_text(serialize_frontmatter(fm, body))
            _annotate_error(wip_file, error_detail)
            dest = move_workitem(wip_file, error_path)
            notify_error(workitem_name, error_detail, container, bw_path)
    elif fm.get("status") == "complete" and fm.get("complete_at"):
        # AI marked it complete
        dest = move_workitem(wip_file, done_path)
    else:
        # Container succeeded but AI didn't mark complete — still move to done
        fm.setdefault("status", "complete")
        fm.setdefault("complete_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        wip_file.write_text(serialize_frontmatter(fm, body))
        dest = move_workitem(wip_file, done_path)

    # 8. Parse nextsteps from the final workitem text
    final_text = dest.read_text()
    created = create_next_step_workitems(final_text, bw_path, config.version)
    if created:
        log.info("Created %d next-step workitem(s)", len(created))

    # 9. Notification
    notification = extract_notification_from_workitem(dest)
    notify_completed(workitem_name, notification, container, bw_path)

    return True


def run_loop(bw_path: Path, max_iterations: int = 0) -> bool:
    """Main processing loop.

    max_iterations: 0 = infinite loop, N = process at most N workitems.
    Re-reads config each iteration.
    Returns True if a restart was requested.
    """
    # Ensure work and log directories exist
    for subdir in ("queue", "wip", "done", "error", "review"):
        (bw_path / "work" / subdir).mkdir(parents=True, exist_ok=True)
    (bw_path / "logs").mkdir(parents=True, exist_ok=True)

    _warn_stale_wip(bw_path / "work" / "wip")

    stop_file = bw_path / "work" / ".stop"
    pause_file = bw_path / "work" / ".pause"
    restart_file = bw_path / "work" / ".restart"

    iteration = 0
    while True:
        if max_iterations > 0 and iteration >= max_iterations:
            log.info("Reached max iterations (%d), stopping", max_iterations)
            break

        # Check for .stop sentinel — graceful shutdown
        if stop_file.exists():
            stop_file.unlink()
            log.info("Stop file detected — shutting down gracefully")
            break

        # Check for .restart sentinel — finish current item then restart
        if restart_file.exists():
            restart_file.unlink()
            log.info("Restart file detected — restarting after cleanup")
            return True

        # Check for .pause sentinel — wait until removed
        if pause_file.exists():
            log.info("Pause file detected — pausing loop")
            while pause_file.exists():
                time.sleep(5)
            log.info("Pause file removed — resuming loop")

        try:
            config = load_config(bw_path)
        except Exception as e:
            log.error("Failed to load config: %s", e)
            time.sleep(30)
            continue

        container = config.get_active_container()
        processed = process_single_workitem(bw_path, config)

        if processed:
            iteration += 1
            # Sleep between workitems to respect rate limits
            sleep_secs = container.sleep_seconds
            log.info("Sleeping %ds before next iteration [%s]...", sleep_secs, container.name)
            time.sleep(sleep_secs)
        else:
            # Queue empty
            if max_iterations > 0:
                log.info("Queue empty, nothing to process")
                break
            # Infinite loop — sleep before checking again
            sleep_secs = container.sleep_seconds
            log.info("Queue empty [%s], sleeping %ds...", container.name, sleep_secs)
            time.sleep(sleep_secs)

    return False


def get_status(bw_path: Path) -> dict:
    """Return counts and container status for display."""
    work = bw_path / "work"
    status = {}
    for subdir in ["queue", "wip", "done", "error", "review"]:
        d = work / subdir
        status[subdir] = len(list(d.glob("*.md"))) if d.exists() else 0

    status["containers"] = check_container_status()
    return status
