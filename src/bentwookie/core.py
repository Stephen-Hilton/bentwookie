"""Core task management functions for BentWookie."""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

import yaml

from .config import get_config
from .constants import (
    BACKUP_EXTENSION,
    NEXT_STAGE,
    RESOURCES_DIR,
    STAGE_ORDER,
    STAGES,
    STATUS_IN_PROGRESS,
    STATUS_PLANNING,
    STATUS_READY,
    TASK_FILE_EXTENSION,
    TIMEOUT_IN_PROGRESS,
    TIMEOUT_PLANNING,
    VALID_STATUSES,
    YAML_DELIMITER,
)
from .exceptions import (
    StageError,
    TaskNotFoundError,
    TaskParseError,
    TaskValidationError,
)


class Task(TypedDict, total=False):
    """Type definition for a task dictionary."""

    name: str
    status: str
    change_type: str
    project_phase: str
    priority: int
    stage: str
    last_updated: str | None
    file_paths: dict[str, str]
    infrastructure: dict[str, str | None]
    errors: list[str]
    body: str
    file_path: str


def get_task(task_file: str | Path) -> Task:
    """Parse a task file and return task dictionary.

    Args:
        task_file: Path to the task markdown file

    Returns:
        Task dictionary with frontmatter data and body

    Raises:
        TaskNotFoundError: If file doesn't exist
        TaskParseError: If file cannot be parsed
    """
    task_path = Path(task_file)

    if not task_path.exists():
        raise TaskNotFoundError(str(task_path))

    try:
        content = task_path.read_text(encoding="utf-8")
    except OSError as e:
        raise TaskParseError(str(task_path), f"Cannot read file: {e}")

    # Parse YAML frontmatter
    # Handle both standard "---" and "--- frontmatter structured data:" formats
    lines = content.split("\n")

    # Find frontmatter boundaries
    start_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(YAML_DELIMITER):
            if start_idx == -1:
                start_idx = i
            else:
                end_idx = i
                break

    if start_idx == -1 or end_idx == -1:
        raise TaskParseError(str(task_path), "No valid YAML frontmatter found")

    # Extract frontmatter (skip the first delimiter line)
    frontmatter_lines = lines[start_idx + 1 : end_idx]
    # Remove the "frontmatter structured data:" part if present
    if frontmatter_lines and "frontmatter" in frontmatter_lines[0].lower():
        frontmatter_lines = frontmatter_lines[1:]

    frontmatter_text = "\n".join(frontmatter_lines)

    try:
        data = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as e:
        raise TaskParseError(str(task_path), f"Invalid YAML: {e}")

    # Parse the specific list formats for file_paths and infrastructure
    task: Task = {
        "name": data.get("name", ""),
        "status": data.get("status", "Not Started"),
        "change_type": data.get("change_type", "New Feature"),
        "project_phase": data.get("project_phase", "MVP"),
        "priority": int(data.get("priority", 5)),
        "stage": data.get("stage", "1plan"),
        "last_updated": data.get("last_updated"),
        "errors": data.get("errors", []) or [],
        "file_path": str(task_path.absolute()),
    }

    # Parse file_paths (list of single-key dicts)
    file_paths: dict[str, str] = {}
    raw_file_paths = data.get("file_paths", [])
    if isinstance(raw_file_paths, list):
        for item in raw_file_paths:
            if isinstance(item, dict):
                file_paths.update(item)
    elif isinstance(raw_file_paths, dict):
        file_paths = raw_file_paths
    task["file_paths"] = file_paths

    # Parse infrastructure (list of single-key dicts)
    infrastructure: dict[str, str | None] = {}
    raw_infra = data.get("infrastructure", [])
    if isinstance(raw_infra, list):
        for item in raw_infra:
            if isinstance(item, dict):
                infrastructure.update(item)
    elif isinstance(raw_infra, dict):
        infrastructure = raw_infra
    task["infrastructure"] = infrastructure

    # Extract body (everything after frontmatter)
    body_lines = lines[end_idx + 1 :]
    task["body"] = "\n".join(body_lines).strip()

    return task


