"""Constants for BentWookie package."""

# =============================================================================
# Request Phases (v2)
# =============================================================================

# Phase names in order of progression
PHASES = ["plan", "dev", "test", "deploy", "verify", "document", "commit", "complete"]

# Phase progression mapping (phase -> order index)
PHASE_ORDER = {
    "plan": 0,
    "dev": 1,
    "test": 2,
    "deploy": 3,
    "verify": 4,
    "document": 5,
    "commit": 6,
    "complete": 7,
}

# Next phase mapping
NEXT_PHASE = {
    "plan": "dev",
    "dev": "test",
    "test": "deploy",
    "deploy": "verify",
    "verify": "document",
    "document": "commit",
    "commit": "complete",
    "complete": None,
}

# Phase display names
PHASE_NAMES = {
    "plan": "Planning",
    "dev": "Development",
    "test": "Testing",
    "deploy": "Deployment",
    "verify": "Verification",
    "document": "Documentation",
    "commit": "Commit",
    "complete": "Complete",
}

# =============================================================================
# Request Statuses (v2)
# =============================================================================

# Status values (v2 - short codes)
STATUS_TBD = "tbd"        # To be done (pending)
STATUS_WIP = "wip"        # Work in progress
STATUS_DONE = "done"      # Completed successfully
STATUS_ERR = "err"        # Error occurred
STATUS_TMOUT = "tmout"    # Timeout

V2_STATUSES = [STATUS_TBD, STATUS_WIP, STATUS_DONE, STATUS_ERR, STATUS_TMOUT]

# v1 compatible status values (for backwards compatibility with core.py)
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

# Status display names
STATUS_NAMES = {
    "tbd": "Pending",
    "wip": "In Progress",
    "done": "Done",
    "err": "Error",
    "tmout": "Timeout",
}

# =============================================================================
# Request Types (v2)
# =============================================================================

TYPE_NEW_FEATURE = "new_feature"
TYPE_BUG_FIX = "bug_fix"
TYPE_ENHANCEMENT = "enhancement"

VALID_REQUEST_TYPES = [TYPE_NEW_FEATURE, TYPE_BUG_FIX, TYPE_ENHANCEMENT]

TYPE_NAMES = {
    "new_feature": "New Feature",
    "bug_fix": "Bug Fix",
    "enhancement": "Enhancement",
}

# =============================================================================
# Project Versions
# =============================================================================

VERSION_POC = "poc"
VERSION_MVP = "mvp"
VERSION_V1 = "v1"
VERSION_V1_1 = "v1.1"
VERSION_V2 = "v2"

VALID_VERSIONS = [VERSION_POC, VERSION_MVP, VERSION_V1, VERSION_V1_1, VERSION_V2]

# =============================================================================
# Project Phases
# =============================================================================

PROJECT_PHASE_DEV = "dev"
PROJECT_PHASE_QA = "qa"
PROJECT_PHASE_UAT = "uat"
PROJECT_PHASE_PROD = "prod"

VALID_PROJECT_PHASES = [PROJECT_PHASE_DEV, PROJECT_PHASE_QA, PROJECT_PHASE_UAT, PROJECT_PHASE_PROD]

# =============================================================================
# Infrastructure
# =============================================================================

# Provider options
PROVIDER_LOCAL = "local"
PROVIDER_CONTAINER = "container"
PROVIDER_AWS = "aws"
PROVIDER_GCP = "gcp"
PROVIDER_AZURE = "azure"

VALID_PROVIDERS = [PROVIDER_LOCAL, PROVIDER_CONTAINER, PROVIDER_AWS, PROVIDER_GCP, PROVIDER_AZURE]

# Infrastructure types
INFRA_COMPUTE = "compute"
INFRA_STORAGE = "storage"
INFRA_QUEUE = "queue"
INFRA_ACCESS = "access"
INFRA_UI = "ui"

VALID_INFRA_TYPES = [INFRA_COMPUTE, INFRA_STORAGE, INFRA_QUEUE, INFRA_ACCESS, INFRA_UI]

# =============================================================================
# Priority
# =============================================================================

PRIORITY_MIN = 1
PRIORITY_MAX = 10
DEFAULT_PRIORITY = 5

# =============================================================================
# Timeouts
# =============================================================================

# Phase timeouts in seconds
TIMEOUT_PLAN = 30 * 60       # 30 minutes
TIMEOUT_DEV = 4 * 60 * 60    # 4 hours
TIMEOUT_TEST = 1 * 60 * 60   # 1 hour
TIMEOUT_DEPLOY = 30 * 60     # 30 minutes
TIMEOUT_VERIFY = 30 * 60     # 30 minutes
TIMEOUT_DOCUMENT = 30 * 60   # 30 minutes
TIMEOUT_COMMIT = 10 * 60     # 10 minutes

PHASE_TIMEOUTS = {
    "plan": TIMEOUT_PLAN,
    "dev": TIMEOUT_DEV,
    "test": TIMEOUT_TEST,
    "deploy": TIMEOUT_DEPLOY,
    "verify": TIMEOUT_VERIFY,
    "document": TIMEOUT_DOCUMENT,
    "commit": TIMEOUT_COMMIT,
}

