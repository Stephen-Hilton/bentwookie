"""BentWookie V2 - AI agent swarm orchestration framework.

BentWookie decomposes projects through a hierarchy
(Project -> Service -> Component -> Function),
manages agents as Claude Code instances, and coordinates
them via a message-based communication system.
"""

__version__ = "0.3.0"

from .constants import (
    AGENT_ROLES,
    AGENT_STATUSES,
    AGENT_STATUS_NAMES,
    BUILD_TASK_STATUSES,
    BUILD_TASK_STATUS_NAMES,
    BUILD_TASK_TYPES,
    BUILD_TASK_TYPE_NAMES,
    COMPONENT_LEVELS,
    COMPONENT_STATUSES,
    COMPONENT_STATUS_NAMES,
    DEFAULT_PRIORITY,
    INTERVIEW_STATUSES,
    INTERVIEW_TYPES,
    INTERVIEW_TYPE_NAMES,
    LEVEL_NAMES,
    MESSAGE_TYPES,
    NEXT_PHASE,
    PHASE_NAMES,
    PHASE_ORDER,
    PHASES,
    ROLE_NAMES,
    VALID_MODELS,
)

from .db import (
    create_project,
    get_project,
    get_project_by_name,
    list_projects,
    update_project,
    delete_project,
    create_component,
    get_component,
    list_components,
    get_component_tree,
    create_agent,
    get_agent,
    list_agents,
    create_interview,
    get_interview,
    list_interviews,
    get_db,
    init_db,
)

from .exceptions import (
    BentWookieError,
    ConfigurationError,
    RaceConditionError,
    StageError,
    TaskNotFoundError,
    TaskParseError,
    TaskValidationError,
    TemplateError,
    WizardError,
)

from .logging_util import (
    BWLogger,
    get_logger,
    init_logger,
)

from .models import (
    Agent,
    AgentMessage,
    BuildPlan,
    BuildTask,
    Component,
    ConnectionMap,
    DaemonState,
    Dependency,
    DesignAmendment,
    Document,
    Interview,
    InterviewMessage,
    Learning,
    Project,
    TestResult,
    TestSpec,
    Traceability,
)