def save_task(task: Task, create_backup: bool = True) -> Path:
    """Save a task dictionary back to its markdown file.

    Args:
        task: Task dictionary to save
        create_backup: If True, create a .bkup file before overwriting

    Returns:
        Path to the saved file

    Raises:
        TaskValidationError: If task data is invalid
    """
    file_path = task.get("file_path")
    if not file_path:
        raise TaskValidationError(
            task.get("name", "unknown"),
            "file_path",
            "Task has no file_path",
        )

    task_path = Path(file_path)

    # Create backup if file exists
    if create_backup and task_path.exists():
        backup_path = task_path.with_suffix(task_path.suffix + BACKUP_EXTENSION)
        shutil.copy2(task_path, backup_path)

    # Build frontmatter
    frontmatter: dict[str, Any] = {
        "name": task.get("name", ""),
        "status": task.get("status", "Not Started"),
        "change_type": task.get("change_type", "New Feature"),
        "project_phase": task.get("project_phase", "MVP"),
        "priority": task.get("priority", 5),
        "stage": task.get("stage", "1plan"),
        "last_updated": datetime.now().isoformat(),
    }

    # Convert file_paths to list format
    file_paths = task.get("file_paths", {})
    if file_paths:
        frontmatter["file_paths"] = [{k: v} for k, v in file_paths.items()]
    else:
        frontmatter["file_paths"] = []

    # Convert infrastructure to list format
    infrastructure = task.get("infrastructure", {})
    if infrastructure:
        frontmatter["infrastructure"] = [{k: v} for k, v in infrastructure.items()]
    else:
        frontmatter["infrastructure"] = []

    frontmatter["errors"] = task.get("errors", [])

    # Build the file content
    yaml_content = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    body = task.get("body", "")

    content = f"{YAML_DELIMITER} frontmatter structured data:\n{yaml_content}{YAML_DELIMITER}\n\n{body}"

    # Write file
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content, encoding="utf-8")

    return task_path


def get_all_tasks() -> list[Task]:
    """Collect all tasks from all stage directories.

    Returns:
        List of all task dictionaries
    """
    config = get_config()
    tasks: list[Task] = []

    for stage in STAGES:
        stage_path = config.get_stage_path(stage)
        if not stage_path.exists():
            continue

        # Find all .md files (excluding .resources directory)
        for task_file in stage_path.glob(f"*{TASK_FILE_EXTENSION}"):
            if RESOURCES_DIR in str(task_file):
                continue
            try:
                task = get_task(task_file)
                tasks.append(task)
            except (TaskParseError, TaskNotFoundError):
                # Skip invalid task files
                continue

    return tasks


def task_ready(task: Task) -> bool:
    """Check if a task is ready for processing.

    A task is ready if:
    - Status is "Ready" or "Not Started"
    - Or status is "Planning" and last_updated is > 4 hours ago
    - Or status is "In Progress" and last_updated is > 24 hours ago

    Args:
        task: Task dictionary

    Returns:
        True if task is ready for processing
    """
    status = task.get("status", "")
    last_updated = task.get("last_updated")

    # Ready or Not Started tasks are always ready
    if status in [STATUS_READY, "Not Started"]:
        return True

    # Check timeout conditions
    if last_updated:
        try:
            # Handle both ISO format and "None" string
            if last_updated == "None" or last_updated is None:
                return True

            last_dt = datetime.fromisoformat(str(last_updated))
            now = datetime.now()
            elapsed = (now - last_dt).total_seconds()

            if status == STATUS_PLANNING and elapsed > TIMEOUT_PLANNING:
                return True

            if status == STATUS_IN_PROGRESS and elapsed > TIMEOUT_IN_PROGRESS:
                return True

        except ValueError:
            # Invalid timestamp, treat as ready
            return True

    return False


def validate_tasks(all_tasks: list[Task]) -> list[Task]:
    """Filter and sort tasks that are ready for processing.

    Filters to only ready tasks, then sorts by:
    1. Stage (descending - later stages first)
    2. Priority (descending - higher priority first)

    Args:
        all_tasks: List of all tasks

    Returns:
        Sorted list of ready tasks
    """
    # Filter to ready tasks
    ready_tasks = [t for t in all_tasks if task_ready(t)]

    # Sort by stage (descending) then priority (descending)
    def sort_key(task: Task) -> tuple[int, int]:
        stage = task.get("stage", "1plan")
        stage_order = STAGE_ORDER.get(stage, 0)
        priority = task.get("priority", 5)
        return (-stage_order, -priority)

    return sorted(ready_tasks, key=sort_key)


def get_next_stage(task: Task) -> str | None:
    """Get the next stage for a task.

    Args:
        task: Task dictionary

    Returns:
        Next stage name, or None if at final stage
    """
    current_stage = task.get("stage", "1plan")
    return NEXT_STAGE.get(current_stage)


