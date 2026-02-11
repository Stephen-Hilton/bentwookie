# BentWookie v0.3

> "I bent my wookie."  - Ralph Wiggum

BentWookie is an AI agent swarm orchestration framework that decomposes software projects through a 4-level hierarchy (Project > Service > Component > Function), manages all agents as Claude Code instances in BW-controlled terminal shells, and coordinates them via a dependency-driven build system with inter-agent messaging.

## QuickStart

```bash
# Clone and install
git clone https://github.com/bentwookie/bentwookie.git
cd bentwookie
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Initialize workspace (default data directory: ./data)
bw init

# Or specify a custom data directory
bw init /path/to/my/data

# Start the web UI
bw web start

# Open in browser
open http://127.0.0.1:5000
```

From the web UI, create a project (which starts an AI interview), manage agents, and monitor builds.

### Requirements

- Python 3.11+
- SQLite (included with Python)
- Claude Code CLI (`claude`) installed and authenticated
- Claude Agent SDK (`claude-agent-sdk`)
- Flask (for web UI)

## Overview

BentWookie operates in four sequential phases:

| Phase | Direction | Driver | What Happens |
|-------|-----------|--------|--------------|
| **Define** | Top-Down | Human + AI | Two conversational interviews (Business Architect, then Enterprise Architect) extract requirements. Interactive hierarchy decomposition with user approval at each level. |
| **Design** | Top-Down | AI | AI produces full build plans, dependency graphs, integration maps, and connection point specs for every component. |
| **Validate Design** | Bottom-Up | AI | AI validates design from Function upward, adjusts plans/dependencies, generates test specifications (not runnable code) at every level. |
| **Build** | Middle-Out | AI Swarm | Coding agents implement components + write tests from Phase 3 specs. Service Engineers assemble components and integrate into services. Work is parallelized based on the dependency DAG. |
| **Test** | Bottom-Up | AI Swarm | Testing agents execute prebuild tests at all levels, starting with functions (unit) and crawling their way up to services an ultimately to all business use-cases. |

### Agent Roles

| Role | Abbreviation | Count | Scope |
|------|-------------|-------|-------|
| Enterprise Architect | `ea` | 1 | Architecture, hierarchy decomposition (persistent) |
| Business Architect | `ba` | 1 | Business goal guidance (persistent) |
| Service Engineer | `se` | N (per service) | OSS setup, component/service integration |
| Coding Agent | `ca` | Up to X (configurable) | Single-component implementation + tests |
| Testing Agent | `ta` | Up to Y (configurable) | Test execution and validation |

Agent names are auto-generated with a role suffix, e.g. "Bastion (ea)", "Pixel (ca)", "Watchdog (ta)".

### Key Features

- **Interview Engine**: Conversational Q&A with voice input (Web Speech API) for project discovery
- **4-Level Hierarchy**: Project > Service > Component > Function
- **Dependency-Driven DAG**: Agents only receive work when all upstream dependencies are satisfied
- **Inter-Agent Messaging**: Normal (queued) and urgent (interrupt) message delivery
- **Rework Protocol**: Coding Agent > Service Engineer > Architect escalation path
- **Real-Time Web UI**: SSE-powered monitoring of agents, build progress, and messages
- **Hierarchical Settings**: Global > Agent Type > Individual Agent override cascade
- **User-Modifiable Prompts**: All AI agent prompt templates are copied to `data/prompts/` on init for easy customization
- **SQLite Persistence**: 21 tables tracking projects, components, agents, messages, tests, and more
- **Golden Wookie Theme**: Custom dark-gold CSS theme across all pages

## Installation

```bash
# Clone the repository
git clone https://github.com/bentwookie/bentwookie.git
cd bentwookie

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Or install with dev dependencies (pytest, ruff, mypy, etc.)
pip install -e ".[dev]"
```

## Authentication

BentWookie spawns Claude Code CLI instances as agent subprocesses. Authentication is handled by the Claude CLI:

| Mode | Description | Setup |
|------|-------------|-------|
| `max` | Claude Max subscription (default) | Authenticate via `claude` CLI |
| `api` | API key | Set `ANTHROPIC_API_KEY` environment variable |

```bash
# Ensure Claude CLI is authenticated
claude --version

# Or set API key for API mode
export ANTHROPIC_API_KEY="sk-ant-..."
```

## CLI Commands

### Initialization

```bash
bw init                    # Initialize workspace in ./data
bw init /path/to/data      # Initialize workspace in custom directory
```

This creates the database, settings file, logs directory, and copies prompt templates to `{data}/prompts/` for user modification.