# Daemon settings
DAEMON_POLL_INTERVAL = 30    # seconds
DAEMON_MAX_TURNS = 50        # max Claude SDK turns per phase

# =============================================================================
# Paths
# =============================================================================

DEFAULT_DB_PATH = "data/bentwookie.db"
DEFAULT_DOCS_PATH = "data/docs"
DEFAULT_LOGS_PATTERN = "logs/{loopname}_{today}.log"
DEFAULT_DOC_RETENTION_DAYS = 30  # Auto-cleanup docs older than this

# =============================================================================
# Claude SDK Settings
# =============================================================================

DEFAULT_MODEL = "claude-opus-4-5"
DEFAULT_PERMISSION_MODE = "acceptEdits"

# Valid Claude models
VALID_MODELS = [
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-opus-4",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
]

# Tools allowed per phase
PHASE_TOOLS = {
    "plan": ["Read", "Glob", "Grep"],
    "dev": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    "test": ["Read", "Bash", "Glob", "Grep"],
    "deploy": ["Bash"],
    "verify": ["Read", "Bash", "WebFetch", "Glob", "Grep"],
    "document": ["Read", "Write"],
    "commit": ["Bash", "Read", "Grep"],  # Need Bash for git, Read/Grep for analysis
}

# =============================================================================
# Commit Phase Options
# =============================================================================

# Commit branch modes
COMMIT_BRANCH_CURRENT = "current"  # Commit to current branch
COMMIT_BRANCH_OTHER = "other"      # Commit to specific branch
VALID_COMMIT_BRANCHES = [COMMIT_BRANCH_CURRENT, COMMIT_BRANCH_OTHER]

# =============================================================================
# Legacy Constants (kept for backwards compatibility during migration)
# =============================================================================

# Old stage names (deprecated)
STAGES = ["1plan", "2dev", "3test", "4deploy", "5validate", "9done"]

STAGE_ORDER = {
    "1plan": 0,
    "2dev": 1,
    "3test": 2,
    "4deploy": 3,
    "5validate": 4,
    "9done": 5,
}

NEXT_STAGE = {
    "1plan": "2dev",
    "2dev": "3test",
    "3test": "4deploy",
    "4deploy": "5validate",
    "5validate": "9done",
    "9done": None,
}

# Old change types (deprecated)
CHANGE_TYPE_NEW = "New Feature"
CHANGE_TYPE_ENHANCEMENT = "Feature Enhancement"
CHANGE_TYPE_BUGFIX = "Bug-Fix"

VALID_CHANGE_TYPES = [CHANGE_TYPE_NEW, CHANGE_TYPE_ENHANCEMENT, CHANGE_TYPE_BUGFIX]

# Old project phases (deprecated)
PROJECT_PHASES = ["MVP", "V1.0", "POC", "V2.0", "Maintenance"]

# Environment variable keys (used by config.py)
ENV_KEYS = {
    "LLM_PROVIDER": "BW_LLM_PROVIDER",
    "LLM_MODEL": "BW_LLM_MODEL",
    "LLM_API_KEY": "BW_LLM_API_KEY",
    "TASKS_PATH": "BW_TASKS_PATH",
    "LOGS_PATH": "BW_LOGS_PATH",
    "ENV_PATH": "BW_ENV_PATH",
}

# File patterns (used by core.py, config.py)
TASK_FILE_EXTENSION = ".md"
BACKUP_EXTENSION = ".bkup"
RESOURCES_DIR = ".resources"
GLOBAL_DIR = "global"
LOGS_DIR = "logs"

# Template files (used by core.py)
TEMPLATE_FILE = "template.md"
INSTRUCTIONS_FILE = "instructions.md"
LEARNINGS_FILE = "learnings.md"
SETTINGS_FILE = "settings.yaml"
INTERFACES_FILE = "interfaces.md"
SETUP_FILE = "setup.md"

# YAML frontmatter delimiters
YAML_DELIMITER = "---"

# Default paths (used by config.py)
DEFAULT_TASKS_SUBDIR = "tasks"

# Timeouts for old v1 system
TIMEOUT_PLANNING = 4 * 60 * 60  # 4 hours
TIMEOUT_IN_PROGRESS = 24 * 60 * 60  # 24 hours
WHITESPACE_SLEEP = 600  # 10 minutes
RACE_CONDITION_SLEEP = 5  # seconds

# Infrastructure options for wizard (Local is default - first in each list)
COMPUTE_OPTIONS = [
    "Local",
    "AWS Lambda",
    "AWS EC2",
    "GCP Cloud Functions",
    "Azure Functions",
    "Container (Docker)",
]

STORAGE_OPTIONS = [
    "Local",
    "AWS AuroraDB",
    "AWS DynamoDB",
    "AWS S3",
    "GCP Cloud SQL",
    "Azure SQL",
]

QUEUE_OPTIONS = [
    "Local",
    "AWS Kinesis",
    "AWS SQS",
    "GCP Pub/Sub",
    "Azure Service Bus",
]

ACCESS_OPTIONS = [
    "Local",
    "AWS API Gateway",
    "GCP API Gateway",
    "Azure API Management",
    "Direct",
]
