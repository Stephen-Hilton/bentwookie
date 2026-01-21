# BentWookie

> "I bent my Wookie." -- Ralph Wiggum

An AI coding loop workflow manager that guides development requests through phases from planning to deployment, powered by the Claude Agent SDK.

## QuickStart

```bash
# Install
git clone https://github.com/bentwookie/bentwookie.git
cd bentwookie
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Initialize and create your first project
bw init
bw project create myapp --desc "My application"
bw request create myapp -n "Add login" -m "Implement user authentication"

# Start processing (foreground mode)
bw loop start --foreground

# Or use the web UI
bw web
```

## Overview

BentWookie v2 provides:

- **SQLite Database**: Persistent state management for projects and requests
- **Claude Agent SDK Integration**: Automated processing through development phases
- **Phase-Based Workflow**: plan → dev → test → deploy → verify → document
- **CLI Interface**: Full control via command line
- **Web UI**: Browser-based dashboard for managing projects and requests
- **Daemon Mode**: Background processing of queued requests

## Installation

```bash
# Clone the repository
git clone https://github.com/bentwookie/bentwookie.git
cd bentwookie

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Or install with dev dependencies (pytest, ruff, mypy, etc.)
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- SQLite (included with Python)
- Claude Agent SDK (`claude-agent-sdk`) - installed automatically
- Flask (for web UI) - installed automatically

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | **Required** - API key for Claude (get one at [console.anthropic.com](https://console.anthropic.com)) |

## CLI Commands

### Initialization

```bash
bw init                      # Initialize database and directories
bw init --db-path ./my.db    # Use custom database path
```

### Project Management

```bash
bw project create <name>              # Create a project
bw project create <name> -d "desc"    # With description
bw project create <name> -v mvp       # Set version (poc, mvp, v1, v1.1, v2)
bw project create <name> -p 3         # Set priority (1-10, lower = higher)

bw project list                       # List all projects
bw project list --phase dev           # Filter by phase (dev, qa, uat, prod)

bw project show <name|id>             # Show project details
bw project delete <name|id>           # Delete project (and all requests)
bw project delete <name> --force      # Skip confirmation
```

### Request Management

```bash
bw request create <project> -n "Name" -m "Prompt"    # Create request
bw request create <project> -n "Fix bug" -m "..." -t bug_fix
bw request create <project> -n "Add feature" -m "..." --priority 2

bw request list                       # List all requests
bw request list --project myapp       # Filter by project
bw request list --status wip          # Filter by status (tbd, wip, done, err, tmout)
bw request list --phase dev           # Filter by phase

bw request show <id>                  # Show request details
bw request update <id> --status wip   # Update status
bw request update <id> --phase dev    # Update phase
bw request delete <id>                # Delete request
```

### Daemon Control

```bash
bw loop start                    # Start daemon (background)
bw loop start --foreground       # Start in foreground (see output)
bw loop start --poll 60          # Custom poll interval (seconds)
bw loop start --log logs/bw.log  # Custom log file

bw loop stop                     # Stop the daemon
bw loop status                   # Check if daemon is running
```

### Status & Web UI

```bash
bw status                        # Show system status
bw web                           # Start web UI (http://127.0.0.1:5000)
bw web --port 8080               # Custom port
bw web --host 0.0.0.0 --debug    # Public access with debug mode
```

## How It Works

### Request Phases

Requests progress through these phases automatically:

| Phase | Description | Tools Available |
|-------|-------------|-----------------|
| `plan` | Analyze requirements, create implementation plan | Read, Glob, Grep |
| `dev` | Implement the changes | Read, Write, Edit, Bash, Glob, Grep |
| `test` | Run tests, verify quality | Read, Bash, Glob, Grep |
| `deploy` | Deploy to target environment | Bash |
| `verify` | Verify deployment success | Read, Bash, WebFetch, Glob, Grep |
| `document` | Update documentation | Read, Write |
| `complete` | Request finished | - |

### Request Statuses

| Status | Code | Description |
|--------|------|-------------|
| Pending | `tbd` | Waiting to be processed |
| In Progress | `wip` | Currently being processed |
| Done | `done` | Completed successfully |
| Error | `err` | Failed with error |
| Timeout | `tmout` | Exceeded time limit |

### Request Types

- `new_feature` - New functionality
- `bug_fix` - Fix for existing bug
- `enhancement` - Improvement to existing feature

## Web UI

The web interface provides:

- **Dashboard**: Overview of projects, requests, and status counts
- **Projects**: Create, view, and manage projects
- **Requests**: Create, filter, and update requests
- **Status**: Daemon status and system health

Access at `http://127.0.0.1:5000` after running `bw web`.

