"""Command-line interface for BentWookie."""

import shutil
import sys
from pathlib import Path
from typing import Optional

import click

from .config import init_config, get_config
from .constants import STAGES
from .core import get_task, move_stage, update_status
from .exceptions import BentWookieError
from .logging_util import init_logger
from .prompt_builder import next_prompt
from .wizard import plan


def get_templates_path() -> Path:
    """Get the path to the templates directory.

    Returns:
        Path to templates directory
    """
    # First, try relative to this file (development mode)
    dev_path = Path(__file__).parent / "templates"
    if dev_path.exists():
        return dev_path

    # Then try installed package location
    import importlib.resources
    try:
        # Python 3.9+
        with importlib.resources.as_file(
            importlib.resources.files("bentwookie") / "templates"
        ) as path:
            return path
    except (TypeError, AttributeError):
        # Fallback for older Python
        return dev_path


def copy_templates(dest_path: Path) -> None:
    """Copy template files to destination.

    Args:
        dest_path: Destination directory

    Raises:
        click.ClickException: If copy fails
    """
    templates_src = get_templates_path()
    tasks_src = templates_src / "tasks"

    if not tasks_src.exists():
        raise click.ClickException(f"Templates not found at {tasks_src}")

    tasks_dest = dest_path / "tasks"

    if tasks_dest.exists():
        if not click.confirm(f"Directory {tasks_dest} exists. Overwrite?"):
            raise click.ClickException("Aborted")
        shutil.rmtree(tasks_dest)

    try:
        shutil.copytree(tasks_src, tasks_dest)
        click.echo(f"Templates copied to {tasks_dest}")
    except OSError as e:
        raise click.ClickException(f"Failed to copy templates: {e}")


@click.group(invoke_without_command=True)
@click.option(
    "--init",
    "init_path",
    type=click.Path(exists=False, path_type=Path),
    help="Initialize BentWookie in the specified directory",
)
@click.option(
    "--env",
    "env_path",
    type=click.Path(exists=False, path_type=Path),
    help="Path to .env file",
)
@click.option(
    "--logs",
    "logs_path",
    type=str,
    help="Log file path pattern (supports {today}, {loopname}, etc.)",
)
@click.option(
    "--tasks",
    "tasks_path",
    type=click.Path(exists=False, path_type=Path),
    help="Path to tasks directory",
)
@click.option(
    "--test",
    "test_mode",
    is_flag=True,
    help="Test mode - don't move files between stages",
)
@click.option(
    "--plan",
    "plan_name",
    type=str,
    help="Create a new task plan with the specified name",
)
@click.option(
    "--next_prompt",
    "--next-prompt",
    "loop_name",
    type=str,
    help="Get the next prompt for the specified loop name",
)
@click.pass_context
def main(
    ctx: click.Context,
    init_path: Optional[Path],
    env_path: Optional[Path],
    logs_path: Optional[str],
    tasks_path: Optional[Path],
    test_mode: bool,
    plan_name: Optional[str],
    loop_name: Optional[str],
) -> None:
    """BentWookie - AI coding loop workflow manager.

    BentWookie manages task-based AI development workflows, guiding tasks
    through stages from planning to deployment.

    \b
    Quick Start:
      bw --init ./myproject          # Initialize templates
      bw --plan "My Feature"         # Create a new task
      bw --next_prompt "loop1"       # Get next prompt for AI loop

    \b
    Usage in a loop:
      while :; do bw --next_prompt "myloop" | claude ; done
    """
    # Initialize configuration
    config = init_config(
        env_path=env_path,
        tasks_path=tasks_path,
        logs_path=logs_path,
        test_mode=test_mode,
    )

    # Initialize logger
    logger = init_logger(
        log_path=logs_path or config.logs_path,
    )

    # Handle --init
    if init_path:
        copy_templates(init_path)
        return

    # Handle --plan
    if plan_name:
        task = plan(plan_name)
        if task:
            click.echo(f"\nTask created: {task.get('file_path')}")
        else:
            click.echo("Task creation cancelled.")
        return

    # Handle --next_prompt
    if loop_name:
        prompt = next_prompt(loop_name)
        # Output to stdout (for piping to claude)
        click.echo(prompt)
        return

    # If no action specified and no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("move-stage")
