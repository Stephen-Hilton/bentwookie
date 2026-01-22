`# BentWookie Development Guide

## Project Overview

BentWookie is an AI-powered development automation system that processes coding requests through a phase-based workflow using the Claude Agent SDK. It manages projects and requests via SQLite database and processes them sequentially through phases: plan → dev → test → deploy → verify → document.

## Architecture

### Core Components

- **Database Layer** (`src/bentwookie/db/`)
  - SQLite for persistent state
  - Tables: `project`, `request`, `infrastructure`, `learning`
  - All CRUD operations in `queries.py`

- **Loop/Daemon** (`src/bentwookie/loop/`)
  - `daemon.py`: Background process that polls for pending requests
  - `processor.py`: Executes requests using Claude Agent SDK
  - `phases.py`: Phase-specific prompts and logic

- **CLI** (`src/bentwookie/cli.py`)
  - Click-based command interface
  - Commands: init, project, request, loop, config, web, status

- **Web UI** (`src/bentwookie/web/`)
  - Flask-based dashboard
  - Templates in `web/templates/`

- **Settings** (`src/bentwookie/settings.py`)
  - JSON-based configuration in `data/settings.json`
  - Auth modes: `api` (API key) or `max` (Claude Max subscription)

### Key Files

- `constants.py`: All configuration constants (timeouts, phases, statuses)
- `models.py`: Data models (Project, Request, DaemonStatus)
- `logging_util.py`: Centralized logging configuration

## Critical Architectural Decisions

### 1. Sequential Processing
**Requests are processed ONE AT A TIME** (src/bentwookie/loop/daemon.py:125-148). The daemon:
- Fetches one request with `get_next_request()` (LIMIT 1)
- Processes it completely through its current phase
- Only then fetches the next request
- Priority determines order (lower number = higher priority)

### 2. Settings vs Constants
**IMPORTANT**: There's a dual system that needs attention:
- `constants.py`: Hardcoded defaults (original architecture)
- `settings.py`: User-configurable settings in `data/settings.json`

When adding configurable parameters:
- Add to `DEFAULT_SETTINGS` in `settings.py`
- Create getter/setter functions in `settings.py`
- Use `get_setting()` in code, NOT the constant
- Keep constant as fallback default

### 3. Phase-Based Workflow
Each phase has (see `constants.py:PHASE_TOOLS`):
- Specific allowed tools (security model)
- Timeout limits (constants.py:PHASE_TIMEOUTS)
- Custom prompt template (src/bentwookie/templates/phases/)

### 4. Working Directory Hierarchy
Code directory resolution (processor.py:321-349):
1. `request.reqcodedir` (request-specific override)
2. `project.prjcodedir` (project-level default)
3. `<cwd>/<project_name>` (auto-created fallback)

## Coding Standards

### Database Operations
- Always use context manager: `with get_db() as conn:`
- Use parameterized queries (NEVER string interpolation)
- Return `dict` for single rows, `list[dict]` for multiple
- Update `touchts` timestamp on modifications

### Error Handling
- Log errors with context: `logger.error(f"Request {reqid} failed: {error}")`
- Set user-friendly error messages in database
- Create bug-fix requests for internal failures (processor.py:198-249)
- Distinguish rate limits (retry) from real errors (mark failed)

### Async/Await
- `process_request()` is async and uses `asyncio.run()` from sync wrapper
- Claude SDK `query()` is async generator
- Use `await asyncio.wait_for()` for timeouts

### Type Hints
- Use Python 3.10+ syntax: `dict[str, Any]`, `list[dict]`
- Use `str | None` not `Optional[str]`
- Return types required on all functions

### Versioning
- Project version is stored in `./pyproject.toml` in the [project].version key 
- Version structure is major.minor.patch
- After every AI change, increment the version.patch number by one

## Common Tasks

### Adding a New Phase
1. Add to `PHASES` and `NEXT_PHASE` in `constants.py`
2. Define tools in `PHASE_TOOLS`
3. Set timeout in `PHASE_TIMEOUTS`
4. Create template in `src/bentwookie/templates/phases/<phase>.md`
5. Update workflow documentation

### Adding a Configurable Setting
1. Add to `DEFAULT_SETTINGS` in `settings.py`
2. Create getter function: `get_<setting_name>()`
3. Create setter function: `set_<setting_name>()` with validation
4. Use `get_setting()` in consuming code, NOT constants
5. Update CLI if it should be user-configurable

### Adding a CLI Command
1. Add to `cli.py` with `@click.command()` decorator
2. Use existing patterns for database access
3. Add to appropriate command group (project, request, loop, config)
4. Update help text and README

### Adding a Database Field
1. Update schema in `src/bentwookie/db/schema.sql`
2. Create migration script (manual for now - future: use Alembic)
3. Update `queries.py` CRUD operations
4. Update `models.py` if applicable

## Important Patterns

### Rate Limit Handling
(processor.py:449-462)
- Detect rate limit errors with `_is_rate_limit_error()`
- Set global `_rate_limited_until` timestamp
- Keep request as `tbd` (not `err`) so it retries
- Daemon checks `is_rate_limited()` before processing

### Test Retry Loop
(processor.py:381-424)
- Parse test results from Claude's response
- If errors found: generate error fix plan, return to dev phase
- Track retry count with `reqtestretries`
- Max retries (3) before marking as error
- Reset counter when tests pass

### Learning System
- Projects accumulate learnings via `add_learning(prjid, desc)`
- Special `prjid=-1` for global learnings (all projects)
- Included in phase prompts via `get_learnings_with_global()`
- Helps Claude learn from past mistakes

## Things to Avoid

1. **Don't bypass settings system**: Always use `get_setting()`, not hardcoded constants
2. **Don't modify reqphase/reqstatus directly**: Use `update_request_phase()`, `update_request_status()`
3. **Don't assume sequential IDs**: Use returned ID from insert operations
4. **Don't use `.claude/` config**: BentWookie has its own settings system
5. **Don't create concurrent processing**: Architecture is intentionally sequential
6. **Don't skip validation**: Check user input before database operations

## Testing

- Tests in `test/` directory
- Run with: `pytest test/ -v`
- Mock Claude SDK in tests (it's async and requires auth)
- Test database operations with in-memory SQLite

## Debug Mode

```bash
bw loop start --foreground --debug  # Verbose logging
tail -f logs/bwloop_$(date +%Y-%m-%d).log  # Watch logs
```

Logs include:
- Request processing start/end
- Claude SDK tool usage
- Database operations (with --debug)
- Error stack traces

## Common Gotchas

1. **PID file stale after crash**: `rm data/bentwookie.pid`
2. **Settings not persisting**: Check `data/settings.json` exists and is writable
3. **Request stuck in `wip`**: Daemon crashed mid-processing, set to `tbd` manually
4. **Phase skipped**: Local-only infrastructure skips deploy/verify phases (phases.py:201-219)

## Dependencies

- `claude-agent-sdk`: Core execution engine
- `click`: CLI framework
- `flask`: Web UI
- SQLite: Built into Python

Keep dependencies minimal - avoid adding unless necessary.

## Future Enhancements

Potential improvements to consider:
- Add proper database migrations (Alembic)
- Support concurrent processing (multiple daemon instances)
- Add request dependencies/ordering
- Implement request templates
- Add more infrastructure providers
- CLI command to configure max_turns and other settings
