"""Prompt building utilities for BentWookie."""

import random
import re
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_config
from .constants import (
    STATUS_PLANNING,
    WHITESPACE_SLEEP,
)
from .core import (
    Task,
    get_global_resources,
    get_stage_resources,
    get_task,
    move_stage,
    save_task,
)
from .logging_util import get_logger


def substitute_placeholders(text: str, task: Task, extra: dict[str, Any] | None = None) -> str:
    """Substitute placeholders in text with task values.

    Supports:
    - Simple keys: {name}, {status}
    - Nested keys: {file_paths.task}, {infrastructure.compute}
    - Date/time: {today}, {now}, {date}, {time}
    - Loop name: {loopname}, {loop_name}

    Args:
        text: Text containing {placeholder} patterns
        task: Task dictionary with values
        extra: Additional placeholder values

    Returns:
        Text with placeholders substituted
    """
    if not text:
        return text

    # Build placeholder dictionary from task
    placeholders: dict[str, str] = {}

    def flatten_dict(d: dict[str, Any], prefix: str = "") -> None:
        """Recursively flatten a dictionary with dot notation."""
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flatten_dict(value, full_key)
            else:
                placeholders[full_key] = str(value) if value is not None else ""
                # Also add without prefix for top-level keys
                if not prefix:
                    placeholders[key] = str(value) if value is not None else ""

    flatten_dict(dict(task))

    # Add date/time placeholders
    now = datetime.now()
    placeholders.update({
        "today": now.strftime("%Y-%m-%d"),
        "date": now.strftime("%Y-%m-%d"),
        "now": now.strftime("%Y-%m-%d_%H-%M-%S"),
        "time": now.strftime("%H-%M-%S"),
        "datetime": now.strftime("%Y-%m-%d_%H-%M-%S"),
        "timestamp": now.strftime("%Y%m%d-%H%M%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "hour": now.strftime("%H"),
    })

    # Add extra placeholders
    if extra:
        placeholders.update({str(k): str(v) for k, v in extra.items()})

    # Perform substitution
    result = text
    for key, value in placeholders.items():
        result = result.replace(f"{{{key}}}", value)

    return result


def whitespace_prompt() -> str:
    """Generate a whitespace prompt when no tasks are available.

    Executes a random whitespace function to perform actual maintenance,
    then returns a prompt with the results and includes a 600-second sleep.

    Returns:
        Whitespace prompt string with function results
    """
    logger = get_logger()

    from .whitespace import WHITESPACE_FUNCTIONS, run_random_whitespace_function

    # Run a random whitespace function
    func_name, result = run_random_whitespace_function()
    description = WHITESPACE_FUNCTIONS[func_name][1]

    logger.info(f"No tasks available. Running whitespace function: {func_name}")

    # Build the prompt with actual results
    prompt = f"""# Whitespace Task

No prioritized tasks are currently available for processing.

## Suggested Activity
{description}

## Pre-computed Results
The following analysis was automatically performed:

```
{result}
```

## Instructions
- This is a low-priority maintenance task
- Review the pre-computed results above
- Take action if needed based on findings
- Log any changes made
- If nothing needs to be done, simply acknowledge completion

## After Completion
After completing this task (or if no action is needed), simply respond with "Whitespace task complete."
"""

    # Sleep for the whitespace duration
    logger.info(f"Sleeping for {WHITESPACE_SLEEP} seconds...")
    time.sleep(WHITESPACE_SLEEP)

    return prompt


def generate_loop_name() -> str:
    """Generate a random 12-character alphanumeric loop name.

    Returns:
        Random loop name string
    """
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=12))


def sanitize_loop_name(name: str) -> str:
    """Sanitize a loop name for use in file paths.

    Args:
        name: Loop name to sanitize

    Returns:
        Sanitized loop name
    """
    # Remove non-alphanumeric characters except hyphens and underscores
    sanitized = re.sub(r"[^\w\-]", "", name)
    return sanitized or generate_loop_name()


