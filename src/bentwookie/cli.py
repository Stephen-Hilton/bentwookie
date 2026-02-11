"""CLI for BentWookie V2."""

import os
import sys
from pathlib import Path

import click

from .constants import (
    AGENT_STATUS_NAMES,
    COMPONENT_STATUS_NAMES,
    INTERVIEW_TYPE_NAMES,
    LEVEL_NAMES,
    PHASE_NAMES,
    PHASES,
    ROLE_NAMES,
    VALID_MODELS,
)
from .db.connection import get_db_path, init_db, set_db_path


def _ensure_db():
    """Ensure database is initialized."""
    if not get_db_path().exists():
        init_db()


def _find_bw_workspace() -> Path | None:
    """Walk up from cwd looking for a BW workspace."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        db_path = parent / "data" / "bentwookie.db"
        if db_path.exists():
            return parent
    return None


def _setup_workspace():
    """Set up the database path from workspace."""
    workspace = _find_bw_workspace()
    if workspace:
        os.chdir(workspace)
        set_db_path(workspace / "data" / "bentwookie.db")


def _pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


# =============================================================================
# Main CLI Group
# =============================================================================


@click.group()
@click.version_option(version="0.4.2", prog_name="BentWookie")
def main():
    """BentWookie - AI Agent Swarm Orchestration Framework."""
    _setup_workspace()


# =============================================================================
# Init
# =============================================================================


@main.command()
@click.argument("path", required=False, default=None)
def init(path: str | None):
    """Initialize a BentWookie workspace.

    Optionally specify a PATH where data files will be stored.
    Defaults to ./data if not provided.
    """
    data_dir = Path(path) if path else Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "docs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    set_db_path(data_dir / "bentwookie.db")
    init_db()

    from .settings import DEFAULT_SETTINGS, save_settings, set_settings_path
    set_settings_path(data_dir / "settings.json")

    from .settings import get_settings_path
    settings_path = get_settings_path()
    if not settings_path.exists():
        save_settings(DEFAULT_SETTINGS)

    # Copy prompt templates to data dir for user modification
    _copy_prompt_templates(data_dir)

    click.echo("BentWookie workspace initialized.")
    click.echo(f"  Data dir:  {data_dir.resolve()}")
    click.echo(f"  Database:  {data_dir / 'bentwookie.db'}")
    click.echo(f"  Settings:  {settings_path}")
    click.echo(f"  Prompts:   {data_dir / 'prompts'}")


def _copy_prompt_templates(data_dir: Path) -> None:
    """Copy prompt .md templates to the data directory for user modification."""
    import shutil

    src_prompts = Path(__file__).parent / "agents" / "prompts"
    dest_prompts = data_dir / "prompts"
    dest_prompts.mkdir(exist_ok=True)

    for src_file in src_prompts.glob("*.md"):
        dest_file = dest_prompts / src_file.name
        if not dest_file.exists():
            shutil.copy2(src_file, dest_file)


# =============================================================================
# Project Commands
# =============================================================================


@main.group()
def project():
    """Manage projects."""
    _ensure_db()


@project.command("create")
@click.argument("name")
@click.option("--desc", "-d", help="Project description")
@click.option("--codedir", "-c", help="Code directory path")
@click.option("--model", "-m", type=click.Choice(VALID_MODELS), help="Claude model")
@click.option("--max-agents", type=int, default=5, help="Max concurrent agents")
def project_create(name: str, desc: str | None, codedir: str | None, model: str | None, max_agents: int):
    """Create a new project."""
    from .db import create_project
    try:
        prjid = create_project(
            prjname=name, prjdesc=desc, prjcodedir=codedir,
            prjmodel=model, prjmaxagents=max_agents,
        )
        click.echo(f"Project created: {name} (ID: {prjid})")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command("list")
@click.option("--phase", type=click.Choice(PHASES), help="Filter by phase")
def project_list(phase: str | None):
    """List all projects."""
    from .db import list_projects
    projects = list_projects(phase=phase)
    if not projects:
        click.echo("No projects found.")
        return

    click.echo(f"{'ID':>4}  {'Name':<30}  {'Phase':<12}  {'Updated'}")
    click.echo("-" * 70)
    for p in projects:
        click.echo(f"{p['prjid']:>4}  {p['prjname']:<30}  {PHASE_NAMES.get(p['prjphase'], p['prjphase']):<12}  {p['prjtouchts'] or ''}")


@project.command("show")
@click.argument("project_id", type=int)
def project_show(project_id: int):
    """Show project details."""
    from .db import get_project, list_agents, list_components
    project = get_project(project_id)
    if not project:
        click.echo("Project not found.", err=True)
        sys.exit(1)

    cmps = list_components(prjid=project_id)
    agents = list_agents(prjid=project_id)

    click.echo(f"Project: {project['prjname']} (ID: {project['prjid']})")
    click.echo(f"  Phase: {PHASE_NAMES.get(project['prjphase'], project['prjphase'])}")
    click.echo(f"  Description: {project['prjdesc'] or 'N/A'}")
    click.echo(f"  Code Dir: {project['prjcodedir'] or 'N/A'}")
    click.echo(f"  Model: {project['prjmodel'] or 'Default'}")
    click.echo(f"  Max Agents: {project['prjmaxagents']}")
    click.echo(f"  Components: {len(cmps)}")
    click.echo(f"  Agents: {len(agents)}")


@project.command("edit")
@click.argument("project_id", type=int)
@click.option("--name", help="New name")
@click.option("--desc", help="New description")
@click.option("--codedir", help="New code directory")
@click.option("--model", type=click.Choice(VALID_MODELS), help="Claude model")
@click.option("--max-agents", type=int, help="Max concurrent agents")
def project_edit(project_id: int, **kwargs):
    """Edit a project."""
    from .db import update_project
    fields = {k: v for k, v in kwargs.items() if v is not None}
    remap = {"name": "prjname", "desc": "prjdesc", "codedir": "prjcodedir",
             "model": "prjmodel", "max_agents": "prjmaxagents"}
    fields = {remap.get(k, k): v for k, v in fields.items()}

    if not fields:
        click.echo("No changes specified.")
        return

    update_project(project_id, **fields)
    click.echo("Project updated.")


@project.command("delete")
@click.argument("project_id", type=int)
@click.confirmation_option(prompt="Are you sure you want to delete this project?")
def project_delete(project_id: int):
    """Delete a project."""
    from .db import delete_project, get_project
    p = get_project(project_id)
    if not p:
        click.echo("Project not found.", err=True)
        sys.exit(1)
    delete_project(project_id)
    click.echo(f"Deleted project: {p['prjname']}")


# =============================================================================
# Interview Commands
# =============================================================================


@main.group()
def interview():
    """Manage interviews."""
    _ensure_db()


@interview.command("start")
@click.argument("project_id", type=int)
@click.option("--type", "itvtype", type=click.Choice(["business_owner", "enterprise_architect"]),
              required=True, help="Interview type")
def interview_start(project_id: int, itvtype: str):
    """Start a new interview."""
    from .db import create_interview, get_project
    p = get_project(project_id)
    if not p:
        click.echo("Project not found.", err=True)
        sys.exit(1)

    itvid = create_interview(project_id, itvtype)
    click.echo(f"Interview started (ID: {itvid})")
    click.echo(f"  Project: {p['prjname']}")
    click.echo(f"  Type: {INTERVIEW_TYPE_NAMES[itvtype]}")
    click.echo(f"  Open in browser: bw web start, then navigate to /interviews/{itvid}")


@interview.command("list")
@click.option("--project", "prjid", type=int, help="Filter by project")
def interview_list(prjid: int | None):
    """List interviews."""
    from .db import list_interviews
    interviews = list_interviews(prjid=prjid)
    if not interviews:
        click.echo("No interviews found.")
        return

    click.echo(f"{'ID':>4}  {'Project':<20}  {'Type':<25}  {'Status':<10}  {'Messages'}")
    click.echo("-" * 80)
    for itv in interviews:
        click.echo(f"{itv['itvid']:>4}  {itv['prjname']:<20}  {INTERVIEW_TYPE_NAMES.get(itv['itvtype'], itv['itvtype']):<25}  {itv['itvstatus']:<10}  {itv['message_count']}")


@interview.command("show")
@click.argument("interview_id", type=int)
def interview_show(interview_id: int):
    """Show interview transcript."""
    from .db import get_interview, get_interview_messages
    itv = get_interview(interview_id)
    if not itv:
        click.echo("Interview not found.", err=True)
        sys.exit(1)

    click.echo(f"Interview {itv['itvid']}: {INTERVIEW_TYPE_NAMES[itv['itvtype']]}")
    click.echo(f"  Project: {itv['prjname']}")
    click.echo(f"  Status: {itv['itvstatus']}")
    click.echo()

    messages = get_interview_messages(interview_id)
    for msg in messages:
        sender = "You" if msg["imsgsender"] == "user" else "Agent"
        click.echo(f"[{sender}] {msg['imsgcontent']}")
        click.echo()


# =============================================================================
# Hierarchy Commands
# =============================================================================


@main.group()
def hierarchy():
    """View project hierarchy."""
    _ensure_db()


@hierarchy.command("show")
@click.argument("project_id", type=int)
def hierarchy_show(project_id: int):
    """Show component hierarchy for a project."""
    from .db import get_component_tree
    tree = get_component_tree(project_id)
    if not tree:
        click.echo("No components found.")
        return

    for node in tree:
        indent = "  " * node["depth"]
        status = COMPONENT_STATUS_NAMES.get(node["cmpstatus"], node["cmpstatus"])
        level = LEVEL_NAMES.get(node["cmplevel"], node["cmplevel"])
        click.echo(f"{indent}[{level}] {node['cmpname']} ({status})")


@hierarchy.command("tree")
@click.argument("project_id", type=int)
def hierarchy_tree(project_id: int):
    """Show component tree in tree format."""
    from .db import get_component_tree
    tree = get_component_tree(project_id)
    if not tree:
        click.echo("No components found.")
        return

    for node in tree:
        prefix = "  " * node["depth"]
        connector = "+-" if node["depth"] > 0 else ""
        click.echo(f"{prefix}{connector}{node['cmpname']}")


# =============================================================================
# Component Commands
# =============================================================================


@main.group()
def component():
    """View component details."""
    _ensure_db()


@component.command("show")
@click.argument("component_id", type=int)
def component_show(component_id: int):
    """Show component details."""
    from .db import get_component, get_component_children, get_dependencies
    cmp = get_component(component_id)
    if not cmp:
        click.echo("Component not found.", err=True)
        sys.exit(1)

    click.echo(f"Component: {cmp['cmpname']} (ID: {cmp['cmpid']})")
    click.echo(f"  Level: {LEVEL_NAMES.get(cmp['cmplevel'], cmp['cmplevel'])}")
    click.echo(f"  Status: {COMPONENT_STATUS_NAMES.get(cmp['cmpstatus'], cmp['cmpstatus'])}")
    click.echo(f"  Description: {cmp['cmpdesc'] or 'N/A'}")

    children = get_component_children(component_id)
    if children:
        click.echo(f"  Children ({len(children)}):")
        for ch in children:
            click.echo(f"    - {ch['cmpname']} [{ch['cmplevel']}]")

    deps = get_dependencies(component_id)
    if deps:
        click.echo(f"  Dependencies ({len(deps)}):")
        for d in deps:
            click.echo(f"    - {d['depends_on_name']} ({d['depends_on_status']})")


# =============================================================================
# Agent Commands
# =============================================================================


@main.group()
def agent():
    """Manage agents."""
    _ensure_db()


@agent.command("list")
@click.option("--project", "prjid", type=int, help="Filter by project")
@click.option("--status", type=click.Choice(["idle", "working", "waiting", "error", "terminated"]))
def agent_list(prjid: int | None, status: str | None):
    """List agents."""
    from .db import list_agents
    agents = list_agents(prjid=prjid, status=status)
    if not agents:
        click.echo("No agents found.")
        return

    click.echo(f"{'ID':>4}  {'Role':<25}  {'Status':<12}  {'Project':<20}  {'Component'}")
    click.echo("-" * 85)
    for a in agents:
        click.echo(f"{a['agtid']:>4}  {ROLE_NAMES.get(a['agtrole'], a['agtrole']):<25}  {AGENT_STATUS_NAMES.get(a['agtstatus'], a['agtstatus']):<12}  {a['prjname'] or 'N/A':<20}  {a['cmpname'] or 'N/A'}")


@agent.command("show")
@click.argument("agent_id", type=int)
def agent_show(agent_id: int):
    """Show agent details."""
    from .db import get_agent
    a = get_agent(agent_id)
    if not a:
        click.echo("Agent not found.", err=True)
        sys.exit(1)

    click.echo(f"Agent {a['agtid']}: {ROLE_NAMES.get(a['agtrole'], a['agtrole'])}")
    click.echo(f"  Status: {AGENT_STATUS_NAMES.get(a['agtstatus'], a['agtstatus'])}")
    click.echo(f"  Project: {a['prjname'] or 'N/A'}")
    click.echo(f"  Component: {a['cmpname'] or 'N/A'}")
    click.echo(f"  Model: {a['agtmodel'] or 'Default'}")
    click.echo(f"  Shell PID: {a['agtshellpid'] or 'N/A'}")
    click.echo(f"  Started: {a['agtstarted'] or 'N/A'}")
    if a.get("agterror"):
        click.echo(f"  Error: {a['agterror']}")


@agent.command("message")
@click.argument("agent_id", type=int)
@click.argument("body")
@click.option("--urgent", is_flag=True, help="Send as urgent message")
def agent_message(agent_id: int, body: str, urgent: bool):
    """Send a message to an agent."""
    from .db import create_message
    msgtype = "urgent" if urgent else "normal"
    msgid = create_message(to_agtid=agent_id, msgbody=body, msgtype=msgtype)
    click.echo(f"Message sent (ID: {msgid}, type: {msgtype})")


@agent.command("pause")
@click.argument("agent_id", type=int)
def agent_pause(agent_id: int):
    """Pause an agent."""
    from .db import update_agent
    update_agent(agent_id, agtstatus="waiting")
    click.echo(f"Agent {agent_id} paused.")


@agent.command("resume")
@click.argument("agent_id", type=int)
def agent_resume(agent_id: int):
    """Resume a paused agent."""
    from .db import update_agent
    update_agent(agent_id, agtstatus="working")
    click.echo(f"Agent {agent_id} resumed.")


@agent.command("kill")
@click.argument("agent_id", type=int)
@click.confirmation_option(prompt="Are you sure?")
def agent_kill(agent_id: int):
    """Terminate an agent."""
    from .db import update_agent
    update_agent(agent_id, agtstatus="terminated")
    click.echo(f"Agent {agent_id} terminated.")


# =============================================================================
# Build Commands
# =============================================================================


@main.group()
def build():
    """Manage build process."""
    _ensure_db()


@build.command("status")
@click.argument("project_id", type=int)
def build_status(project_id: int):
    """Show build status for a project."""
    from .db import get_build_progress
    progress = get_build_progress(project_id)
    click.echo(f"Build Progress (Project {project_id}):")
    click.echo(f"  Total tasks: {progress['total']}")
    click.echo(f"  Complete: {progress['complete']}")
    click.echo(f"  In Progress: {progress['in_progress']}")
    click.echo(f"  Pending: {progress['pending']}")
    click.echo(f"  Blocked: {progress['blocked']}")
    click.echo(f"  Errors: {progress['error']}")


@build.command("start")
@click.argument("project_id", type=int)
def build_start(project_id: int):
    """Start the build phase for a project."""
    import asyncio
    from .db import get_project, update_project
    from .agents.orchestrator import Orchestrator

    project = get_project(project_id)
    if not project:
        click.echo("Project not found.", err=True)
        sys.exit(1)

    if project["prjphase"] != "build":
        click.echo(f"Project is in '{PHASE_NAMES[project['prjphase']]}' phase. Advancing to build.")
        update_project(project_id, prjphase="build")

    click.echo(f"Starting build for project {project['prjname']}...")
    orchestrator = Orchestrator()
    try:
        asyncio.run(orchestrator.start(project_id))
    except KeyboardInterrupt:
        click.echo("\nBuild interrupted.")
    except Exception as e:
        click.echo(f"Build error: {e}", err=True)
        sys.exit(1)


@build.command("pause")
@click.argument("project_id", type=int)
def build_pause(project_id: int):
    """Pause the build."""
    from .db import get_daemon_state, set_daemon_state
    from .settings import pause_loop

    pause_loop()
    daemon = get_daemon_state()
    if daemon and daemon.get("dsstatus") == "running":
        set_daemon_state(
            pid=daemon.get("pid"),
            dsstatus="paused",
            dsphase=daemon.get("dsphase"),
            dsproject_id=project_id,
        )
    click.echo("Build paused.")


@build.command("resume")
@click.argument("project_id", type=int)
def build_resume(project_id: int):
    """Resume the build."""
    from .db import get_daemon_state, set_daemon_state
    from .settings import resume_loop

    resume_loop()
    daemon = get_daemon_state()
    if daemon and daemon.get("dsstatus") == "paused":
        set_daemon_state(
            pid=daemon.get("pid"),
            dsstatus="running",
            dsphase=daemon.get("dsphase"),
            dsproject_id=project_id,
        )
    click.echo("Build resumed.")


# =============================================================================
# Message Commands
# =============================================================================


@main.group()
def message():
    """Manage inter-agent messages."""
    _ensure_db()


@message.command("list")
@click.option("--type", "msgtype", type=click.Choice(["normal", "urgent"]))
@click.option("--status", type=click.Choice(["queued", "delivered", "read"]))
@click.option("--limit", type=int, default=20)
def message_list(msgtype: str | None, status: str | None, limit: int):
    """List messages."""
    from .db import list_messages
    msgs = list_messages(msgtype=msgtype, status=status, limit=limit)
    if not msgs:
        click.echo("No messages found.")
        return

    click.echo(f"{'ID':>4}  {'From':<15}  {'To':<15}  {'Type':<8}  {'Status':<10}  {'Body'}")
    click.echo("-" * 80)
    for m in msgs:
        body = (m["msgbody"] or "")[:40]
        click.echo(f"{m['msgid']:>4}  {m.get('from_name') or 'System':<15}  {m.get('to_name') or '?':<15}  {m['msgtype']:<8}  {m['msgstatus']:<10}  {body}")


@message.command("send")
@click.argument("to_agent_id", type=int)
@click.argument("body")
@click.option("--urgent", is_flag=True)
def message_send(to_agent_id: int, body: str, urgent: bool):
    """Send a message to an agent."""
    from .db import create_message
    msgtype = "urgent" if urgent else "normal"
    msgid = create_message(to_agtid=to_agent_id, msgbody=body, msgtype=msgtype)
    click.echo(f"Message sent (ID: {msgid})")


# =============================================================================
# System Commands
# =============================================================================


@main.group("system")
def system_cmd():
    """System management."""
    _ensure_db()


@system_cmd.command("status")
def system_status():
    """Show system status."""
    from .db import get_daemon_state, get_dashboard_stats
    from .settings import load_settings

    daemon = get_daemon_state()
    stats = get_dashboard_stats()
    settings = load_settings()

    click.echo("BentWookie System Status")
    click.echo("=" * 40)

    if daemon and daemon.get("dsstatus") == "running":
        pid = daemon.get("pid")
        alive = _pid_alive(pid) if pid else False
        if alive:
            click.echo(f"Orchestrator: Running (PID: {pid})")
        else:
            click.echo(f"Orchestrator: Stale (PID {pid} not running)")
    elif daemon and daemon.get("dsstatus") == "paused":
        click.echo("Orchestrator: Paused")
    else:
        click.echo("Orchestrator: Stopped")

    click.echo(f"\nProjects: {stats['projects']}")
    click.echo(f"Active Agents: {stats['active_agents']}")
    click.echo(f"Idle Agents: {stats['idle_agents']}")
    click.echo(f"Error Agents: {stats['error_agents']}")
    click.echo(f"Pending Messages: {stats['pending_messages']}")
    click.echo(f"\nModel: {settings.get('model', 'default')}")
    click.echo(f"Max Agents: {settings.get('max_concurrent_agents', 5)}")


@system_cmd.command("start")
@click.argument("project_id", type=int)
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (no daemon)")
def system_start(project_id: int, foreground: bool):
    """Start the orchestrator for a project."""
    import asyncio
    import signal

    from .db import get_daemon_state, get_project
    from .agents.orchestrator import Orchestrator

    project = get_project(project_id)
    if not project:
        click.echo("Project not found.", err=True)
        sys.exit(1)

    # Check for existing running daemon
    daemon = get_daemon_state()
    if daemon and daemon.get("dsstatus") == "running":
        pid = daemon.get("pid")
        if pid and _pid_alive(pid):
            click.echo(f"Orchestrator already running (PID: {pid}).", err=True)
            sys.exit(1)

    if foreground:
        click.echo(f"Starting orchestrator for '{project['prjname']}' (foreground)...")
        orchestrator = Orchestrator()
        try:
            asyncio.run(orchestrator.start(project_id))
        except KeyboardInterrupt:
            click.echo("\nOrchestrator interrupted.")
        except Exception as e:
            click.echo(f"Orchestrator error: {e}", err=True)
            sys.exit(1)
        return

    # Daemonize: fork a child process
    child_pid = os.fork()
    if child_pid > 0:
        # Parent process
        click.echo(f"Orchestrator started for '{project['prjname']}' (PID: {child_pid})")
        return

    # Child process: detach from terminal
    os.setsid()
    # Redirect stdio to /dev/null
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)

    signal.signal(signal.SIGTERM, lambda *_: None)  # let finally block run

    orchestrator = Orchestrator()
    try:
        asyncio.run(orchestrator.start(project_id))
    except Exception:
        pass
    finally:
        os._exit(0)


@system_cmd.command("stop")
def system_stop():
    """Stop the running orchestrator."""
    import signal

    from .db import clear_daemon_state, get_daemon_state

    daemon = get_daemon_state()
    if not daemon or daemon.get("dsstatus") != "running":
        click.echo("No running orchestrator to stop.")
        return

    pid = daemon.get("pid")
    if pid and _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            click.echo(f"Sent SIGTERM to orchestrator (PID: {pid}).")
        except ProcessLookupError:
            click.echo(f"PID {pid} already gone.")
    else:
        click.echo(f"Orchestrator PID {pid} is not running. Cleaning up state.")

    clear_daemon_state()
    click.echo("Orchestrator stopped.")


@system_cmd.command("config")
@click.option("--model", type=click.Choice(VALID_MODELS))
@click.option("--max-agents", type=int)
@click.option("--poll-interval", type=int)
@click.option("--agent-timeout", type=int)
def system_config(model: str | None, max_agents: int | None, poll_interval: int | None, agent_timeout: int | None):
    """Update system configuration."""
    from .settings import load_settings, save_settings

    settings = load_settings()
    changed = False

    if model:
        settings["model"] = model
        changed = True
    if max_agents is not None:
        settings["max_concurrent_agents"] = max_agents
        changed = True
    if poll_interval is not None:
        settings["poll_interval"] = poll_interval
        changed = True
    if agent_timeout is not None:
        settings["agent_timeout"] = agent_timeout
        changed = True

    if changed:
        save_settings(settings)
        click.echo("Configuration updated.")
    else:
        click.echo("Current configuration:")
        for k, v in settings.items():
            click.echo(f"  {k}: {v}")


# =============================================================================
# Web Commands
# =============================================================================


@main.group()
def web():
    """Web UI management."""
    _ensure_db()


@web.command("start")
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", "-p", default=None, type=int, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def web_start(host: str | None, port: int | None, debug: bool):
    """Start the BentWookie web UI."""
    from .settings import get_web_host, get_web_port
    from .web.app import create_app

    host = host or get_web_host()
    port = port or get_web_port()

    app = create_app()
    click.echo(f"Starting BentWookie web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


@web.command("status")
def web_status():
    """Check web UI status."""
    from .settings import get_web_host, get_web_port
    host = get_web_host()
    port = get_web_port()
    click.echo(f"Web UI configured at http://{host}:{port}")
