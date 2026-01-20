"""BentWookie - AI coding loop workflow manager.

BentWookie manages task-based AI development workflows, guiding tasks
through stages from planning to deployment.

Usage:
    import bentwookie as bw

    # Initialize templates in a project
    bw.init("./myproject")

    # Set environment file
    bw.env("./myproject/.env")

    # Set log path pattern
    bw.logs("./myproject/logs/{loopname}_{today}.log")

    # Create a new task plan
    bw.plan("My New Feature")

    # Get the next prompt for AI execution
    prompt = bw.next_prompt("myloop")
"""

import shutil
from pathlib import Path
from typing import Optional

from .config import init_config, get_config, BWConfig
from .core import (
    Task,
    get_task,
    save_task,
    get_all_tasks,
    task_ready,
    validate_tasks,
    get_next_stage,
    move_stage,
    update_status,
    create_task_file,
    get_task_by_name,
    get_stage_resources,
    get_global_resources,
)
from .exceptions import (
    BentWookieError,
    TaskParseError,
    TaskValidationError,
    TaskNotFoundError,
    StageError,
    ConfigurationError,
    TemplateError,
    RaceConditionError,
    WizardError,
)
from .logging_util import init_logger, get_logger, BWLogger
from .prompt_builder import next_prompt as _next_prompt, whitespace_prompt
from .whitespace import (
    WHITESPACE_FUNCTIONS,
    get_whitespace_function_names,
    run_whitespace_function,
    run_random_whitespace_function,
    run_all_whitespace_functions,
)
from .wizard import plan as _plan, PlanningWizard

__version__ = "0.1.0"
__all__ = [
    # Version
    "__version__",
    # Main functions
    "init",
    "env",
    "logs",
    "plan",
    "next_prompt",
    # Core functions
    "get_task",
    "save_task",
    "get_all_tasks",
    "task_ready",
    "validate_tasks",
    "get_next_stage",
    "move_stage",
    "update_status",
    "create_task_file",
    "get_task_by_name",
    "get_stage_resources",
    "get_global_resources",
    "whitespace_prompt",
    # Whitespace functions
    "WHITESPACE_FUNCTIONS",
    "get_whitespace_function_names",
    "run_whitespace_function",
    "run_random_whitespace_function",
    "run_all_whitespace_functions",
    # Classes
    "Task",
    "BWConfig",
    "BWLogger",
    "PlanningWizard",
    # Exceptions
    "BentWookieError",
    "TaskParseError",
    "TaskValidationError",
    "TaskNotFoundError",
    "StageError",
    "ConfigurationError",
    "TemplateError",
    "RaceConditionError",
    "WizardError",
]


def init(path: str | Path) -> Path:
    """Initialize BentWookie templates in a directory.

    Copies the tasks/ template folder structure to the specified location.

    Args:
        path: Destination directory

    Returns:
        Path to the created tasks directory

    Raises:
        ConfigurationError: If templates cannot be copied
    """
    from .cli import get_templates_path

    dest_path = Path(path)
    templates_src = get_templates_path()
    tasks_src = templates_src / "tasks"

    if not tasks_src.exists():
        raise ConfigurationError("templates", f"Templates not found at {tasks_src}")

    tasks_dest = dest_path / "tasks"

    if tasks_dest.exists():
        shutil.rmtree(tasks_dest)

    try:
        shutil.copytree(tasks_src, tasks_dest)
        return tasks_dest
    except OSError as e:
        raise ConfigurationError("init", f"Failed to copy templates: {e}")


def env(path: str | Path) -> BWConfig:
    """Set and load the environment file.

    Args:
        path: Path to .env file

    Returns:
        Updated configuration instance
    """
    config = init_config(env_path=path)

    # Update settings.yaml with the env path
    config.update_setting("envfile", str(path))

    return config


def logs(path: str) -> BWConfig:
    """Set the log file path pattern.

    Args:
        path: Log file path pattern (supports {today}, {loopname}, etc.)

    Returns:
        Updated configuration instance
    """
    config = get_config()
    config._logs_path = path

    # Re-initialize logger with new path
    init_logger(log_path=path)

    return config


def plan(feature_name: Optional[str] = None) -> Task | None:
    """Run the planning wizard to create a new task.

    Args:
        feature_name: Optional pre-set feature name

    Returns:
        Created task dictionary, or None if cancelled
    """
    return _plan(feature_name)


def next_prompt(loop_name: Optional[str] = None) -> str:
    """Get the next prompt for AI execution.

    This is the main entry point for the BentWookie loop.
    Returns a prompt for the highest priority ready task,
    or a whitespace prompt if no tasks are available.

    Args:
        loop_name: Optional loop name for logging/identification

    Returns:
        Prompt string to execute
    """
    return _next_prompt(loop_name)