@click.option(
    "--task",
    "task_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the task file",
)
@click.option(
    "--stage",
    "new_stage",
    type=click.Choice(STAGES),
    help="Target stage (default: next stage)",
)
def move_stage_cmd(task_path: Path, new_stage: Optional[str]) -> None:
    """Move a task to a different stage.

    \b
    Examples:
      bw move-stage --task tasks/1plan/my-feature.md
      bw move-stage --task tasks/1plan/my-feature.md --stage 3test
    """
    try:
        task = get_task(task_path)

        if new_stage is None:
            from .core import get_next_stage
            new_stage = get_next_stage(task)
            if new_stage is None:
                click.echo("Task is already at the final stage (9done)")
                return

        task = move_stage(task, new_stage)
        click.echo(f"Task moved to {new_stage}: {task.get('file_path')}")

    except BentWookieError as e:
        raise click.ClickException(str(e))


@main.command("update-status")
@click.option(
    "--task",
    "task_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the task file",
)
@click.option(
    "--status",
    "new_status",
    type=str,
    required=True,
    help="New status value",
)
def update_status_cmd(task_path: Path, new_status: str) -> None:
    """Update the status of a task.

    \b
    Examples:
      bw update-status --task tasks/1plan/my-feature.md --status "Ready"
      bw update-status --task tasks/2dev/my-feature.md --status "In Progress"
    """
    try:
        task = get_task(task_path)
        task = update_status(task, new_status)
        click.echo(f"Status updated to '{new_status}': {task.get('file_path')}")

    except BentWookieError as e:
        raise click.ClickException(str(e))


@main.command("list")
@click.option(
    "--stage",
    "stage_filter",
    type=click.Choice(STAGES),
    help="Filter by stage",
)
@click.option(
    "--ready",
    "ready_only",
    is_flag=True,
    help="Show only ready tasks",
)
def list_tasks(stage_filter: Optional[str], ready_only: bool) -> None:
    """List all tasks.

    \b
    Examples:
      bw list
      bw list --stage 1plan
      bw list --ready
    """
    from .core import get_all_tasks, validate_tasks

    try:
        all_tasks = get_all_tasks()

        if ready_only:
            all_tasks = validate_tasks(all_tasks)

        if stage_filter:
            all_tasks = [t for t in all_tasks if t.get("stage") == stage_filter]

        if not all_tasks:
            click.echo("No tasks found.")
            return

        click.echo(f"\nFound {len(all_tasks)} task(s):\n")
        click.echo(f"{'Stage':<12} {'Priority':<10} {'Status':<20} {'Name'}")
        click.echo("-" * 70)

        for task in all_tasks:
            click.echo(
                f"{task.get('stage', 'N/A'):<12} "
                f"{task.get('priority', 0):<10} "
                f"{task.get('status', 'N/A'):<20} "
                f"{task.get('name', 'N/A')}"
            )

    except BentWookieError as e:
        raise click.ClickException(str(e))


@main.command("show")
@click.argument("task_path", type=click.Path(exists=True, path_type=Path))
def show_task(task_path: Path) -> None:
    """Show details of a specific task.

    \b
    Example:
      bw show tasks/1plan/my-feature.md
    """
    try:
        task = get_task(task_path)

        click.echo(f"\n{'=' * 60}")
        click.echo(f"Task: {task.get('name', 'N/A')}")
        click.echo(f"{'=' * 60}")
        click.echo(f"Stage:        {task.get('stage', 'N/A')}")
        click.echo(f"Status:       {task.get('status', 'N/A')}")
        click.echo(f"Priority:     {task.get('priority', 'N/A')}")
        click.echo(f"Change Type:  {task.get('change_type', 'N/A')}")
        click.echo(f"Phase:        {task.get('project_phase', 'N/A')}")
        click.echo(f"Last Updated: {task.get('last_updated', 'N/A')}")
        click.echo(f"File:         {task.get('file_path', 'N/A')}")

        file_paths = task.get("file_paths", {})
        if file_paths:
            click.echo(f"\nFile Paths:")
            for key, value in file_paths.items():
                click.echo(f"  {key}: {value}")

        infrastructure = task.get("infrastructure", {})
        if infrastructure and any(infrastructure.values()):
            click.echo(f"\nInfrastructure:")
            for key, value in infrastructure.items():
                if value:
                    click.echo(f"  {key}: {value}")

        errors = task.get("errors", [])
        if errors:
            click.echo(f"\nErrors:")
            for error in errors:
                click.echo(f"  - {error}")

        click.echo(f"\n{'=' * 60}")

    except BentWookieError as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
