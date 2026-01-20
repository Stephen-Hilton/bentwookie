# BentWookie

"I bent my Wookie." -- Ralph Wiggum

A framework designed to gently guide business requirements into a continuous AI dev/test/deploy/validate loop.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Initialize BentWookie templates in your project
bw --init ./myproject

# Create a new task using the planning wizard
bw --plan "My New Feature"

# Get the next prompt for an AI coding loop
bw --next_prompt "myloop"
```

## Usage in a Continuous Loop

BentWookie is designed to work in a continuous loop with AI coding assistants:

```bash
while :; do bw --next_prompt "myloop" | claude; done
```

## Task Stages

Tasks progress through the following stages:

| Stage | Description |
|-------|-------------|
| `1plan` | Planning and requirements gathering |
| `2dev` | Development and implementation |
| `3test` | Testing and quality assurance |
| `4deploy` | Deployment to target environment |
| `5validate` | Validation and acceptance testing |
| `9done` | Completed tasks |

## Commands

### Main Options

```bash
bw --init <path>           # Initialize templates in directory
bw --plan <name>           # Create a new task with the planning wizard
bw --next_prompt <loop>    # Get the next prompt for AI loop
bw --logs <path>           # Set log file path or directory
bw --tasks <path>          # Set tasks directory path
bw --env <path>            # Set path to .env file
bw --test                  # Test mode (don't move files between stages)
```

### Subcommands

```bash
# List all tasks
bw list
bw list --stage 1plan      # Filter by stage
bw list --ready            # Show only ready tasks

# Show task details
bw show tasks/1plan/my-feature.md

# Move a task to a different stage
bw move-stage --task tasks/1plan/my-feature.md
bw move-stage --task tasks/1plan/my-feature.md --stage 3test

# Update task status
bw update-status --task tasks/2dev/my-feature.md --status "In Progress"
```

## Task Statuses

- `Not Started` - Task has not been started
- `Planning` - Task is being planned
- `Ready` - Task is ready for the current stage
- `In Progress` - Task is actively being worked on
- `Complete` - Task stage is complete

## Change Types

- `New Feature` - Entirely new functionality
- `Feature Enhancement` - Improvement to existing functionality
- `Bug-Fix` - Fix for an existing bug

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BW_TASKS_PATH` | Path to tasks directory |
| `BW_LOGS_PATH` | Path to logs directory or file pattern |
| `BW_ENV_PATH` | Path to .env file |
| `BW_LLM_PROVIDER` | LLM provider (for future use) |
| `BW_LLM_MODEL` | LLM model (for future use) |
| `BW_LLM_API_KEY` | LLM API key (for future use) |

## Log Path Placeholders

Log paths support the following placeholders:

- `{today}` - Current date (YYYY-MM-DD)
- `{now}` / `{datetime}` - Current datetime (YYYY-MM-DD_HH-MM-SS)
- `{date}` - Current date (YYYY-MM-DD)
- `{time}` - Current time (HH-MM-SS)
- `{year}`, `{month}`, `{day}`, `{hour}`, `{minute}` - Individual components
- `{loopname}` / `{loop_name}` - Name of the current loop

Example: `--logs "logs/{loopname}_{today}.log"`

## License

MIT
