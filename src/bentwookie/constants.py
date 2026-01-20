"""Constants for BentWookie package."""

# Stage names in order of progression
STAGES = ["1plan", "2dev", "3test", "4deploy", "5validate", "9done"]

# Stage progression mapping
STAGE_ORDER = {
    "1plan": 0,
    "2dev": 1,
    "3test": 2,
    "4deploy": 3,
    "5validate": 4,
    "9done": 5,
}

# Next stage mapping
NEXT_STAGE = {
    "1plan": "2dev",
    "2dev": "3test",
    "3test": "4deploy",
    "4deploy": "5validate",
    "5validate": "9done",
    "9done": None,
}

# Environment variable keys
ENV_KEYS = {
    "LLM_PROVIDER": "BW_LLM_PROVIDER",
    "LLM_MODEL": "BW_LLM_MODEL",
    "LLM_API_KEY": "BW_LLM_API_KEY",
    "TASKS_PATH": "BW_TASKS_PATH",
    "LOGS_PATH": "BW_LOGS_PATH",
    "ENV_PATH": "BW_ENV_PATH",
}

# Task status values
STATUS_NOT_STARTED = "Not Started"
STATUS_PLANNING = "Planning"
STATUS_READY = "Ready"
STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETE = "Complete"

VALID_STATUSES = [
    STATUS_NOT_STARTED,
    STATUS_PLANNING,
    STATUS_READY,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETE,
]

# Change types
CHANGE_TYPE_NEW = "New Feature"
CHANGE_TYPE_ENHANCEMENT = "Feature Enhancement"
CHANGE_TYPE_BUGFIX = "Bug-Fix"

VALID_CHANGE_TYPES = [
    CHANGE_TYPE_NEW,
    CHANGE_TYPE_ENHANCEMENT,
    CHANGE_TYPE_BUGFIX,
]

# Project phases
PROJECT_PHASES = ["MVP", "V1.0", "POC", "V2.0", "Maintenance"]

# Priority range
PRIORITY_MIN = 1
PRIORITY_MAX = 10
DEFAULT_PRIORITY = 5

# Timeouts in seconds
TIMEOUT_PLANNING = 4 * 60 * 60  # 4 hours
TIMEOUT_IN_PROGRESS = 24 * 60 * 60  # 24 hours
WHITESPACE_SLEEP = 600  # 10 minutes

# Race condition detection sleep
RACE_CONDITION_SLEEP = 5  # seconds

# File patterns
TASK_FILE_EXTENSION = ".md"
BACKUP_EXTENSION = ".bkup"
RESOURCES_DIR = ".resources"
GLOBAL_DIR = "global"
LOGS_DIR = "logs"

# Template files
TEMPLATE_FILE = "template.md"
INSTRUCTIONS_FILE = "instructions.md"
LEARNINGS_FILE = "learnings.md"
SETTINGS_FILE = "settings.yaml"
INTERFACES_FILE = "interfaces.md"
SETUP_FILE = "setup.md"

# YAML frontmatter delimiters
YAML_DELIMITER = "---"

# Default paths
DEFAULT_TASKS_SUBDIR = "tasks"
DEFAULT_LOGS_PATTERN = "logs/{loopname}_{today}.log"

# Infrastructure options (for wizard)
COMPUTE_OPTIONS = [
    "Don't Care",
    "AWS Lambda",
    "AWS EC2",
    "Local",
]

STORAGE_OPTIONS = [
    "Don't Care",
    "AWS AuroraDB",
    "AWS DynamoDB",
    "AWS S3",
    "Local",
]

QUEUE_OPTIONS = [
    "Don't Care",
    "AWS Kinesis",
    "AWS SQS",
    "Local",
]

ACCESS_OPTIONS = [
    "Don't Care",
    "AWS API Gateway",
    "Direct",
    "Local",
]
