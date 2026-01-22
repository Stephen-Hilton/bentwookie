# BentWookie

> "I bent my wookie."  - Ralph Wiggum

BentWookie - AI coding loop that manages development requests through a phase-based workflow using the Claude Agent SDK for execution, with centrally managed deployment and infrastructure configurations.

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
- **Phase-Based Workflow**: plan → dev → test → deploy → verify → document → commit
- **Git Integration**: Automatic commit and push with AI-generated commit messages
- **Project Customization**: Project-level prompts and claude.md file integration
- **Flexible Configuration**: Global, project-level, and request-level settings
- **CLI Interface**: Full control via command line
- **Web UI**: Browser-based dashboard with auto-refresh for real-time status
- **Daemon Mode**: Background processing of queued requests
- **Smart Workspace Detection**: Automatically finds BentWookie workspace
- **Editable Prompts**: Phase templates in `data/prompts/` - edit without restart
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
bw config --show                        # View all current settings with descriptions
bw config --auth max                    # Switch to Claude Max mode
bw config --auth api                    # Switch to API key mode
bw config --max-turns 100               # Set max API calls per phase
bw config --poll-interval 60            # Set daemon poll interval (seconds)

# Commit phase configuration
bw config commit                        # Show current commit settings
bw config commit --enabled              # Enable commit phase globally
bw config commit --disabled             # Disable commit phase globally
bw config commit --branch current       # Commit to current branch
bw config commit --branch other --branch-name main  # Commit to specific branch
```

### Project Management

```bash
bw project create <name>                          # Create a project
bw project create <name> -d "desc"                # With description
bw project create <name> -v mvp                   # Set version (poc, mvp, v1, v1.1, v2)
bw project create <name> -p 3                     # Set priority (1-10, lower = higher)
bw project create <name> --codedir /path/to/code  # Set default code directory
bw project create <name> --prompt "Use type hints and docstrings"  # Project-level guidelines
bw project create <name> --claude-md /path/to/claude.md  # Project-specific instructions

# Commit phase overrides (project-level)
bw project create <name> --commit                 # Enable commit phase for this project
bw project create <name> --no-commit              # Disable commit phase for this project
bw project create <name> --commit-branch current  # Use current branch
bw project create <name> --commit-branch other --commit-branch-name develop  # Use specific branch

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
bw request create <project> -n "Feature" -m "..." --codedir /custom/path

# Commit phase overrides (request-level)
bw request create <project> -n "Feature" -m "..." --commit  # Force commit for this request
bw request create <project> -n "Feature" -m "..." --no-commit  # Skip commit for this request
bw request create <project> -n "Feature" -m "..." --commit-branch feature-branch  # Custom branch

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
| `deploy` | Deploy to target environment (skipped for local-only) | Bash |
| `verify` | Verify deployment success (skipped for local-only) | Read, Bash, WebFetch, Glob, Grep |
| `document` | Update documentation | Read, Write |
| `commit` | Create git commit with AI-generated message (optional) | Bash, Read, Grep |
| `complete` | Request finished | - |

**Note**: The `deploy` and `verify` phases are automatically skipped for local-only infrastructure. The `commit` phase can be enabled/disabled globally, per-project, or per-request.

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

### Commit Phase

The commit phase automatically creates git commits with AI-generated commit messages:

**Features**:
- Analyzes changes with `git status` and `git diff`
- Generates meaningful commit messages following best practices
- Supports current branch or specific target branch
- Pushes to remote automatically
- Never fails the request (errors logged as warnings)

**Configuration**:
```bash
# Global settings
bw config commit --enabled --branch current

# Project-level override
bw project create myapp --commit-branch other --commit-branch-name develop

# Request-level override
bw request create myapp -n "Feature" -m "..." --commit-branch feature-x
```

**Branch Modes**:
- `current`: Commit to whatever branch is currently checked out
- `other`: Commit to a specific named branch (creates if needed)

### Project Customization

**Project Prompt**:
Add default instructions that apply to all requests in a project:

```bash
bw project create myapp --prompt "Always use type hints and write docstrings"
```

**Claude.md Integration**:
Link to a project's `claude.md` file for detailed project-specific instructions:

```bash
bw project create myapp --claude-md /path/to/myapp/claude.md
```

The content is appended to the system prompt for every request in that project.

### Editable Prompts

Phase templates are stored in `data/prompts/phases/` and can be edited directly:

```bash
# Edit the dev phase prompt
vim data/prompts/phases/dev.md

# Edit the system prompt
vim data/prompts/system.md
```

