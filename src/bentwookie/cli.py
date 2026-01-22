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
    VALID_PROVIDERS,
    VALID_REQUEST_TYPES,
    VALID_VERSIONS,
)
from .db import (
    add_infra_option,
    add_learning,
    create_project,
    create_request,
    delete_infra_option,
    delete_learning,
    delete_project,
    delete_request,
    get_infra_options,
    get_learning,
    get_project,
    get_project_by_name,
    get_request,
    init_db,
    list_all_learnings,
    list_projects,
    list_requests,
    seed_default_infra_options,
    update_learning,
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


# =============================================================================
# Workspace Detection
# =============================================================================


def is_bw_workspace(path: Path) -> bool:
    """Check if a directory looks like a BentWookie workspace.

    Args:
        path: Path to check.

    Returns:
        True if path appears to be a BentWookie workspace.
    """
    # Must have data/ directory with expected files
    data_dir = path / "data"
    if not data_dir.exists():
        return False

    # Check for key files that indicate initialization
    db_file = data_dir / "bentwookie.db"
    settings_file = data_dir / "settings.json"

    # Must have at least one of these
    return db_file.exists() or settings_file.exists()


def find_bw_workspace() -> Path | None:
    """Find BentWookie workspace by checking CWD, parent, and children.

    Returns:
        Path to workspace root, or None if not found.
    """
    cwd = Path.cwd()

    # Check current directory
    if is_bw_workspace(cwd):
        return cwd

    # Check parent directory
    parent = cwd.parent
    if parent != cwd and is_bw_workspace(parent):
        return parent

    # Check immediate children (one level only)
    try:
        for child in cwd.iterdir():
            if child.is_dir() and is_bw_workspace(child):
                return child
    except PermissionError:
        pass

    return None


def ensure_bw_workspace() -> Path:
    """Ensure we're in a BentWookie workspace or can find one.

    Raises:
        click.ClickException: If no workspace found.

    Returns:
        Path to workspace root.
    """
    workspace = find_bw_workspace()
    if workspace is None:
        raise click.ClickException(
            "No initialized BentWookie workspace found.\n\n"
            "Searched:\n"
            "  - Current directory\n"
            "  - Parent directory\n"
            "  - Child directories\n\n"
            "Run 'bw init' to initialize this directory as a BentWookie workspace."
        )

    # Change to workspace directory if not already there
    if workspace != Path.cwd():
        import os
        os.chdir(workspace)
        click.echo(f"Using BentWookie workspace: {workspace}", err=True)

    return workspace


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """"I bent my wookie."  - Ralph Wiggum

    BentWookie - AI coding loop that manages development requests through
    various phases using the Claude Agent SDK for execution, using centrally
    managed deployment and infrastructure configurations.

    \b
    Quick Start:
      bw init                          # Initialize database
      bw project create myproject      # Create a project
      bw request create myproject      # Create a request
      bw loop start                    # Start the daemon
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
@click.option(
    "--auth",
    type=click.Choice(["api", "max"]),
    help="Authentication mode: 'api' (ANTHROPIC_API_KEY) or 'max' (Claude Max subscription)",
)
def init_cmd(db_path: Path, auth: str | None) -> None:
    """Initialize the BentWookie database and directories.

    \b
    Examples:
      bw init
      bw init --auth max
      bw init --auth api
      bw init --db-path ./mydata/bw.db
    """
    from .db.connection import set_db_path
    from .settings import AUTH_MODE_API, AUTH_MODE_MAX, save_settings, load_settings

    # Set custom database path if provided
    if db_path != Path("data/bentwookie.db"):
        set_db_path(db_path)

    # Ensure directories exist
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/docs").mkdir(parents=True, exist_ok=True)
    Path("data/prompts/phases").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Copy template files from package to data/prompts/
    import shutil
    template_src_dir = Path(__file__).parent / "templates" / "phases"
    template_dst_dir = Path("data/prompts/phases")

    phase_names = ["plan", "dev", "test", "deploy", "verify", "document", "commit"]
    templates_copied = 0

    for phase in phase_names:
        src = template_src_dir / f"{phase}.md"
        dst = template_dst_dir / f"{phase}.md"
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            templates_copied += 1

    # Copy system prompt template
    system_src = Path(__file__).parent / "templates" / "system.md"
    system_dst = Path("data/prompts/system.md")
    if system_src.exists() and not system_dst.exists():
        shutil.copy2(system_src, system_dst)
        templates_copied += 1

    if templates_copied > 0:
        click.echo(f"  ✓ Copied {templates_copied} prompt templates to data/prompts/")

    # Initialize database
    init_db()

    # Create BentWookie project (ID: 1) for auto-generated bug-fix requests
    try:
        from .db import get_project
        if not get_project(1):
            create_project(
                prjname="BentWookie",
                prjdesc="BentWookie self-management project for auto-generated bug-fix requests",
                prjversion="v1",
                prjpriority=1,
            )
    except Exception:
        pass  # Project may already exist

    # Handle auth mode
    if auth is None:
        # Interactive prompt
        click.echo("\nAuthentication mode:")
        click.echo("  1. max - Claude Max subscription (web auth, no API key needed)")
        click.echo("  2. api - API key (requires ANTHROPIC_API_KEY env var)")
        choice = click.prompt("Select auth mode", type=click.Choice(["max", "api"]), default="max")
        auth = choice

    # Save settings
    settings = load_settings()
    settings["auth_mode"] = auth
    save_settings(settings)

    click.echo(f"\nDatabase initialized at: {db_path}")
    click.echo(f"Auth mode: {auth}")
    click.echo("Created directories: data/, data/docs/, data/prompts/, logs/")
    click.echo("\nℹ️  Prompt templates in data/prompts/ can be customized - changes take effect immediately")

    if auth == AUTH_MODE_API:
        click.echo("\nNote: Set ANTHROPIC_API_KEY environment variable before running the daemon.")
    else:
        click.echo("\nNote: Using Claude Max subscription. Ensure you've run 'claude' and authenticated.")

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
@click.option("--codedir", "-c", type=click.Path(path_type=Path), help="Code directory path")
@click.option("--prompt", "-m", type=str, help="Project-level prompt/guidelines")
@click.option("--claude-md", type=click.Path(exists=True), help="Path to claude.md file for project")
@click.option("--model", type=click.Choice(VALID_MODELS), help="Claude model override (uses global setting if not specified)")
@click.option("--commit/--no-commit", default=None, help="Enable/disable commit phase (overrides global)")
@click.option("--commit-branch", type=click.Choice(["current", "other"]), help="Commit branch mode")
@click.option("--commit-branch-name", type=str, help="Branch name when mode=other")
def project_create(
    name: str,
    version: str,
    priority: int,
    phase: str,
    desc: str | None,
    codedir: Path | None,
    prompt: str | None,
    claude_md: Path | None,
    model: str | None,
    commit: bool | None,
    commit_branch: str | None,
    commit_branch_name: str | None,
) -> None:
    """Create a new project.

    \b
    Examples:
      bw project create myapp
      bw project create myapp --version mvp --priority 3
      bw project create myapp -d "My awesome app"
      bw project create myapp --codedir /path/to/code
      bw project create myapp --prompt "Use type hints and docstrings"
      bw project create myapp --claude-md /path/to/claude.md
    """
    # Convert commit bool to int (None=use global, True=1, False=0)
    prjcommitenabled = None if commit is None else (1 if commit else 0)

    try:
        prjid = create_project(
            prjname=name,
            prjversion=version,
            prjpriority=priority,
            prjphase=phase,
            prjdesc=desc,
            prjcodedir=str(codedir) if codedir else None,
            prjprompt=prompt,
            prjclaudemd=str(claude_md) if claude_md else None,
            prjmodel=model,
            prjcommitenabled=prjcommitenabled,
            prjcommitbranchmode=commit_branch,
            prjcommitbranchname=commit_branch_name,
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
    ensure_bw_workspace()
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
    ensure_bw_workspace()
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
    click.echo(f"Code Dir:    {project.get('prjcodedir') or '-'}")
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
    ensure_bw_workspace()
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
@click.option("--commit/--no-commit", default=None, help="Override commit phase for this request")
@click.option("--commit-branch", help="Branch name for commit (overrides global)")
def request_create(
    project: str,
    name: str,
    prompt: str,
    reqtype: str,
    priority: int,
    codedir: Path | None,
    commit: bool | None,
    commit_branch: str | None,
) -> None:
    """Create a new request for a project.

    \b
    Examples:
      bw request create myapp -n "Add login" -m "Implement user login with OAuth"
      bw request create myapp -n "Fix bug" -m "Fix the null pointer" -t bug_fix
      bw request create myapp -n "Update" -m "Update docs" --no-commit
      bw request create myapp -n "Feature" -m "New feature" --commit-branch develop
    """
    proj = _get_project(project)
    if not proj:
        raise click.ClickException(f"Project not found: {project}")

    # Convert commit bool to int (0=disabled, 1=default, 2=forced)
    reqcommitenabled = None
    if commit is not None:
        reqcommitenabled = 2 if commit else 0

    try:
        reqid = create_request(
            prjid=proj["prjid"],
            reqname=name,
            reqprompt=prompt,
            reqtype=reqtype,
            reqpriority=priority,
            reqcodedir=str(codedir) if codedir else None,
            reqcommitenabled=reqcommitenabled,
            reqcommitbranch=commit_branch,
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
    ensure_bw_workspace()
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
# Learning Commands
# =============================================================================

GLOBAL_PROJECT_ID = -1


@main.group("learning")
def learning_group() -> None:
    """Manage learnings (project-specific or global)."""
    pass


@learning_group.command("list")
@click.option("--project", "-p", "project_name", help="Filter by project name (use 'global' for global learnings)")
def learning_list(project_name: str | None) -> None:
    """List learnings.

    \b
    Examples:
      bw learning list                  # List all learnings
      bw learning list --project myapp  # List learnings for myapp
      bw learning list --project global # List global learnings only
    """
    prjid = None
    if project_name:
        if project_name.lower() == "global":
            prjid = GLOBAL_PROJECT_ID
        else:
            proj = _get_project(project_name)
            if not proj:
                raise click.ClickException(f"Project not found: {project_name}")
            prjid = proj["prjid"]

    learnings = list_all_learnings(prjid=prjid)

    if not learnings:
        click.echo("No learnings found.")
        return

    click.echo(f"\n{'ID':<6} {'Project':<15} {'Description':<50} {'Updated'}")
    click.echo("-" * 95)

    for l in learnings:
        desc = (l["lrndesc"] or "")[:50]
        prjname = l.get("prjname", "Global") if l["prjid"] != GLOBAL_PROJECT_ID else "Global"
        updated = str(l["lrntouchts"])[:19] if l["lrntouchts"] else "-"
        click.echo(f"{l['lrnid']:<6} {prjname:<15} {desc:<50} {updated}")


@learning_group.command("show")
@click.argument("learning_id", type=int)
def learning_show(learning_id: int) -> None:
    """Show learning details.

    \b
    Examples:
      bw learning show 1
    """
    learning = get_learning(learning_id)
    if not learning:
        raise click.ClickException(f"Learning not found: {learning_id}")

    prjname = learning.get("prjname", "Global") if learning["prjid"] != GLOBAL_PROJECT_ID else "Global"

    click.echo(f"\n{'=' * 60}")
    click.echo(f"Learning #{learning['lrnid']}")
    click.echo(f"{'=' * 60}")
    click.echo(f"Project:  {prjname} (ID: {learning['prjid']})")
    click.echo(f"Updated:  {learning['lrntouchts']}")
    click.echo(f"\nDescription:\n{learning['lrndesc']}")


@learning_group.command("add")
@click.argument("project")
@click.option("--message", "-m", required=True, help="Learning description")
def learning_add(project: str, message: str) -> None:
    """Add a learning to a project or globally.

    Use 'global' as the project name to add a global learning that
    applies to all projects.

    \b
    Examples:
      bw learning add myapp -m "Always run tests before deploy"
      bw learning add global -m "Use async for I/O operations"
    """
    if project.lower() == "global":
        prjid = GLOBAL_PROJECT_ID
        prjname = "Global"
    else:
        proj = _get_project(project)
        if not proj:
            raise click.ClickException(f"Project not found: {project}")
        prjid = proj["prjid"]
        prjname = proj["prjname"]

    lrnid = add_learning(prjid=prjid, lrndesc=message)
    click.echo(f"Learning added to {prjname} (ID: {lrnid})")


@learning_group.command("update")
@click.argument("learning_id", type=int)
@click.option("--message", "-m", required=True, help="New learning description")
def learning_update(learning_id: int, message: str) -> None:
    """Update a learning's description.

    \b
    Examples:
      bw learning update 1 -m "Updated learning text"
    """
    learning = get_learning(learning_id)
    if not learning:
        raise click.ClickException(f"Learning not found: {learning_id}")

    update_learning(learning_id, message)
    click.echo(f"Learning #{learning_id} updated")


@learning_group.command("delete")
@click.argument("learning_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def learning_delete(learning_id: int, force: bool) -> None:
    """Delete a learning.

    \b
    Examples:
      bw learning delete 1
      bw learning delete 1 --force
    """
    learning = get_learning(learning_id)
    if not learning:
        raise click.ClickException(f"Learning not found: {learning_id}")

    if not force:
        desc_preview = (learning["lrndesc"] or "")[:50]
        if not click.confirm(f"Delete learning '{desc_preview}...'?"):
            raise click.ClickException("Aborted")

    delete_learning(learning_id)
    click.echo(f"Learning #{learning_id} deleted")


# =============================================================================
# Infrastructure Options Commands (Wizard Selectable Options)
# =============================================================================

VALID_OPTION_TYPES = ["compute", "storage", "queue", "access"]


@main.group("infra-options")
def infra_options_group() -> None:
    """Manage wizard infrastructure options (compute, storage, queue, access)."""
    pass


@infra_options_group.command("list")
@click.option("--type", "-t", "opttype", type=click.Choice(VALID_OPTION_TYPES), help="Filter by type")
def infra_options_list(opttype: str | None) -> None:
    """List infrastructure options available in the wizard.

    \b
    Examples:
      bw infra-options list                # List all options
      bw infra-options list --type compute # List compute options only
    """
    options = get_infra_options(opttype)

    if not options:
        if opttype:
            click.echo(f"No {opttype} options found. Use 'bw infra-options seed' to load defaults.")
        else:
            click.echo("No infrastructure options found. Use 'bw infra-options seed' to load defaults.")
        return

    click.echo(f"\n{'ID':<6} {'Type':<10} {'Name':<25} {'Provider':<12} {'Order'}")
    click.echo("-" * 65)

    current_type = None
    for opt in options:
        if opttype is None and opt["opttype"] != current_type:
            if current_type is not None:
                click.echo("")  # Blank line between types
            current_type = opt["opttype"]
        click.echo(
            f"{opt['optid']:<6} {opt['opttype']:<10} {opt['optname']:<25} "
            f"{opt['optprovider']:<12} {opt['optsortorder']}"
        )


@infra_options_group.command("add")
@click.argument("opttype", type=click.Choice(VALID_OPTION_TYPES))
@click.argument("name")
@click.option("--provider", "-p", type=click.Choice(VALID_PROVIDERS), default="local", help="Provider hint")
@click.option("--order", "-o", type=int, default=99, help="Sort order (lower = first)")
def infra_options_add(opttype: str, name: str, provider: str, order: int) -> None:
    """Add an infrastructure option to the wizard.

    \b
    Examples:
      bw infra-options add compute "My Custom Server"
      bw infra-options add storage "AWS Aurora" --provider aws
      bw infra-options add queue "RabbitMQ" --provider container --order 5
    """
    try:
        optid = add_infra_option(
            opttype=opttype,
            optname=name,
            optprovider=provider,
            optsortorder=order,
        )
        click.echo(f"Added {opttype} option: '{name}' (ID: {optid})")
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise click.ClickException(f"Option '{name}' already exists for {opttype}")
        raise click.ClickException(str(e))


@infra_options_group.command("remove")
@click.argument("opttype", type=click.Choice(VALID_OPTION_TYPES))
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def infra_options_remove(opttype: str, name: str, force: bool) -> None:
    """Remove an infrastructure option from the wizard.

    \b
    Examples:
      bw infra-options remove compute "AWS Lambda"
      bw infra-options remove storage "Local" --force
    """
    if not force:
        if not click.confirm(f"Remove {opttype} option '{name}'?"):
            raise click.ClickException("Aborted")

    if delete_infra_option(opttype, name):
        click.echo(f"Removed {opttype} option: '{name}'")
    else:
        raise click.ClickException(f"Option '{name}' not found for {opttype}")


@infra_options_group.command("seed")
@click.option("--force", "-f", is_flag=True, help="Seed even if options already exist")
def infra_options_seed(force: bool) -> None:
    """Seed default infrastructure options from constants.

    This loads the built-in options (Local, AWS Lambda, AWS S3, etc.)
    into the database. Only works if no options exist yet, unless --force is used.

    \b
    Examples:
      bw infra-options seed
      bw infra-options seed --force  # Re-seed (adds duplicates if not careful)
    """
    existing = get_infra_options()
    if existing and not force:
        click.echo(f"Options already exist ({len(existing)} found). Use --force to add anyway.")
        return

    count = seed_default_infra_options()
    if count > 0:
        click.echo(f"Seeded {count} default infrastructure options.")
    else:
        click.echo("No options added (defaults may already exist).")


@infra_options_group.command("clear")
@click.option("--type", "-t", "opttype", type=click.Choice(VALID_OPTION_TYPES), help="Clear only this type")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def infra_options_clear(opttype: str | None, force: bool) -> None:
    """Clear all infrastructure options (or by type).

    \b
    Examples:
      bw infra-options clear                # Clear all options
      bw infra-options clear --type compute # Clear only compute options
    """
    options = get_infra_options(opttype)

    if not options:
        click.echo("No options to clear.")
        return

    type_desc = f"{opttype} " if opttype else ""
    if not force:
        if not click.confirm(f"Clear {len(options)} {type_desc}infrastructure options?"):
            raise click.ClickException("Aborted")

    count = 0
    for opt in options:
        if delete_infra_option(opt["opttype"], opt["optname"]):
            count += 1

    click.echo(f"Cleared {count} {type_desc}options.")


# =============================================================================
# Loop Commands
# =============================================================================


@main.group("loop")
def loop_group() -> None:
    """Control the daemon loop."""
    pass


@loop_group.command("start")
@click.option("--poll", "-p", type=int, default=30, help="Poll interval in seconds")
@click.option("--log", "-l", type=str, help="Log file path pattern (default: logs/{loopname}_{today}.log)")
@click.option("--name", "-n", type=str, default="bwloop", help="Loop name")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging")
def loop_start(
    poll: int,
    log: str | None,
    name: str,
    foreground: bool,
    debug: bool,
) -> None:
    """Start the daemon loop.

    \b
    Examples:
      bw loop start
      bw loop start --foreground
      bw loop start --foreground --debug
      bw loop start --poll 60 --log logs/{loopname}_{today}.log
    """
    ensure_bw_workspace()

    from .loop.daemon import start_daemon

    click.echo(f"Starting BentWookie daemon (loop: {name})...")
    if debug:
        click.echo("Debug logging enabled")

    if foreground:
        click.echo("Running in foreground. Press Ctrl+C to stop.")
    else:
        click.echo("Running in background.")

    # start_daemon handles PID file and checks if already running
    started = start_daemon(
        poll_interval=poll,
        log_path=log,
        loop_name=name,
        foreground=foreground,
        debug=debug,
    )
    if not started:
        raise click.ClickException("Failed to start daemon (may already be running)")


@loop_group.command("stop")
def loop_stop() -> None:
    """Stop the daemon loop.

    \b
    Examples:
      bw loop stop
    """
    ensure_bw_workspace()

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
    ensure_bw_workspace()

    from .loop.daemon import is_daemon_running, read_pid_file
    from .settings import get_loop_settings

    if is_daemon_running():
        pid = read_pid_file()
        click.echo(f"Daemon is running (PID: {pid})")
    else:
        click.echo("Daemon is not running")

    # Show loop settings
    settings = get_loop_settings()
    click.echo(f"\nLoop Settings:")
    click.echo(f"  Paused:         {'Yes' if settings['loop_paused'] else 'No'}")
    click.echo(f"  Max Iterations: {settings['max_iterations'] or 'Unlimited'}")
    click.echo(f"  Poll Interval:  {settings['poll_interval']}s")


@loop_group.command("pause")
def loop_pause() -> None:
    """Pause the daemon loop.

    \b
    Examples:
      bw loop pause
    """
    from .settings import pause_loop

    pause_loop()
    click.echo("Loop paused. The daemon will stop processing after the current request.")


@loop_group.command("resume")
def loop_resume() -> None:
    """Resume the daemon loop.

    \b
    Examples:
      bw loop resume
    """
    from .settings import resume_loop

    resume_loop()
    click.echo("Loop resumed. The daemon will continue processing requests.")


@loop_group.command("config")
@click.option("--poll-interval", "-p", type=int, help="Poll interval in seconds")
@click.option("--max-iterations", "-m", type=int, help="Max iterations (0 = unlimited)")
@click.option("--show", is_flag=True, help="Show current settings")
def loop_config(poll_interval: int | None, max_iterations: int | None, show: bool) -> None:
    """Configure loop settings.

    \b
    Examples:
      bw loop config --show
      bw loop config --poll-interval 60
      bw loop config --max-iterations 100
      bw loop config -p 30 -m 0
    """
    from .settings import get_loop_settings, update_loop_settings

    if poll_interval is not None or max_iterations is not None:
        settings = update_loop_settings(
            poll_interval=poll_interval,
            max_iterations=max_iterations,
        )
        click.echo("Loop settings updated:")
    else:
        settings = get_loop_settings()
        click.echo("Current loop settings:")

    click.echo(f"  Paused:         {'Yes' if settings['loop_paused'] else 'No'}")
    click.echo(f"  Max Iterations: {settings['max_iterations'] or 'Unlimited'}")
    click.echo(f"  Poll Interval:  {settings['poll_interval']}s")


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
    ensure_bw_workspace()

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
    ensure_bw_workspace()

    try:
        from .web.app import create_app

        app = create_app()
        click.echo(f"Starting web UI at http://{host}:{port}")
        app.run(host=host, port=port, debug=debug)
    except ImportError:
        raise click.ClickException("Flask is required. Install with: pip install flask")


# =============================================================================
# Config Command
# =============================================================================


@main.command("config")
@click.option("--auth", type=click.Choice(["api", "max"]), help="Set auth mode")
@click.option("--doc-retention", type=int, help="Days to retain docs (0 = keep forever)")
@click.option("--commit/--no-commit", default=None, help="Enable/disable commit phase")
@click.option("--commit-branch", type=click.Choice(["current", "other"]), help="Commit branch mode")
@click.option("--commit-branch-name", help="Branch name (when mode=other)")
@click.option("--show", is_flag=True, help="Show current settings")
def config_cmd(
    auth: str | None,
    doc_retention: int | None,
    commit: bool | None,
    commit_branch: str | None,
    commit_branch_name: str | None,
    show: bool,
) -> None:
    """View or update configuration.

    \b
    Examples:
      bw config --show
      bw config --auth max
      bw config --auth api
      bw config --doc-retention 30
      bw config --doc-retention 0    # Disable auto-cleanup
      bw config --commit              # Enable commit phase
      bw config --no-commit           # Disable commit phase
      bw config --commit-branch current
      bw config --commit-branch other --commit-branch-name main
    """
    from .settings import (
        load_settings,
        save_settings,
        set_doc_retention_days,
        set_commit_enabled,
        set_commit_branch_mode,
        set_commit_branch_name,
    )

    settings = load_settings()
    made_changes = False

    if auth:
        settings["auth_mode"] = auth
        save_settings(settings)
        click.echo(f"Auth mode set to: {auth}")
        if auth == "api":
            click.echo("Note: Ensure ANTHROPIC_API_KEY is set.")
        else:
            click.echo("Note: Using Claude Max subscription (web auth).")
        made_changes = True

    if doc_retention is not None:
        set_doc_retention_days(doc_retention)
        if doc_retention == 0:
            click.echo("Doc retention: disabled (keeping forever)")
        else:
            click.echo(f"Doc retention set to: {doc_retention} days")
        made_changes = True

    if commit is not None:
        set_commit_enabled(commit)
        click.echo(f"Commit phase: {'enabled' if commit else 'disabled'}")
        made_changes = True

    if commit_branch:
        set_commit_branch_mode(commit_branch)
        click.echo(f"Commit branch mode: {commit_branch}")
        made_changes = True

    if commit_branch_name is not None:
        set_commit_branch_name(commit_branch_name)
        click.echo(f"Commit branch name: {commit_branch_name or '(none)'}")
        made_changes = True

    if show or not made_changes:
        settings = load_settings()  # Reload to get updated values

        # Setting descriptions
        descriptions = {
            "auth_mode": "Authentication mode (api = API key, max = Claude Max subscription)",
            "model": "Claude model to use for all requests",
            "max_turns": "Max Claude API calls per phase (prevents runaway loops)",
            "poll_interval": "Seconds between daemon polls for new requests",
            "loop_paused": "Whether daemon is paused (skips processing if True)",
            "max_iterations": "Max requests to process before stopping (0 = unlimited)",
            "doc_retention_days": "Days to keep generated docs (0 = keep forever)",
            "commit_enabled": "Enable commit phase globally",
            "commit_branch_mode": "Commit to 'current' branch or 'other' (specific branch)",
            "commit_branch_name": "Specific branch name (when mode = other)",
        }

        click.echo("\nCurrent Settings:")
        click.echo("-" * 80)

        # Find max key length for alignment
        max_key_len = max(len(key) for key in settings.keys())
        max_value_len = max(len(str(value)) for value in settings.values())

        for key, value in settings.items():
            desc = descriptions.get(key, "")
            # Format: key: value  <- description
            key_value = f"{key}: {value}".ljust(max_key_len + max_value_len + 2)
            if desc:
                click.echo(f"  {key_value}  <- {desc}")
            else:
                click.echo(f"  {key_value}")


# =============================================================================
# Wizard Command
# =============================================================================


@main.command("wizard")
@click.argument("name", required=False)
def wizard_cmd(name: str | None) -> None:
    """Interactive wizard to create a new request.

    Guides you through creating a project (if needed) and a request
    with infrastructure preferences.

    \b
    Examples:
      bw wizard
      bw wizard "Add user authentication"
    """
    try:
        from .wizard import wizard

        wizard(feature_name=name)
    except ImportError as e:
        if "questionary" in str(e):
            raise click.ClickException(
                "The wizard requires 'questionary'. Install with: pip install questionary"
            )
        raise click.ClickException(str(e))


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
