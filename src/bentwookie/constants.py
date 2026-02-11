"""Constants for BentWookie V2 package."""

# =============================================================================
# Project Phases (V2 workflow)
# =============================================================================

PHASE_DEFINE = "define"
PHASE_DESIGN = "design"
PHASE_VALIDATE = "validate"
PHASE_BUILD = "build"
PHASE_COMPLETE = "complete"

PHASES = [PHASE_DEFINE, PHASE_DESIGN, PHASE_VALIDATE, PHASE_BUILD, PHASE_COMPLETE]

PHASE_ORDER = {
    "define": 0,
    "design": 1,
    "validate": 2,
    "build": 3,
    "complete": 4,
}

NEXT_PHASE = {
    "define": "design",
    "design": "validate",
    "validate": "build",
    "build": "complete",
    "complete": None,
}

PHASE_NAMES = {
    "define": "Define",
    "design": "Design",
    "validate": "Validate",
    "build": "Build",
    "complete": "Complete",
}

# =============================================================================
# Component Levels (4-level hierarchy)
# =============================================================================

LEVEL_PROJECT = "project"
LEVEL_SERVICE = "service"
LEVEL_COMPONENT = "component"
LEVEL_FUNCTION = "function"

COMPONENT_LEVELS = [
    LEVEL_PROJECT,
    LEVEL_SERVICE,
    LEVEL_COMPONENT,
    LEVEL_FUNCTION,
]

LEVEL_NAMES = {
    "project": "Project",
    "service": "Service",
    "component": "Component",
    "function": "Function",
}

LEVEL_ORDER = {
    "project": 0,
    "service": 1,
    "component": 2,
    "function": 3,
}

# =============================================================================
# Agent Roles
# =============================================================================

ROLE_ENTERPRISE_ARCHITECT = "enterprise_architect"
ROLE_BUSINESS_ARCHITECT = "business_architect"
ROLE_SERVICE_ENGINEER = "service_engineer"
ROLE_CODING_AGENT = "coding_agent"
ROLE_TESTING_AGENT = "testing_agent"

# Legacy alias for backward compatibility with interview system
ROLE_BUSINESS_OWNER = "business_owner"

AGENT_ROLES = [
    ROLE_ENTERPRISE_ARCHITECT,
    ROLE_BUSINESS_ARCHITECT,
    ROLE_SERVICE_ENGINEER,
    ROLE_CODING_AGENT,
    ROLE_TESTING_AGENT,
]

ROLE_NAMES = {
    "enterprise_architect": "Enterprise Architect",
    "business_architect": "Business Architect",
    "service_engineer": "Service Engineer",
    "coding_agent": "Coding Agent",
    "testing_agent": "Testing Agent",
    "business_owner": "Business Owner",  # legacy
}

ROLE_ABBREVIATIONS = {
    "enterprise_architect": "ea",
    "business_architect": "ba",
    "service_engineer": "se",
    "coding_agent": "ca",
    "testing_agent": "ta",
    "business_owner": "ba",  # legacy
}

# =============================================================================
# Agent Statuses
# =============================================================================

AGENT_STATUS_IDLE = "idle"
AGENT_STATUS_WORKING = "working"
AGENT_STATUS_WAITING = "waiting"
AGENT_STATUS_INTERRUPTED = "interrupted"
AGENT_STATUS_TERMINATED = "terminated"
AGENT_STATUS_ERROR = "error"

AGENT_STATUSES = [
    AGENT_STATUS_IDLE,
    AGENT_STATUS_WORKING,
    AGENT_STATUS_WAITING,
    AGENT_STATUS_INTERRUPTED,
    AGENT_STATUS_TERMINATED,
    AGENT_STATUS_ERROR,
]

AGENT_STATUS_NAMES = {
    "idle": "Idle",
    "working": "Working",
    "waiting": "Waiting",
    "interrupted": "Interrupted",
    "terminated": "Terminated",
    "error": "Error",
}

# =============================================================================
# Component Statuses
# =============================================================================

COMPONENT_STATUS_DRAFT = "draft"
COMPONENT_STATUS_DEFINED = "defined"
COMPONENT_STATUS_DESIGNED = "designed"
COMPONENT_STATUS_VALIDATED = "validated"
COMPONENT_STATUS_BUILDING = "building"
COMPONENT_STATUS_BUILT = "built"
COMPONENT_STATUS_TESTED = "tested"
COMPONENT_STATUS_ERROR = "error"

