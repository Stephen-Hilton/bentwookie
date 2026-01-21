"""Command-line interface for BentWookie v2."""

from pathlib import Path

import click

from .constants import (
    DEFAULT_PRIORITY,
    PHASE_NAMES,
    PHASES,
    STATUS_NAMES,
    TYPE_NAMES,
    V2_STATUSES,
    VALID_PROJECT_PHASES,
    VALID_REQUEST_TYPES,
    VALID_VERSIONS,
)
from .db import (
    create_project,
    create_request,
    delete_project,
    delete_request,
    get_project,
    get_project_by_name,
    get_request,
    init_db,
    list_projects,
    list_requests,
    update_request_phase,
    update_request_status,
)


def get_templates_path() -> Path:
    """Get the path to the templates directory.

    Returns:
        Path to templates directory
    """
    dev_path = Path(__file__).parent / "templates"
    if dev_path.exists():
        return dev_path

    import importlib.resources
    try:
        with importlib.resources.as_file(
            importlib.resources.files("bentwookie") / "templates"
        ) as path:
            return path
    except (TypeError, AttributeError):
        return dev_path


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """BentWookie v2 - AI coding loop workflow manager.

    BentWookie manages development requests through phases using the
    Claude Agent SDK for execution.

    \b
    Quick Start:
      bw init                          # Initialize database
      bw project create myproject      # Create a project
      bw request create myproject      # Create a request
      bw loop start                    # Start the daemon

    \b
    Commands:
      bw init           Initialize the database
      bw project ...    Manage projects
      bw request ...    Manage requests
      bw loop ...       Control the daemon
      bw status         Show current status
      bw web            Start the web UI
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# =============================================================================
# Init Command
# =============================================================================


@main.command("init")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default="data/bentwookie.db",
    help="Path for SQLite database",
)
def init_cmd(db_path: Path) -> None:
    """Initialize the BentWookie database and directories.

    \b
    Examples:
      bw init
      bw init --db-path ./mydata/bw.db
    """
    from .db.connection import set_db_path

    # Set custom database path if provided
    if db_path != Path("data/bentwookie.db"):
        set_db_path(db_path)

    # Ensure directories exist
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Initialize database
    init_db()

    click.echo(f"Database initialized at: {db_path}")
    click.echo("Created directories: data/, docs/, logs/")
    click.echo("\nNext steps:")
    click.echo("  bw project create <name>  - Create a project")
    click.echo("  bw request create <proj>  - Create a request")


# =============================================================================
# Project Commands
# =============================================================================


@main.group("project")
def project_group() -> None:
    """Manage projects."""
    pass


@project_group.command("create")
@click.argument("name")
@click.option("--version", "-v", type=click.Choice(VALID_VERSIONS), default="poc", help="Project version")
@click.option("--priority", "-p", type=int, default=DEFAULT_PRIORITY, help="Priority (1-10)")
@click.option("--phase", type=click.Choice(VALID_PROJECT_PHASES), default="dev", help="Project phase")
@click.option("--desc", "-d", type=str, help="Project description")
def project_create(
    name: str,
    version: str,
    priority: int,
    phase: str,
    desc: str | None,
) -> None:
    """Create a new project.

    \b
    Examples:
      bw project create myapp
      bw project create myapp --version mvp --priority 3
      bw project create myapp -d "My awesome app"
    """
    try:
        prjid = create_project(
            prjname=name,
            prjversion=version,
            prjpriority=priority,
            prjphase=phase,
            prjdesc=desc,
        )
        click.echo(f"Project created: {name} (ID: {prjid})")
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise click.ClickException(f"Project '{name}' already exists")
        raise click.ClickException(str(e))


@project_group.command("list")
@click.option("--phase", type=click.Choice(VALID_PROJECT_PHASES), help="Filter by phase")
def project_list(phase: str | None) -> None:
    """List all projects.

    \b
    Examples:
      bw project list
      bw project list --phase dev
    """
    projects = list_projects(phase=phase)

    if not projects:
        click.echo("No projects found.")
        return

    click.echo(f"\n{'ID':<6} {'Name':<20} {'Version':<8} {'Pri':<5} {'Phase':<8} {'Description'}")
    click.echo("-" * 80)

    for p in projects:
        desc = (p["prjdesc"] or "")[:30]
        click.echo(
            f"{p['prjid']:<6} {p['prjname']:<20} {p['prjversion']:<8} "
            f"{p['prjpriority']:<5} {p['prjphase']:<8} {desc}"
        )


@project_group.command("show")
@click.argument("name_or_id")
def project_show(name_or_id: str) -> None:
    """Show project details.

    \b
    Examples:
      bw project show myapp
      bw project show 1
    """
    project = _get_project(name_or_id)
    if not project:
        raise click.ClickException(f"Project not found: {name_or_id}")

    click.echo(f"\n{'=' * 50}")
    click.echo(f"Project: {project['prjname']}")
    click.echo(f"{'=' * 50}")
    click.echo(f"ID:          {project['prjid']}")
    click.echo(f"Version:     {project['prjversion']}")
    click.echo(f"Priority:    {project['prjpriority']}")
    click.echo(f"Phase:       {project['prjphase']}")
    click.echo(f"Description: {project['prjdesc'] or '-'}")
    click.echo(f"Updated:     {project['prjtouchts']}")

    # Show request counts
    requests = list_requests(prjid=project["prjid"])
    if requests:
        click.echo(f"\nRequests:    {len(requests)}")
        by_status = {}
        for r in requests:
            status = r["reqstatus"]
            by_status[status] = by_status.get(status, 0) + 1
        for status, count in by_status.items():
            click.echo(f"  - {STATUS_NAMES.get(status, status)}: {count}")


@project_group.command("delete")
@click.argument("name_or_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def project_delete(name_or_id: str, force: bool) -> None:
    """Delete a project and all its requests.

    \b
    Examples:
      bw project delete myapp
      bw project delete 1 --force
    """
    project = _get_project(name_or_id)
    if not project:
        raise click.ClickException(f"Project not found: {name_or_id}")

    if not force:
        requests = list_requests(prjid=project["prjid"])
        if requests:
            click.echo(f"Warning: This will delete {len(requests)} request(s).")
        if not click.confirm(f"Delete project '{project['prjname']}'?"):
            raise click.ClickException("Aborted")

    delete_project(project["prjid"])
    click.echo(f"Project deleted: {project['prjname']}")


# =============================================================================
# Request Commands
# =============================================================================


@main.group("request")
def request_group() -> None:
    """Manage requests."""
    pass


@request_group.command("create")
@click.argument("project")
@click.option("--name", "-n", required=True, help="Request name")
@click.option("--prompt", "-m", required=True, help="Request prompt/description")
@click.option("--type", "-t", "reqtype", type=click.Choice(VALID_REQUEST_TYPES), default="new_feature")
@click.option("--priority", "-p", type=int, default=DEFAULT_PRIORITY, help="Priority (1-10)")
@click.option("--codedir", type=click.Path(path_type=Path), help="Code sandbox directory")
def request_create(
    project: str,
    name: str,
    prompt: str,
    reqtype: str,
    priority: int,
    codedir: Path | None,
) -> None:
    """Create a new request for a project.

    \b
    Examples:
      bw request create myapp -n "Add login" -m "Implement user login with OAuth"
      bw request create myapp -n "Fix bug" -m "Fix the null pointer" -t bug_fix
    """
    proj = _get_project(project)
    if not proj:
        raise click.ClickException(f"Project not found: {project}")

    try:
        reqid = create_request(
            prjid=proj["prjid"],
            reqname=name,
            reqprompt=prompt,
            reqtype=reqtype,
            reqpriority=priority,
            reqcodedir=str(codedir) if codedir else None,
        )
        click.echo(f"Request created: {name} (ID: {reqid})")
        click.echo("Phase: plan | Status: tbd")
    except Exception as e:
        raise click.ClickException(str(e))


@request_group.command("list")
@click.option("--project", "-p", "project_name", help="Filter by project")
@click.option("--status", "-s", type=click.Choice(V2_STATUSES), help="Filter by status")
@click.option("--phase", type=click.Choice(PHASES[:-1]), help="Filter by phase")
def request_list(
    project_name: str | None,
    status: str | None,
    phase: str | None,
) -> None:
    """List requests.

    \b
    Examples:
      bw request list
      bw request list --project myapp
      bw request list --status wip
      bw request list --phase dev
    """
    prjid = None
    if project_name:
        proj = _get_project(project_name)
        if not proj:
            raise click.ClickException(f"Project not found: {project_name}")
        prjid = proj["prjid"]

    requests = list_requests(prjid=prjid, status=status, phase=phase)

    if not requests:
        click.echo("No requests found.")
        return

    click.echo(f"\n{'ID':<6} {'Project':<15} {'Name':<20} {'Phase':<10} {'Status':<10} {'Type'}")
    click.echo("-" * 90)

    for r in requests:
        click.echo(
            f"{r['reqid']:<6} {r['prjname']:<15} {r['reqname'][:20]:<20} "
            f"{r['reqphase']:<10} {r['reqstatus']:<10} {r['reqtype']}"
        )


@request_group.command("show")
@click.argument("request_id", type=int)
def request_show(request_id: int) -> None:
    """Show request details.

    \b
    Examples:
      bw request show 1
    """
    req = get_request(request_id)
    if not req:
        raise click.ClickException(f"Request not found: {request_id}")

    proj = get_project(req["prjid"])

    click.echo(f"\n{'=' * 60}")
    click.echo(f"Request: {req['reqname']}")
    click.echo(f"{'=' * 60}")
    click.echo(f"ID:        {req['reqid']}")
    click.echo(f"Project:   {proj['prjname'] if proj else req['prjid']}")
    click.echo(f"Type:      {TYPE_NAMES.get(req['reqtype'], req['reqtype'])}")
    click.echo(f"Phase:     {PHASE_NAMES.get(req['reqphase'], req['reqphase'])}")
    click.echo(f"Status:    {STATUS_NAMES.get(req['reqstatus'], req['reqstatus'])}")
    click.echo(f"Priority:  {req['reqpriority']}")
    click.echo(f"Code Dir:  {req['reqcodedir'] or '-'}")
    click.echo(f"Doc Path:  {req['reqdocpath'] or '-'}")
    click.echo(f"Updated:   {req['reqtouchts']}")
    click.echo(f"\nPrompt:\n{req['reqprompt']}")


@request_group.command("update")
@click.argument("request_id", type=int)
@click.option("--status", "-s", type=click.Choice(V2_STATUSES), help="New status")
@click.option("--phase", type=click.Choice(PHASES[:-1]), help="New phase")
def request_update(
    request_id: int,
    status: str | None,
    phase: str | None,
) -> None:
    """Update a request's status or phase.

    \b
    Examples:
      bw request update 1 --status wip
      bw request update 1 --phase dev
    """
    req = get_request(request_id)
    if not req:
        raise click.ClickException(f"Request not found: {request_id}")

    if status:
        update_request_status(request_id, status)
        click.echo(f"Status updated to: {STATUS_NAMES.get(status, status)}")

    if phase:
        update_request_phase(request_id, phase)
        click.echo(f"Phase updated to: {PHASE_NAMES.get(phase, phase)}")


@request_group.command("delete")
@click.argument("request_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def request_delete(request_id: int, force: bool) -> None:
    """Delete a request.

    \b
    Examples:
      bw request delete 1
      bw request delete 1 --force
    """
    req = get_request(request_id)
    if not req:
        raise click.ClickException(f"Request not found: {request_id}")

    if not force:
        if not click.confirm(f"Delete request '{req['reqname']}'?"):
            raise click.ClickException("Aborted")

    delete_request(request_id)
    click.echo(f"Request deleted: {req['reqname']}")


# =============================================================================
# Loop Commands
# =============================================================================


@main.group("loop")
def loop_group() -> None:
    """Control the daemon loop."""
    pass


@loop_group.command("start")
@click.option("--poll", "-p", type=int, default=30, help="Poll interval in seconds")
@click.option("--log", "-l", type=str, help="Log file path pattern")
@click.option("--name", "-n", type=str, default="bwloop", help="Loop name")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
def loop_start(
    poll: int,
    log: str | None,
    name: str,
    foreground: bool,
) -> None:
    """Start the daemon loop.

    \b
    Examples:
      bw loop start
      bw loop start --foreground
      bw loop start --poll 60 --log logs/{loopname}_{today}.log
    """
    from .loop.daemon import is_daemon_running, start_daemon, write_pid_file

    if is_daemon_running():
        raise click.ClickException("Daemon is already running")

    click.echo(f"Starting BentWookie daemon (loop: {name})...")

    if foreground:
        click.echo("Running in foreground. Press Ctrl+C to stop.")
    else:
        click.echo("Running in background.")

    write_pid_file()
    start_daemon(
        poll_interval=poll,
        log_path=log,
        loop_name=name,
        foreground=foreground,
    )


@loop_group.command("stop")
def loop_stop() -> None:
    """Stop the daemon loop.

    \b
    Examples:
      bw loop stop
    """
    import os
    import signal

    from .loop.daemon import is_daemon_running, read_pid_file, remove_pid_file

    if not is_daemon_running():
        click.echo("Daemon is not running")
        return

    pid = read_pid_file()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            click.echo(f"Sent stop signal to daemon (PID: {pid})")
            remove_pid_file()
        except OSError as e:
            raise click.ClickException(f"Failed to stop daemon: {e}")
    else:
        click.echo("Could not find daemon PID")


@loop_group.command("status")
def loop_status() -> None:
    """Show daemon status.

    \b
    Examples:
      bw loop status
    """
    from .loop.daemon import is_daemon_running, read_pid_file

    if is_daemon_running():
        pid = read_pid_file()
        click.echo(f"Daemon is running (PID: {pid})")
    else:
        click.echo("Daemon is not running")


# =============================================================================
# Status Command
# =============================================================================


@main.command("status")
def status_cmd() -> None:
    """Show overall system status.

    \b
    Examples:
      bw status
    """
    from .loop.daemon import is_daemon_running, read_pid_file

    click.echo("\nBentWookie Status")
    click.echo("=" * 40)

    # Daemon status
    if is_daemon_running():
        pid = read_pid_file()
        click.echo(f"Daemon:     Running (PID: {pid})")
    else:
        click.echo("Daemon:     Stopped")

    # Database stats
    projects = list_projects()
    click.echo(f"\nProjects:   {len(projects)}")

    requests = list_requests()
    click.echo(f"Requests:   {len(requests)}")

    if requests:
        by_status = {}
        for r in requests:
            s = r["reqstatus"]
            by_status[s] = by_status.get(s, 0) + 1

        click.echo("\nRequests by status:")
        for status, count in by_status.items():
            click.echo(f"  {STATUS_NAMES.get(status, status):<15} {count}")


# =============================================================================
# Web Command
# =============================================================================


@main.command("web")
@click.option("--host", "-h", type=str, default="127.0.0.1", help="Host to bind")
@click.option("--port", "-p", type=int, default=5000, help="Port to bind")
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode")
def web_cmd(host: str, port: int, debug: bool) -> None:
    """Start the web UI.

    \b
    Examples:
      bw web
      bw web --port 8080
      bw web --host 0.0.0.0 --debug
    """
    try:
        from .web.app import create_app

        app = create_app()
        click.echo(f"Starting web UI at http://{host}:{port}")
        app.run(host=host, port=port, debug=debug)
    except ImportError:
        raise click.ClickException("Flask is required. Install with: pip install flask")


# =============================================================================
# Helpers
# =============================================================================


def _get_project(name_or_id: str) -> dict | None:
    """Get project by name or ID.

    Args:
        name_or_id: Project name or ID string.

    Returns:
        Project dict or None.
    """
    # Try as ID first
    try:
        prjid = int(name_or_id)
        return get_project(prjid)
    except ValueError:
        pass

    # Try as name
    return get_project_by_name(name_or_id)


if __name__ == "__main__":
    main()
