# BentWookie

> "I bent my wookie."  - Ralph Wiggum

BentWookie - AI coding loop that manages development requests through various phases using the Claude Agent SDK for execution, using centrally managed deployment and infrastructure configurations.

## QuickStart

### Using Claude Max (Recommended)

```bash
# Install
python -m pip install bentwookie

# Initialize with Claude Max subscription
bw init --auth max

# Create your first project and request
bw project create myapp --desc "My application"
bw request create myapp -n "Add login" -m "Implement user authentication"

# Start processing
bw loop start --foreground
```

### Using API Key

```bash
# Initialize with API key mode
bw init --auth api

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Start processing
bw loop start --foreground
```

## Overview

BentWookie v2 provides:

- **SQLite Database**: Persistent state management for projects and requests
- **Claude Agent SDK Integration**: Automated processing through development phases
- **Phase-Based Workflow**: plan → dev → test → deploy → verify → document
- **CLI Interface**: Full control via command line
- **Web UI**: Browser-based dashboard for managing projects and requests
- **Daemon Mode**: Background processing of queued requests
- **Rate Limit Handling**: Automatic retry with backoff on API limits

## Installation

```bash
# Clone the repository
git clone -b AIGen02 https://github.com/bentwookie/bentwookie.git
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

## Authentication

BentWookie supports two authentication modes:

| Mode | Description | Setup |
|------|-------------|-------|
| `max` | Claude Max subscription | Authenticate via `claude` CLI (web auth) |
| `api` | API key | Set `ANTHROPIC_API_KEY` environment variable |

### Claude Max (Recommended)

Uses your Claude Max subscription via the Claude Code CLI's web authentication:

```bash
# Ensure you're authenticated with Claude CLI
claude --version

# Initialize BentWookie with max mode
bw init --auth max
```

### API Key

Uses the Anthropic API directly (requires credits):

```bash
# Initialize with API mode
bw init --auth api

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get an API key at [console.anthropic.com](https://console.anthropic.com)

### Switching Modes

```bash
bw config --auth max    # Switch to Claude Max
bw config --auth api    # Switch to API key
bw config --show        # View current settings
```

## CLI Commands

### Initialization

```bash
bw init                      # Initialize (prompts for auth mode)
bw init --auth max           # Use Claude Max subscription
bw init --auth api           # Use API key
bw init --db-path ./my.db    # Custom database path
```

### Configuration

```bash
bw config --show             # View current settings
bw config --auth max         # Switch to Claude Max mode
bw config --auth api         # Switch to API key mode
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
bw loop start --foreground -d    # Foreground with debug logging
bw loop start --poll 60          # Custom poll interval (seconds)
bw loop start --log logs/bw.log  # Custom log file

bw loop stop                     # Stop the daemon
bw loop status                   # Check if daemon is running
```

Logs are written to `logs/{loopname}_{today}.log` by default (e.g., `logs/bwloop_2026-01-21.log`).

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

### Rate Limit Handling

BentWookie automatically handles API rate limits:

- Detects rate limit errors (429, "too many requests", etc.)
- Keeps request as `tbd` so it gets retried (not marked as `err`)
- Pauses daemon for 60 seconds before retrying
- Logs warnings instead of errors for rate limits

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
├── settings.py           # Settings management (auth mode, etc.)
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

data/
├── bentwookie.db         # SQLite database
└── settings.json         # Configuration settings
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

### Settings File

Settings are stored in `data/settings.json`:

```json
{
  "auth_mode": "max",
  "model": "claude-sonnet-4-20250514",
  "max_turns": 50,
  "poll_interval": 30
}
```

### Log Path Placeholders

The default log path is `logs/{loopname}_{today}.log`. You can customize it:

```bash
bw loop start --log "logs/{loopname}_{today}.log"
```

Available placeholders:
- `{today}` - Current date (YYYY-MM-DD)
- `{loopname}` - Loop identifier
- `{datetime}` - Full datetime stamp

## Troubleshooting

### Daemon says "already running" but isn't

If the daemon crashed or was killed, the PID file may be stale:

```bash
rm data/bentwookie.pid
bw loop start --foreground --debug
```

### Debug mode

Use `--debug` (or `-d`) for verbose logging:

```bash
bw loop start --foreground --debug
```

Check the log file at `logs/bwloop_YYYY-MM-DD.log` for detailed output.

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