### Project Management

```bash
bw project create <name>                          # Create a project
bw project create <name> -d "description"         # With description
bw project create <name> -c /path/to/code         # Set code directory
bw project list                                   # List all projects
bw project list --phase build                     # Filter by phase
bw project show <id>                              # Show project details
bw project edit <id> --name "new name"            # Edit project
bw project delete <id>                            # Delete project
```

### Interviews (Define Phase)

```bash
bw interview start <project_id> --type business_owner       # Start BA interview
bw interview start <project_id> --type enterprise_architect  # Start EA interview
bw interview list                                            # List all interviews
bw interview show <id>                                       # Show transcript
```

Interviews are best conducted through the web UI. Creating a new project from the web UI automatically starts a Business Architect interview.

### Agent Management

```bash
bw agent list                        # List all agents
bw agent list --project <id>         # Filter by project
bw agent list --status working       # Filter by status
bw agent show <id>                   # Show agent details
bw agent message <id> "text"         # Send message to agent
bw agent message <id> "text" --urgent  # Send urgent (interrupt) message
bw agent pause <id>                  # Pause agent
bw agent resume <id>                 # Resume agent
bw agent kill <id>                   # Terminate agent
```

### Build Management

```bash
bw build status <project_id>     # Show build progress
bw build start <project_id>      # Start build phase
bw build pause <project_id>      # Pause build
bw build resume <project_id>     # Resume build
```

### System

```bash
bw system status                     # Show orchestrator status + stats
bw system start <project_id>         # Start orchestrator (daemon)
bw system start <project_id> -f      # Start orchestrator (foreground)
bw system stop                       # Stop orchestrator
bw system config                     # Show all settings
bw system config --model claude-sonnet-4-5    # Change model
bw system config --max-agents 10     # Change agent ceiling
```

### Web UI

```bash
bw web start                         # Start web UI (http://127.0.0.1:5000)
bw web start --port 8080             # Custom port
bw web start --host 0.0.0.0 --debug  # Public access with debug mode
bw web status                        # Show configured host/port
```

## Web UI

The web UI provides three main pages plus supporting views:

| Page | URL | Description |
|------|-----|-------------|
| **Workspace** | `/workspace` | Split-panel: hierarchy tree (left) + detail view (right). Project selector, service creation, progress tracking. |
| **Agent Swarm** | `/agents` | Split-panel: agent tree by role (left) + queue log & terminal (right). Spawn, terminate, rename, and configure agents. |
| **Settings** | `/settings` | Global settings, per-agent-type overrides, and feature toggles. |

Additional views: Dashboard (`/`), Project View (`/projects/<id>`), Interview Chat (`/interviews/<id>`), Build Progress, Messages.

The **agent sub-header** spans all pages showing live counts for all 5 agent types with quick-spawn buttons. An **EA Chat** slideover panel is accessible from any page via the "EA" button in the nav bar.

All pages update in real-time via Server-Sent Events (SSE).

## AI Agent Prompt System

All AI agent prompts are built from `.md` template files using a simple `{variable}` substitution system. Templates are loaded by `load_prompt(name, **kwargs)` which:

1. Checks `{data}/prompts/{name}.md` first (user-modifiable copy)
2. Falls back to the package directory `src/bentwookie/agents/prompts/{name}.md`

Run `bw init` to copy all templates to your data directory. Edit the copies freely — they take priority over the built-in versions.

### Prompt Assembly

Agent system prompts are assembled from multiple templates concatenated together:

```
┌─────────────────────────────┐
│  all_startup_header.md      │  ← Project context (all agents)
├─────────────────────────────┤
│  {role}_startup.md          │  ← Role-specific instructions (ea/ba/se/ca/ta)
├─────────────────────────────┤
│  [component info]           │  ← Injected at runtime if agent has assigned component
├─────────────────────────────┤
│  all_startup_footer.md      │  ← Operational constraints (all agents)
└─────────────────────────────┘
```

Build task prompts use a separate template:

```
┌─────────────────────────────┐
│  all_build_task.md          │  ← Task type, component spec, connections, tests
└─────────────────────────────┘
```

### Template Reference

#### Shared Templates (all agents)

| Template | Purpose | Variables |
|----------|---------|-----------|
| `all_startup_header.md` | Project context header for all agent startups | `{project_name}`, `{project_desc}` |
| `all_startup_footer.md` | Operational constraints footer for all agent startups | `{timeout_minutes}` |
| `all_build_task.md` | Build task assignment prompt | `{task_type}`, `{cmp_name}`, `{cmp_desc}`, `{cmp_spec}`, `{conn_section}`, `{test_section}`, `{role_name}` |

