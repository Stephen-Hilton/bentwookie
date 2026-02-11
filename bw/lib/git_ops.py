"""Git operations for BentWookie — all subprocess-based."""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

BRANCH_NAME = "AIAutoCoder"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command, capturing output."""
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=60
    )


def is_git_repo(code_path: Path) -> bool:
    """Check if code_path is inside a git repository."""
    result = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=code_path)
    return result.returncode == 0


def get_current_branch(code_path: Path) -> str | None:
    """Return the current branch name, or None."""
    result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=code_path)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def commit_current_state(code_path: Path, message: str) -> bool:
    """Stage all changes and commit. Returns True if a commit was made."""
    _run(["git", "add", "-A"], cwd=code_path)
    result = _run(["git", "commit", "-m", message], cwd=code_path)
    if result.returncode == 0:
        log.info("Committed: %s", message)
        return True
    # Nothing to commit is not an error
    if "nothing to commit" in result.stdout:
        log.debug("Nothing to commit")
        return False
    log.warning("Git commit failed: %s", result.stderr.strip())
    return False


def ensure_branch(code_path: Path, branch: str = BRANCH_NAME) -> str | None:
    """Switch to the target branch, creating it if needed.

    Returns the original branch name so we can switch back later.
    """
    if not is_git_repo(code_path):
        return None

    original = get_current_branch(code_path)

    # Check if branch exists
    result = _run(["git", "rev-parse", "--verify", branch], cwd=code_path)
    if result.returncode == 0:
        _run(["git", "checkout", branch], cwd=code_path)
    else:
        _run(["git", "checkout", "-b", branch], cwd=code_path)

    log.info("On branch: %s", branch)
    return original


def prepare_for_processing(code_path: Path) -> str | None:
    """Prepare the repo for AI processing: commit any pending changes, switch to AIAutoCoder branch.

    Returns the original branch name, or None if not a git repo.
    """
    if not is_git_repo(code_path):
        log.debug("Not a git repo: %s", code_path)
        return None

    # Commit any uncommitted work on the current branch
    commit_current_state(code_path, "BW: auto-save before AI processing")
    # Switch to the AI branch
    return ensure_branch(code_path)


def finalize_after_processing(code_path: Path, original_branch: str | None) -> None:
    """After AI processing: commit AI changes, optionally switch back to original branch."""
    if not is_git_repo(code_path):
        return

    commit_current_state(code_path, "BW: AI auto-coder changes")

    # Switch back to original branch if we know it
    if original_branch and original_branch != BRANCH_NAME:
        _run(["git", "checkout", original_branch], cwd=code_path)
        log.info("Switched back to branch: %s", original_branch)
