# BentWookie Development Guide

## Project Overview

BentWookie (BW) is a framework for orchestrating AI agent swarms to build complex software projects. It decomposes projects through a hierarchy (Project → Service → Component → Function), manages all agents as Claude Code instances in BW-controlled terminal shells, and coordinates them via a message-based communication system.

See `BUILD_INSTRUCTION.md` for the full requirements specification.

## Target Architecture

### Workflow Phases

BW operates in four sequential phases:

1. **Define — Top-Down** (human + AI): Begins with two conversational agent interviews (Business Owner, then Enterprise Architect) to extract project requirements via voice or text. Then interactive hierarchy decomposition from Project down to Functions. User approves each level.
2. **Design — Top-Down** (AI-driven): AI produces the full build plan, dependency graph, integration maps, and connection point specs.
3. **Validate — Bottom-Up** (AI-driven): AI validates the design from Function upward, adjusts plans/dependencies, and generates test specifications (not runnable code) at every level.
4. **Build — Middle-Out** (AI swarm): Coding agents implement components (functions + runnable tests from Phase 3 specs), hand off to Service Engineers who assemble components into Services. Service Engineers may delegate component assembly back to coding agents.

### Agent Roles

| Role | Count | Scope |
|------|-------|-------|
| Business Owner | 1 | Business goal guidance, persistent |
| Enterprise Architect | 1 | Architectural guidance, persistent |
| Service Engineer | N (per service) | OSS setup, component/service integration, may delegate assembly to coding agents |
| Coding Agent | X (user max) | Single-component implementation + tests, may also handle component assembly when delegated |

### Core Components

#### Agent Modules (`agents/`)

- **InterviewEngine** (`agents/interview.py`): Conversational Q&A system for Phase 1 project discovery. Supports voice input (speech-to-text). Runs two sequential agent interviews (Business Owner, Enterprise Architect), saves transcripts, produces structured project summary.
- **AgentManager** (`agents/manager.py`): PTY-based agent lifecycle management. Spawns, monitors, and communicates with agents in BW-managed terminal shells. Enforces the agent count ceiling (X).
- **MessageQueue** (`agents/message_queue.py`): Database-backed inter-agent messaging. Normal messages queue until the recipient finishes current work. Urgent messages interrupt immediately (e.g., Architect stopping a coding agent building against stale plans).
- **Orchestrator** (`agents/orchestrator.py`): Main event loop, phase progression, and work assignment. Manages the dependency graph and ensures coding agents only receive work whose dependencies are satisfied.

#### Other Components

- **Hierarchy Store**: Persistent representation of the project decomposition (Project → Service → Component → Function) with connection maps at each level.
- **Dependency Graph**: DAG of build tasks derived from the hierarchy. Drives parallelism — agents are assigned work when all upstream dependencies are complete.
- **Test Registry**: Stores test specifications from Phase 3. Coding agents write runnable tests from these specs; Service Engineers run integration tests.
- **Database Layer**: SQLite for persistent state (projects, hierarchy, tasks, agent state, test results, learnings).
- **CLI**: Click-based command interface. Entry point: `bw`.
- **Web UI**: Flask-based split-panel workspace layout. Left panel for navigation and hierarchy; right panel for detail views, agent monitoring, and project status.
- **Settings**: JSON-based user configuration in `data/settings.json`.

### Key Design Rules

- **All design decisions are locked before build**: Coding agents do not make architectural choices. Design is finalized in Phases 1-2. Design amendments during Phase 4 flow through the Architect via the rework protocol.
- **Test specs exist before code**: Phase 3 produces test specifications; coding agents write runnable tests alongside implementation in Phase 4.
- **Minimal agent context**: Coding agents receive only their component spec, connection map, and test specs — not the full project.
- **Dependency-driven parallelism**: Work is parallelized up to the user-defined ceiling, constrained by the DAG.
- **User approval gates**: Each hierarchy level in Phase 1 requires user sign-off.
- **BW owns all shells**: Every agent runs in a BW-managed terminal. BW can observe, message, or terminate any agent at any time.
- **Rework protocol**: Coding agent flags issue → Service Engineer triages (local fix or escalate) → Architect issues design amendment if structural.

## Coding Standards

### Python

- Python 3.12+ required.
- Type hints on all functions. Use `dict[str, Any]`, `list[dict]`, `str | None` (not `Optional[str]`).
- Format with `black` (line-length 88). Lint with `ruff`.

### Async

- Agent processing is async. Use `asyncio.run()` from sync entry points.
- Claude SDK `query()` is an async generator.
- Use `await asyncio.wait_for()` for timeouts.

### Database

- Always use context manager: `with get_db() as conn:`
- Parameterized queries only (never string interpolation).
- Return `dict` for single rows, `list[dict]` for multiple.
- Update `touchts` timestamp on modifications.

### Error Handling

- Log with context: `logger.error(f"Agent {agent_id} failed on module {mod}: {error}")`
- Distinguish rate limits (retry) from real errors (mark failed).
- Set user-readable error messages in the database.

### Settings System

All configurable parameters go through `settings.py`:
- Add default to `DEFAULT_SETTINGS`.
- Create `get_<name>()` / `set_<name>()` with validation.
- Use `get_setting()` in code, never hardcoded constants.

### Versioning

- Version in `pyproject.toml` under `[project].version` (currently `0.3.0`).
- Structure: `major.minor.patch`.
- Increment patch after every AI-driven change.

## Testing

- Tests in `test/` directory.
- Run: `pytest test/ -v`
- Mock the Claude Agent SDK in tests (async, requires auth).
- Use in-memory SQLite for database tests.
- Tooling: `pytest`, `pytest-cov`, `mypy --strict`.

## Dependencies

- `claude-agent-sdk`: Agent execution engine
- `click`: CLI framework
- `flask`: Web UI
- `markdown` / `markupsafe`: Markdown rendering in Flask templates
- `pyyaml`: Configuration
- `questionary`: Interactive prompts
- SQLite: Built into Python

Keep dependencies minimal. Do not add new ones without justification.

## Things to Avoid

1. **Don't bypass the settings system**: Use `get_setting()`, not constants.
2. **Don't let coding agents make design decisions**: Architecture is locked after Phase 2. Changes go through the rework protocol.
3. **Don't skip validation**: Check user input before database writes.
4. **Don't assume sequential IDs**: Use returned IDs from insert operations.
5. **Don't write to shared state without coordination**: Service Engineers own integration; coding agents own only their assigned component.