#### Role Startup Templates (no variables — static role descriptions)

| Template | Agent Role |
|----------|-----------|
| `ea_startup.md` | Enterprise Architect |
| `ba_startup.md` | Business Architect |
| `se_startup.md` | Service Engineer |
| `ca_startup.md` | Coding Agent |
| `ta_startup.md` | Testing Agent |

#### Interview Templates

| Template | Purpose | Variables |
|----------|---------|-----------|
| `ba_interview01_intro.md` | Business Architect interview system prompt | `{project_name}`, `{project_desc}` |
| `ba_interview02_summary.md` | BA interview completion/summary prompt | *(none)* |
| `ea_interview01_intro.md` | Enterprise Architect interview system prompt | `{project_name}`, `{project_desc}`, `{bo_transcript_section}` |
| `ea_interview02_summary.md` | EA interview completion/summary prompt | *(none)* |

#### Rework & Escalation Templates

| Template | Purpose | Variables |
|----------|---------|-----------|
| `ca_rework_notify.md` | Notify Service Engineer of Coding Agent failure | `{cmp_name}`, `{task_id}`, `{error}` |
| `se_rework_local.md` | Authorize Service Engineer for local fix | `{cmp_name}`, `{task_id}`, `{error}` |
| `ea_escalation_notify.md` | Escalate to Architect when SE can't fix | `{cmp_name}`, `{task_id}`, `{error}` |
| `ea_rework_structural.md` | Notify Architect of structural rework needed | `{cmp_name}`, `{task_id}`, `{error}` |

### Variable Reference

Every `{variable}` in a prompt template is substituted at runtime. Here is where each value originates and how to influence it:

| Variable | Source | DB Table.Column | How to Modify |
|----------|--------|-----------------|---------------|
| `{project_name}` | Project record | `project.prjname` | Edit via Web UI (Workspace > Edit Project) or `bw project edit <id> --name "..."` |
| `{project_desc}` | Project record | `project.prjdesc` | Edit via Web UI or `bw project edit <id> --desc "..."` |
| `{timeout_minutes}` | Settings cascade | `data/settings.json` → `agent_timeout` | Settings page or `bw system config --agent-timeout 45` |
| `{bo_transcript_section}` | Computed | `interview` + `interview_message` tables | Conduct the Business Architect interview — transcript is built from all messages |
| `{task_type}` | Build task record | `build_task.bttype` | Set during Design phase (values: Implement, Assemble, Integrate, Test) |
| `{cmp_name}` | Component record | `component.cmpname` | Edit component name via Web UI or during Define phase |
| `{cmp_desc}` | Component record | `component.cmpdesc` | Edit component description in Web UI |
| `{cmp_spec}` | Component record | `component.cmpspec` | Generated during Design phase by the Architect |
| `{conn_section}` | Computed | `connection_map` table | Built from connection map entries; connections defined during Design phase |
| `{test_section}` | Computed | `test_spec` table | Built from test specs; specs generated during Validate phase |
| `{role_name}` | Computed | Derived from `build_task.bttype` | Mapped from task type: implement→"coding agent", assemble/integrate→"service engineer", test→"testing agent" |
| `{task_id}` | Build task record | `build_task.btid` | Auto-assigned database ID |
| `{error}` | Runtime | Agent output buffer | Error message from a failed agent (detected via `TASK_FAILED:` marker in output) |

**Missing variable safety**: If a variable is not provided, it renders literally as `{variable_name}` in the output (no crash). This is useful for debugging templates.

### Customization Examples

**Change what the Enterprise Architect knows about its role:**
```bash
# Edit the EA startup prompt
nano data/prompts/ea_startup.md
```

**Adjust the build task instructions for all agents:**
```bash
# Edit the shared build task template
nano data/prompts/all_build_task.md
```

**Add a new variable to a template:**
1. Add `{my_variable}` to the `.md` template
2. Find the corresponding `load_prompt()` call in the Python code
3. Pass the new keyword argument: `load_prompt("template_name", my_variable="value")`

## Settings

Settings are stored in `{data}/settings.json` and configurable via the web UI Settings page:

```json
{
  "auth_mode": "max",
  "model": "claude-opus-4-5",
  "max_concurrent_agents": 5,
  "agent_timeout": 30,
  "poll_interval": 30,
  "voice_enabled": true,
  "sse_enabled": true,
  "web_host": "127.0.0.1",
  "web_port": 5000,
  "max_enterprise_architect": 1,
  "max_business_architect": 1,
  "max_service_engineer": 5,
  "max_coding_agent": 10,
  "max_testing_agent": 5
}
```