def move_stage(task: Task, new_stage: str) -> Task:
    """Move a task file to a new stage directory.

    Args:
        task: Task dictionary
        new_stage: Target stage name

    Returns:
        Updated task dictionary with new file_path

    Raises:
        StageError: If stage is invalid or move fails
    """
    config = get_config()

    # Check test mode
    if config.test_mode:
        # In test mode, just update the stage but don't move the file
        task["stage"] = new_stage
        task["last_updated"] = datetime.now().isoformat()
        return task

    # Validate stage
    if new_stage not in STAGES:
        raise StageError(new_stage, "move", f"Invalid stage: {new_stage}")

    current_path = Path(task.get("file_path", ""))
    if not current_path.exists():
        raise StageError(
            new_stage,
            "move",
            f"Source file does not exist: {current_path}",
        )

    # Build new path
    new_stage_path = config.get_stage_path(new_stage)
    new_stage_path.mkdir(parents=True, exist_ok=True)
    new_path = new_stage_path / current_path.name

    # Move file
    try:
        shutil.move(str(current_path), str(new_path))
    except OSError as e:
        raise StageError(new_stage, "move", f"Failed to move file: {e}")

    # Update task
    task["file_path"] = str(new_path.absolute())
    task["stage"] = new_stage
    task["last_updated"] = datetime.now().isoformat()

    # Update file_paths.task in the task
    file_paths = task.get("file_paths", {})
    file_paths["task"] = str(new_path)
    task["file_paths"] = file_paths

    # Save the updated task
    save_task(task)

    return task


def update_status(task: Task, new_status: str) -> Task:
    """Update task status and save.

    Args:
        task: Task dictionary
        new_status: New status value

    Returns:
        Updated task dictionary

    Raises:
        TaskValidationError: If status is invalid
    """
    if new_status not in VALID_STATUSES:
        raise TaskValidationError(
            task.get("name", "unknown"),
            "status",
            f"Invalid status: {new_status}. Must be one of: {VALID_STATUSES}",
        )

    task["status"] = new_status
    task["last_updated"] = datetime.now().isoformat()
    save_task(task)

    return task


def create_task_file(
    name: str,
    stage: str = "1plan",
    body: str = "",
    **kwargs: Any,
) -> Task:
    """Create a new task file.

    Args:
        name: Task name
        stage: Initial stage
        body: Markdown body content
        **kwargs: Additional task fields

    Returns:
        Created task dictionary
    """
    config = get_config()

    # Generate filename from name
    safe_name = re.sub(r"[^\w\s-]", "", name).strip()
    safe_name = re.sub(r"[-\s]+", "-", safe_name).lower()
    filename = f"{safe_name}{TASK_FILE_EXTENSION}"

    # Build task path
    stage_path = config.get_stage_path(stage)
    stage_path.mkdir(parents=True, exist_ok=True)
    task_path = stage_path / filename

    # Build task dictionary
    task: Task = {
        "name": name,
        "status": kwargs.get("status", "Not Started"),
        "change_type": kwargs.get("change_type", "New Feature"),
        "project_phase": kwargs.get("project_phase", "MVP"),
        "priority": kwargs.get("priority", 5),
        "stage": stage,
        "last_updated": datetime.now().isoformat(),
        "file_paths": {
            "project_root": kwargs.get("project_root", "./"),
            "tasks": str(config.tasks_path),
            "task": str(task_path),
        },
        "infrastructure": kwargs.get("infrastructure", {}),
        "errors": [],
        "body": body,
        "file_path": str(task_path.absolute()),
    }

    # Save the task
    save_task(task, create_backup=False)

    return task


def get_task_by_name(name: str) -> Task | None:
    """Find a task by name.

    Args:
        name: Task name to search for

    Returns:
        Task dictionary if found, None otherwise
    """
    all_tasks = get_all_tasks()
    for task in all_tasks:
        if task.get("name", "").lower() == name.lower():
            return task
    return None


def get_stage_resources(stage: str) -> dict[str, str]:
    """Get resources (instructions, learnings) for a stage.

    Args:
        stage: Stage name

    Returns:
        Dictionary with 'instructions' and 'learnings' content
    """
    config = get_config()
    resources_path = config.get_resources_path(stage)

    result: dict[str, str] = {
        "instructions": "",
        "learnings": "",
    }

    # Read instructions
    instructions_file = resources_path / "instructions.md"
    if instructions_file.exists():
        result["instructions"] = instructions_file.read_text(encoding="utf-8")

    # Read learnings
    learnings_file = resources_path / "learnings.md"
    if learnings_file.exists():
        result["learnings"] = learnings_file.read_text(encoding="utf-8")

    return result


def get_global_resources() -> dict[str, str]:
    """Get global resources (interfaces, learnings, setup).

    Returns:
        Dictionary with 'interfaces', 'learnings', 'setup' content
    """
    config = get_config()
    global_path = config.global_dir

    result: dict[str, str] = {
        "interfaces": "",
        "learnings": "",
        "setup": "",
    }

    # Read interfaces
    interfaces_file = global_path / "interfaces.md"
    if interfaces_file.exists():
        result["interfaces"] = interfaces_file.read_text(encoding="utf-8")

    # Read learnings
    learnings_file = global_path / "learnings.md"
    if learnings_file.exists():
        result["learnings"] = learnings_file.read_text(encoding="utf-8")

    # Read setup
    setup_file = global_path / "setup.md"
    if setup_file.exists():
        result["setup"] = setup_file.read_text(encoding="utf-8")

    return result