COMPONENT_STATUSES = [
    COMPONENT_STATUS_DRAFT,
    COMPONENT_STATUS_DEFINED,
    COMPONENT_STATUS_DESIGNED,
    COMPONENT_STATUS_VALIDATED,
    COMPONENT_STATUS_BUILDING,
    COMPONENT_STATUS_BUILT,
    COMPONENT_STATUS_TESTED,
    COMPONENT_STATUS_ERROR,
]

COMPONENT_STATUS_NAMES = {
    "draft": "Draft",
    "defined": "Defined",
    "designed": "Designed",
    "validated": "Validated",
    "building": "Building",
    "built": "Built",
    "tested": "Tested",
    "error": "Error",
}

# =============================================================================
# Message Types
# =============================================================================

MSG_TYPE_NORMAL = "normal"
MSG_TYPE_URGENT = "urgent"

MESSAGE_TYPES = [MSG_TYPE_NORMAL, MSG_TYPE_URGENT]

MESSAGE_STATUS_QUEUED = "queued"
MESSAGE_STATUS_DELIVERED = "delivered"
MESSAGE_STATUS_READ = "read"

MESSAGE_STATUSES = [MESSAGE_STATUS_QUEUED, MESSAGE_STATUS_DELIVERED, MESSAGE_STATUS_READ]

# =============================================================================
# Build Task Types
# =============================================================================

BUILD_TASK_IMPLEMENT = "implement"
BUILD_TASK_ASSEMBLE = "assemble"
BUILD_TASK_INTEGRATE = "integrate"
BUILD_TASK_TEST = "test"

BUILD_TASK_TYPES = [
    BUILD_TASK_IMPLEMENT,
    BUILD_TASK_ASSEMBLE,
    BUILD_TASK_INTEGRATE,
    BUILD_TASK_TEST,
]

BUILD_TASK_TYPE_NAMES = {
    "implement": "Implement",
    "assemble": "Assemble",
    "integrate": "Integrate",
    "test": "Test",
}

# =============================================================================
# Build Task Statuses
# =============================================================================

BUILD_STATUS_PENDING = "pending"
BUILD_STATUS_BLOCKED = "blocked"
BUILD_STATUS_ASSIGNED = "assigned"
BUILD_STATUS_IN_PROGRESS = "in_progress"
BUILD_STATUS_COMPLETE = "complete"
BUILD_STATUS_ERROR = "error"
BUILD_STATUS_CANCELLED = "cancelled"
BUILD_STATUS_REWORK = "rework"

BUILD_TASK_STATUSES = [
    BUILD_STATUS_PENDING,
    BUILD_STATUS_BLOCKED,
    BUILD_STATUS_ASSIGNED,
    BUILD_STATUS_IN_PROGRESS,
    BUILD_STATUS_COMPLETE,
    BUILD_STATUS_ERROR,
    BUILD_STATUS_CANCELLED,
    BUILD_STATUS_REWORK,
]

BUILD_TASK_STATUS_NAMES = {
    "pending": "Pending",
    "blocked": "Blocked",
    "assigned": "Assigned",
    "in_progress": "In Progress",
    "complete": "Complete",
    "error": "Error",
    "cancelled": "Cancelled",
    "rework": "Rework",
}

# =============================================================================
# Interview Types and Statuses
# =============================================================================

INTERVIEW_TYPE_BO = "business_owner"
INTERVIEW_TYPE_EA = "enterprise_architect"

INTERVIEW_TYPES = [INTERVIEW_TYPE_BO, INTERVIEW_TYPE_EA]

INTERVIEW_TYPE_NAMES = {
    "business_owner": "Business Owner",
    "enterprise_architect": "Enterprise Architect",
}

INTERVIEW_STATUS_PENDING = "pending"
INTERVIEW_STATUS_ACTIVE = "active"
INTERVIEW_STATUS_COMPLETE = "complete"
INTERVIEW_STATUS_ERROR = "error"

INTERVIEW_STATUSES = [
    INTERVIEW_STATUS_PENDING,
    INTERVIEW_STATUS_ACTIVE,
    INTERVIEW_STATUS_COMPLETE,
    INTERVIEW_STATUS_ERROR,
]

# =============================================================================
# Test Spec Types
# =============================================================================

TEST_TYPE_UNIT = "unit"
TEST_TYPE_INTEGRATION = "integration"
TEST_TYPE_E2E = "e2e"