### Hierarchical Settings Cascade

Settings resolve in order: **Individual Agent > Agent Type > Global**

- Set a global default model for all agents
- Override at the agent-type level (e.g., all Coding Agents use Sonnet)
- Override for a specific agent instance

Per-type overrides are set on the Settings page. Per-agent overrides are set on the Agent Swarm page (select agent > Settings tab).

## Database Schema

BentWookie uses SQLite with 21 tables:

```
project              - Top-level projects (name, desc, phase, priority, code dir)
component            - 4-level hierarchy (self-referencing via cmpparentid)
connection_map       - Peer connections between components
dependency           - Build-order DAG edges
agent                - Agent instances (role, status, name, shell PID)
agent_message        - Inter-agent message queue (normal + urgent)
agent_output         - Agent terminal output chunks (for live streaming)
agent_settings       - Per-agent and per-type setting overrides
agent_context        - Saved agent context for work queue transitions
interview            - Interview sessions (BA + EA)
interview_message    - Individual messages within interviews
test_spec            - Test specifications per component
test_result          - Test execution results
build_task           - Work items assigned to agents
build_plan           - Design phase plans per component
design_amendment     - Rework protocol log (append-only)
traceability         - Business goals to component mapping
learning             - Accumulated learnings
daemon_state         - Orchestrator singleton status
document             - Generated artifacts
techstack_catalog    - Searchable tech stack catalog (~387 entries)
```

## Project Structure

```
src/bentwookie/
├── __init__.py            # Package exports
├── cli.py                 # CLI commands (Click)
├── constants.py           # Constants (phases, levels, roles, statuses, name generator)
├── models.py              # Dataclasses with from_dict/to_dict
├── settings.py            # Settings management with hierarchical cascade
├── logging_util.py        # Logging configuration
├── exceptions.py          # Exception hierarchy
├── agents/
│   ├── __init__.py        # Agent engine exports
│   ├── manager.py         # Agent subprocess lifecycle (pty + spawn)
│   ├── message_queue.py   # DB-backed message queue with urgent priority
│   ├── orchestrator.py    # Main event loop, DAG work assignment, rework protocol
│   ├── interview.py       # Conversational interview engine
│   └── prompts/           # AI prompt templates (.md files)
│       ├── loader.py      # Template loader (checks user dir first)
│       ├── all_startup_header.md
│       ├── all_startup_footer.md
│       ├── all_build_task.md
│       ├── ea_startup.md / ba_startup.md / se_startup.md / ca_startup.md / ta_startup.md
│       ├── ba_interview01_intro.md / ba_interview02_summary.md
│       ├── ea_interview01_intro.md / ea_interview02_summary.md
│       └── ca_rework_notify.md / se_rework_local.md / ea_escalation_notify.md / ea_rework_structural.md
├── templates/
│   └── techstack_catalog.txt  # Tech stack seed data
├── db/
│   ├── __init__.py        # Database module exports
│   ├── connection.py      # SQLite connection manager + migrations
│   ├── queries.py         # CRUD operations for all 21 tables
│   └── schema_v2.sql      # Database schema
└── web/
    ├── app.py             # Flask application with SSE + API endpoints
    ├── templates/
    │   ├── base.html              # Base layout (nav, sub-header, EA chat)
    │   ├── workspace.html         # Workspace split-panel
    │   ├── agents.html            # Agent swarm monitor
    │   ├── settings.html          # Settings page
    │   ├── dashboard.html         # Mission control
    │   ├── project_form.html      # Create/edit project
    │   ├── project_view.html      # Project detail
    │   ├── interview_session.html # Chat UI
    │   └── ...                    # Additional views
    └── static/
        ├── style.css              # Golden Wookie theme
        └── js/
            ├── sse-client.js      # SSE wrapper with auto-reconnect
            ├── agent-monitor.js   # Agent tree refresh, spawn/terminate
            ├── agent-terminal.js  # Live terminal output
            ├── ea-chat.js         # EA chat slideover
            ├── hierarchy-tree.js  # Collapsible tree rendering
            ├── detail-panel.js    # Right-panel detail loading
            ├── interview-chat.js  # Chat UI + voice input
            ├── folder-picker.js   # Directory browser modal
            └── dependency-graph.js # DAG visualization

data/                      # Created by `bw init`
├── bentwookie.db          # SQLite database
├── settings.json          # Configuration
├── docs/                  # Generated documents
└── prompts/               # User-modifiable prompt templates (copied from package)

logs/                      # Log files
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

## License

MIT