def build_final_prompt(task: Task | str | Path, loop_name: str | None = None) -> str:
    """Build the final prompt for a task.

    This function:
    1. Checks for race conditions by updating status
    2. Loads stage-specific instructions and learnings
    3. Moves the task to the next stage
    4. Substitutes all placeholders
    5. Returns the complete prompt

    Args:
        task: Task dictionary or path to task file
        loop_name: Name of the loop (for logging/identification)

    Returns:
        Complete prompt string, or "do nothing" on race condition
    """
    config = get_config()
    logger = get_logger()

    # Load task if path provided
    if isinstance(task, (str, Path)):
        task = get_task(task)

    # Generate loop name if not provided
    if not loop_name:
        loop_name = generate_loop_name()
    else:
        loop_name = sanitize_loop_name(loop_name)

    logger.set_loop_name(loop_name)
    logger.info(f"Building prompt for task: {task.get('name')}")

    # Race condition check - update status with loop name marker
    race_marker = f"planning implementation phase - {loop_name}"
    task["status"] = race_marker
    task["last_updated"] = datetime.now().isoformat()
    save_task(task)

    # Sleep for random duration (1-2000 ms) to detect race conditions
    sleep_ms = random.randint(1, 2000)
    time.sleep(sleep_ms / 1000.0)

    # Re-read the task to check for race condition
    task_path = task.get("file_path")
    if not task_path:
        logger.error("Task has no file_path")
        return "do nothing"

    task = get_task(task_path)
    current_status = task.get("status", "")

    if current_status != race_marker:
        logger.warning(
            f"Race condition detected! Expected '{race_marker}', "
            f"found '{current_status}'. Aborting."
        )
        return "do nothing"

    # Get the current stage
    current_stage = task.get("stage", "1plan")

    # Load stage resources (instructions and learnings)
    stage_resources = get_stage_resources(current_stage)
    instructions = stage_resources.get("instructions", "")
    stage_learnings = stage_resources.get("learnings", "")

    # Load global resources
    global_resources = get_global_resources()
    global_learnings = global_resources.get("learnings", "")
    interfaces = global_resources.get("interfaces", "")
    setup = global_resources.get("setup", "")

    # Combine learnings (global + stage-specific)
    combined_learnings = ""
    if global_learnings:
        combined_learnings += f"## Global Learnings\n{global_learnings}\n\n"
    if stage_learnings:
        combined_learnings += f"## Stage Learnings ({current_stage})\n{stage_learnings}"

    # Move task to next stage (unless in test mode)
    if not config.test_mode:
        task = move_stage(task, task.get("stage", "1plan"))
        # Re-read to get updated path
        task = get_task(task.get("file_path", ""))

    # Prepare extra placeholders
    extra_placeholders = {
        "loopname": loop_name,
        "loop_name": loop_name,
        "instructions": instructions,
        "learnings": combined_learnings,
        "interfaces": interfaces,
        "setup": setup,
        "global_learnings": global_learnings,
        "stage_learnings": stage_learnings,
    }

    # Substitute placeholders in instructions
    instructions = substitute_placeholders(instructions, task, extra_placeholders)

    # Update extra placeholders with substituted instructions
    extra_placeholders["instructions"] = instructions

    # Get the task body and substitute placeholders
    body = task.get("body", "")
    body = substitute_placeholders(body, task, extra_placeholders)

    # Update task body
    task["body"] = body

    # Update status to In Progress
    task["status"] = STATUS_PLANNING
    task["last_updated"] = datetime.now().isoformat()

    # Save the updated task
    save_task(task)

    # Re-read and return the full file content as the prompt
    task_path = task.get("file_path")
    if task_path:
        final_content = Path(task_path).read_text(encoding="utf-8")
        logger.info(f"Prompt built successfully for task: {task.get('name')}")
        return final_content

    logger.error("Failed to read final task file")
    return "do nothing"


def next_prompt(loop_name: str | None = None) -> str:
    """Get the next prompt to run.

    This is the main entry point for the BentWookie loop.
    It:
    1. Gets all tasks
    2. Validates and sorts them by priority
    3. Returns a prompt for the highest priority task, or whitespace prompt if none

    Args:
        loop_name: Optional loop name for logging

    Returns:
        Prompt string to execute
    """
    from .core import get_all_tasks, validate_tasks

    logger = get_logger()

    # Generate loop name if not provided
    if not loop_name:
        loop_name = generate_loop_name()
    else:
        loop_name = sanitize_loop_name(loop_name)

    logger.set_loop_name(loop_name)
    logger.info("Getting next prompt...")

    # Get all tasks
    all_tasks = get_all_tasks()
    logger.info(f"Found {len(all_tasks)} total tasks")

    # Validate and sort tasks
    ready_tasks = validate_tasks(all_tasks)
    logger.info(f"Found {len(ready_tasks)} ready tasks")

    # If no tasks, return whitespace prompt
    if not ready_tasks:
        logger.info("No ready tasks, returning whitespace prompt")
        return whitespace_prompt()

    # Get the highest priority task
    task = ready_tasks[0]
    logger.info(
        f"Selected task: {task.get('name')} "
        f"(stage: {task.get('stage')}, priority: {task.get('priority')})"
    )

    # Build and return the final prompt
    return build_final_prompt(task, loop_name)
