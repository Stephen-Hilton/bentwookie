"""BentWookie CLI — Click-based entry point."""

import logging
import shutil
import sys
from pathlib import Path

import click

from bw.lib.config import get_bw_path, load_config
from bw.lib.docker_manager import (
    build_image,
    ensure_credential_volume,
    run_interactive_login,
)
from bw.lib.engine import get_status, run_loop
from bw.lib.workitem import create_workitem_from_instructions, generate_workitem_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bw")


@click.group()
@click.version_option(version="0.3.0", prog_name="bentwookie")
def main():
    """BentWookie — AI auto-coding framework."""


@main.command()
def init():
    """Initialize BW: create work dirs, build Docker image, create credential volumes."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory. Are you in the right repo?", err=True)
        sys.exit(1)

    config = load_config(bw_path)

    # Ensure work directories exist
    for subdir in ["queue", "wip", "done", "error", "review"]:
        d = bw_path / "work" / subdir
        d.mkdir(parents=True, exist_ok=True)
        click.echo(f"  Directory ready: {d}")

    # Build Docker image
    dockerfile = bw_path.parent / "Dockerfile"
    if dockerfile.exists():
        click.echo(f"\nBuilding Docker image '{config.image.name}'...")
        if build_image(dockerfile, config.image.name):
            click.echo("  Image built successfully.")
        else:
            click.echo("  Image build FAILED. Check Docker output above.", err=True)
    else:
        click.echo(f"\nWarning: Dockerfile not found at {dockerfile}", err=True)

    # Create credential volumes for all containers
    click.echo("\nCreating credential volumes...")
    for container in config.containers:
        if ensure_credential_volume(container.name):
            click.echo(f"  Volume ready: bw-creds-{container.name}")

    click.echo("\nBW init complete.")


@main.command()
@click.option("--name", "-n", required=True, help="Name for the workitem")
@click.option("--code", "-c", required=True, type=click.Path(exists=True, file_okay=False),
              help="Path to the code directory")
@click.option("--instructions", "-i", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Path to the instructions markdown file")
@click.option("--container", default=None, help="Container name (defaults to active_container)")
def add(name, code, instructions, container):
    """Create a workitem and add it to the queue."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    config = load_config(bw_path)
    container_name = container or config.active_container
    code_path = str(Path(code).resolve())

    # Read instructions file
    instructions_text = Path(instructions).read_text()

    # Create the workitem
    content = create_workitem_from_instructions(
        bw_path=bw_path,
        name=name,
        code_path=code_path,
        instructions_text=instructions_text,
        container_name=container_name,
        version=config.version,
    )

    # Write to queue
    filename = generate_workitem_filename(name)
    queue_dir = bw_path / "work" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    dest = queue_dir / filename
    dest.write_text(content)

    click.echo(f"Workitem queued: {dest}")


@main.command()
def status():
    """Show queue/wip/done/error/review counts and container info."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    config = load_config(bw_path)
    s = get_status(bw_path)

    click.echo(f"BentWookie v{config.version}")
    click.echo(f"Active container: {config.active_container}\n")
    click.echo("Work items:")
    click.echo(f"  Queue:  {s['queue']}")
    click.echo(f"  WIP:    {s['wip']}")
    click.echo(f"  Done:   {s['done']}")
    click.echo(f"  Error:  {s['error']}")
    click.echo(f"  Review: {s['review']}")
    click.echo(f"\nContainers:\n  {s['containers']}")


@main.command()
@click.argument("mode", default="once")
def run(mode):
    """Process workitems. MODE: 'once' (1 item), a number, or 'loop' (infinite)."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    if mode == "once":
        max_iter = 1
    elif mode == "loop":
        max_iter = 0
    else:
        try:
            max_iter = int(mode)
        except ValueError:
            click.echo(f"Invalid mode: '{mode}'. Use 'once', a number, or 'loop'.", err=True)
            sys.exit(1)

    click.echo(f"Starting BW engine (max_iterations={max_iter or 'infinite'})...")
    run_loop(bw_path, max_iterations=max_iter)
    click.echo("Engine stopped.")


@main.command()
@click.argument("container_name")
def login(container_name):
    """Run interactive `claude login` in a container for credential setup."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    config = load_config(bw_path)

    # Validate container name
    valid_names = [c.name for c in config.containers]
    if container_name not in valid_names:
        click.echo(f"Unknown container '{container_name}'. Valid: {', '.join(valid_names)}", err=True)
        sys.exit(1)

    click.echo(f"Launching interactive login for '{container_name}'...")
    run_interactive_login(container_name, config.image.name)


if __name__ == "__main__":
    main()