TEST_TYPES = [TEST_TYPE_UNIT, TEST_TYPE_INTEGRATION, TEST_TYPE_E2E]

# =============================================================================
# Daemon Statuses
# =============================================================================

DAEMON_STATUS_STOPPED = "stopped"
DAEMON_STATUS_RUNNING = "running"
DAEMON_STATUS_PAUSED = "paused"

DAEMON_STATUSES = [DAEMON_STATUS_STOPPED, DAEMON_STATUS_RUNNING, DAEMON_STATUS_PAUSED]

# =============================================================================
# Timeouts (seconds)
# =============================================================================

TIMEOUT_DEFINE = 30 * 60        # 30 minutes
TIMEOUT_DESIGN = 2 * 60 * 60    # 2 hours
TIMEOUT_VALIDATE = 1 * 60 * 60  # 1 hour
TIMEOUT_BUILD = 4 * 60 * 60     # 4 hours

PHASE_TIMEOUTS = {
    "define": TIMEOUT_DEFINE,
    "design": TIMEOUT_DESIGN,
    "validate": TIMEOUT_VALIDATE,
    "build": TIMEOUT_BUILD,
}

DAEMON_POLL_INTERVAL = 30    # seconds
DAEMON_MAX_TURNS = 50        # max Claude SDK turns per phase
DEFAULT_MAX_AGENTS = 5       # default max concurrent agents
DEFAULT_AGENT_TIMEOUT = 30 * 60  # 30 minutes per agent task

# =============================================================================
# Paths
# =============================================================================

DEFAULT_DB_PATH = "data/bentwookie.db"
DEFAULT_DOCS_PATH = "data/docs"
DEFAULT_LOGS_PATTERN = "logs/{loopname}_{today}.log"

# =============================================================================
# Claude SDK Settings
# =============================================================================

DEFAULT_MODEL = "claude-opus-4-5"

VALID_MODELS = [
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-opus-4",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
]

# =============================================================================
# Priority
# =============================================================================

PRIORITY_MIN = 1
PRIORITY_MAX = 10
DEFAULT_PRIORITY = 5

# =============================================================================
# Commit Settings
# =============================================================================

VALID_COMMIT_BRANCHES = ["current", "other"]

# =============================================================================
# SSE Event Types
# =============================================================================

SSE_AGENT_STATUS = "agent_status"
SSE_AGENT_OUTPUT = "agent_output"
SSE_ACTIVITY = "activity"
SSE_PHASE_CHANGE = "phase_change"
SSE_BUILD_PROGRESS = "build_progress"
SSE_MESSAGE_SENT = "message_sent"
SSE_STATS_UPDATE = "stats_update"

SSE_EVENT_TYPES = [
    SSE_AGENT_STATUS,
    SSE_AGENT_OUTPUT,
    SSE_ACTIVITY,
    SSE_PHASE_CHANGE,
    SSE_BUILD_PROGRESS,
    SSE_MESSAGE_SENT,
    SSE_STATS_UPDATE,
]

# =============================================================================
# Hierarchical Settings (per-type overrides)
# =============================================================================

HIERARCHICAL_SETTINGS = [
    "model",
    "poll_interval",
    "agent_timeout",
    "max_agents",
]

# =============================================================================
# Agent Name Generator (themed names per role)
# =============================================================================

AGENT_NAME_POOL = {
    "enterprise_architect": [
        "Blueprint", "Vanguard", "Meridian", "Keystone", "Horizon",
        "Pinnacle", "Compass", "Summit", "Atlas", "Foundry",
        "Apex", "Sentinel", "Bastion", "Lighthouse", "Paragon",
    ],
    "business_architect": [
        "Catalyst", "Maven", "Strategist", "Nexus", "Clarity",
        "Visionary", "Broker", "Pathfinder", "Oracle", "Venture",
        "Mosaic", "Prism", "Charter", "Beacon", "Synapse",
    ],
    "service_engineer": [
        "Forge", "Conduit", "Piston", "Rivet", "Dynamo",
        "Wrench", "Circuit", "Bolt", "Torque", "Anchor",
        "Gearbox", "Pipeline", "Chassis", "Turbine", "Socket",
    ],
    "coding_agent": [
        "Pixel", "Bytewise", "Sparky", "Glitch", "Neon",
        "Cipher", "Dash", "Flux", "Blaze", "Echo",
        "Zen", "Turbo", "Nova", "Rocket", "Qubit",
        "Vector", "Bit", "Hex", "Nimbus", "Comet",
    ],
    "testing_agent": [
        "Watchdog", "Probe", "Scanner", "Veritas", "Audit",
        "Falcon", "Radar", "Sentry", "Inspector", "Validator",
        "Checkmate", "Guardian", "Sweep", "Gauntlet", "Litmus",
    ],
}