## Database Schema

BentWookie uses SQLite with four main tables:

```
project            - Projects container
├── request        - Development requests (linked to project)
├── infrastructure - Infrastructure config (compute, storage, etc.)
└── learning       - Project learnings/notes
```

### Key Fields

**Project**: `prjid`, `prjname`, `prjversion`, `prjpriority`, `prjphase`, `prjdesc`

**Request**: `reqid`, `prjid`, `reqname`, `reqtype`, `reqstatus`, `reqphase`, `reqprompt`, `reqpriority`, `reqcodedir`, `reqdocpath`

## Project Structure

```
src/bentwookie/
├── __init__.py           # Package exports
├── cli.py                # CLI commands (Click)
├── constants.py          # Configuration constants
├── models.py             # Data models (Project, Request, etc.)
├── logging_util.py       # Logging configuration
├── db/
│   ├── __init__.py       # Database module exports
│   ├── connection.py     # SQLite connection manager
│   ├── queries.py        # CRUD operations
│   └── schema.sql        # Database schema
├── loop/
│   ├── __init__.py       # Loop module exports
│   ├── daemon.py         # Background daemon
│   ├── processor.py      # Request processor (Claude SDK)
│   └── phases.py         # Phase-specific logic
├── web/
│   ├── __init__.py       # Web module exports
│   ├── app.py            # Flask application
│   ├── templates/        # Jinja2 HTML templates
│   └── static/           # CSS styles
└── templates/
    └── phases/           # Phase prompt templates
        ├── plan.md
        ├── dev.md
        ├── test.md
        ├── deploy.md
        ├── verify.md
        └── document.md

data/                     # SQLite database
docs/                     # Generated documentation
logs/                     # Log files
```

## Python API

```python
from bentwookie import (
    init_db,
    create_project,
    create_request,
    list_requests,
)

# Initialize
init_db()

# Create project
prjid = create_project("myapp", prjdesc="My application")

# Create request
reqid = create_request(
    prjid=prjid,
    reqname="Add feature",
    reqprompt="Implement user dashboard",
    reqtype="new_feature",
)

# List pending requests
for req in list_requests(status="tbd"):
    print(f"{req['reqid']}: {req['reqname']}")
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest test/ -v

# Run linter
ruff check src/

# Run type checker
mypy src/bentwookie/
```

## Configuration

### Log Path Placeholders

```bash
bw loop start --log "logs/{loopname}_{today}.log"
```

- `{today}` - Current date (YYYY-MM-DD)
- `{loopname}` - Loop identifier
- `{datetime}` - Full datetime stamp

## Migration from v1

BentWookie v2 replaces the file-based task system with SQLite:

| v1 | v2 |
|----|-----|
| Markdown task files | SQLite database |
| Stage directories (1plan, 2dev...) | Phase field on request |
| `--init`, `--plan`, `--next_prompt` | `init`, `project`, `request`, `loop` commands |
| Manual stage movement | Automatic phase progression |

The v1 modules (`core.py`, `config.py`, `wizard.py`) are preserved for backwards compatibility.

## License

MIT