Changes take effect immediately - no restart required. Templates use Python string formatting with variables like `{project_name}`, `{request_name}`, `{code_dir}`, etc.

### Rate Limit Handling

BentWookie automatically handles API rate limits:

- Detects rate limit errors (429, "too many requests", etc.)
- Keeps request as `tbd` so it gets retried (not marked as `err`)
- Pauses daemon for 60 seconds before retrying
- Logs warnings instead of errors for rate limits

## Web UI

The web interface provides:

- **Dashboard**: Overview of projects, requests, and status counts
- **Projects**: Create, view, edit, and manage projects with full configuration
- **Requests**: Create, filter, and update requests with commit overrides
- **System**: Daemon status and system health with auto-refresh every 3 seconds

Access at `http://127.0.0.1:5000` after running `bw web`.

### Custom Port

```bash
bw web                    # Default port 5000
bw web --port 8080        # Custom port
bw web --host 0.0.0.0     # Allow external access
```

## Database Schema

BentWookie uses SQLite with four main tables:

```
project            - Projects container
├── request        - Development requests (linked to project)
├── infrastructure - Infrastructure config (compute, storage, etc.)
└── learning       - Project learnings/notes
```

### Key Fields

**Project**:
- Core: `prjid`, `prjname`, `prjversion`, `prjpriority`, `prjphase`, `prjdesc`
- Customization: `prjprompt`, `prjclaudemd`, `prjcodedir`
- Commit Config: `prjcommitenabled`, `prjcommitbranchmode`, `prjcommitbranchname`

**Request**:
- Core: `reqid`, `prjid`, `reqname`, `reqtype`, `reqstatus`, `reqphase`, `reqprompt`, `reqpriority`
- Paths: `reqcodedir`, `reqplanpath`, `reqtestplanpath`, `reqdocpath`
- Commit Config: `reqcommitenabled`, `reqcommitbranch`
- Testing: `reqtestretries`, `reqerror`

**Infrastructure**: `infid`, `prjid`, `inftype`, `infprovider`, `infval`, `infnote`

**Request Infrastructure** (overrides): `rinfid`, `reqid`, `inftype`, `infprovider`, `infval`, `infnote`

**Learning**: `lrnid`, `prjid`, `lrndesc` (prjid=-1 for global learnings)

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
    └── phases/           # Bundled phase templates (fallback)
        ├── plan.md
        ├── dev.md
        ├── test.md
        ├── deploy.md
        ├── verify.md
        ├── document.md
        ├── commit.md
        └── system.md

data/
├── bentwookie.db         # SQLite database
├── settings.json         # Configuration settings
└── prompts/              # Editable prompt templates (created by bw init)
    ├── system.md         # System prompt template
    └── phases/           # Phase-specific prompts
        ├── plan.md
        ├── dev.md
        ├── test.md
        ├── deploy.md
        ├── verify.md
        ├── document.md
        └── commit.md
docs/                     # Generated documentation
logs/                     # Log files

**Note**: Templates in `data/prompts/` take precedence over bundled templates and can be edited without restarting. Changes take effect immediately.
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
  "model": "claude-opus-4-5",
  "max_turns": 50,
  "max_iterations": 5,
  "poll_interval": 30,
  "commit_enabled": true,
  "commit_branch_mode": "current",
  "commit_branch_name": null,
  "doc_retention_days": 30
}
```

### Configuration Hierarchy

BentWookie uses a three-level configuration hierarchy for commit settings:

1. **Request-level** (highest priority) - Set on individual requests
2. **Project-level** (middle priority) - Set on projects
3. **Global** (lowest priority) - System-wide defaults in `settings.json`

Example:
- Global: Commit enabled, use current branch
- Project "myapp": Commit to "develop" branch (overrides global)
- Request #42: Commit disabled (overrides project and global)

This allows flexible control: most requests use defaults, but you can customize per-project or per-request as needed.

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

### "No initialized BentWookie workspace found"

BentWookie looks for a workspace in:
1. Current directory
2. Parent directory
3. Immediate child directories

If you see this error:
```bash
cd /path/to/your/bentwookie/workspace
bw loop start
```

Or initialize a new workspace:
```bash
bw init
```

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

### Commit phase not running

Check if it's enabled:
```bash
bw config commit  # Show current settings
```

Enable it globally:
```bash
bw config commit --enabled
```

Or enable for specific project/request:
```bash
bw project create myapp --commit
bw request create myapp -n "Feature" -m "..." --commit
```

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