def generate_agent_name(role: str, existing_names: list[str] | None = None) -> str:
    """Generate a fun, unique agent name for the given role.

    Picks from the themed name pool, falling back to numbered names
    if all pool names are taken.  Appends the role abbreviation suffix,
    e.g. "Bastion (ea)", "Pixel (ca)".
    """
    import random

    abbrev = ROLE_ABBREVIATIONS.get(role, "ag")
    existing = set(existing_names or [])
    pool = AGENT_NAME_POOL.get(role, AGENT_NAME_POOL["coding_agent"])

    # Build candidate names with suffix
    available = [f"{n} ({abbrev})" for n in pool if f"{n} ({abbrev})" not in existing]
    if available:
        return random.choice(available)

    # All pool names taken; add a number suffix to a random pool name
    base = random.choice(pool)
    counter = 2
    while f"{base}-{counter} ({abbrev})" in existing:
        counter += 1
    return f"{base}-{counter} ({abbrev})"


# =============================================================================
# Task Queue Statuses
# =============================================================================

TQ_STATUS_PENDING = "pending"
TQ_STATUS_ASSIGNED = "assigned"
TQ_STATUS_IN_PROGRESS = "in_progress"
TQ_STATUS_COMPLETE = "complete"
TQ_STATUS_FAILED = "failed"
TQ_STATUS_EXPIRED = "expired"
TQ_STATUS_CANCELLED = "cancelled"

TQ_STATUSES = [
    TQ_STATUS_PENDING,
    TQ_STATUS_ASSIGNED,
    TQ_STATUS_IN_PROGRESS,
    TQ_STATUS_COMPLETE,
    TQ_STATUS_FAILED,
    TQ_STATUS_EXPIRED,
    TQ_STATUS_CANCELLED,
]

# Task Request Types
TQ_REQUEST_TASK = "task"
TQ_REQUEST_COLLAB = "collab"

TQ_REQUEST_TYPES = [TQ_REQUEST_TASK, TQ_REQUEST_COLLAB]

# =============================================================================
# Context Clearing Scopes
# =============================================================================

CONTEXT_SCOPE_PROJECT = "project"
CONTEXT_SCOPE_SERVICE = "service"
CONTEXT_SCOPE_COMPONENT = "component"
CONTEXT_SCOPE_REQUEST = "request"

ROLE_CONTEXT_SCOPE: dict[str, str] = {
    "enterprise_architect": CONTEXT_SCOPE_PROJECT,
    "business_architect": CONTEXT_SCOPE_PROJECT,
    "business_owner": CONTEXT_SCOPE_PROJECT,
    "service_engineer": CONTEXT_SCOPE_SERVICE,
    "coding_agent": CONTEXT_SCOPE_COMPONENT,
    "testing_agent": CONTEXT_SCOPE_REQUEST,
}

# Abbreviation-to-role mapping (reverse of ROLE_ABBREVIATIONS, excluding legacy)
ABBREV_TO_ROLE: dict[str, str] = {
    v: k for k, v in ROLE_ABBREVIATIONS.items() if k != "business_owner"
}

# =============================================================================
# Safe Word
# =============================================================================

DEFAULT_SAFE_WORD = "KAMILI"

# =============================================================================
# Workflow
# =============================================================================

WORKFLOW_TOTAL_STEPS = 27

# =============================================================================
# SSE Event Types (task queue additions)
# =============================================================================

SSE_TASK_QUEUED = "task_queued"
SSE_TASK_ASSIGNED = "task_assigned"
SSE_TASK_COMPLETE = "task_complete"
SSE_TASK_FAILED = "task_failed"
SSE_PROGRESS_UPDATE = "progress_update"

# Per-type agent limits (defaults)
DEFAULT_MAX_ENTERPRISE_ARCHITECT = 1
DEFAULT_MAX_BUSINESS_ARCHITECT = 1
DEFAULT_MAX_SERVICE_ENGINEER = 5
DEFAULT_MAX_CODING_AGENT = 10
DEFAULT_MAX_TESTING_AGENT = 5
