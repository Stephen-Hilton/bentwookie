"""BentWookie v2 - AI coding loop workflow manager.

BentWookie manages development requests through phases using the
Claude Agent SDK for execution, with SQLite for state management.

Usage:
    # CLI
    bw init                          # Initialize database
    bw project create myproject      # Create a project
    bw request create myproject ...  # Create a request
    bw loop start                    # Start the daemon
    bw web                           # Start web UI

    # Python API
    from bentwookie import db, models

    # Initialize database
    db.init_db()

    # Create a project
    prjid = db.create_project("myproject", prjdesc="My awesome project")

    # Create a request
    reqid = db.create_request(
        prjid=prjid,
        reqname="Add feature",
        reqprompt="Implement user authentication"
    )
"""

# Version
__version__ = "2.0.0"

# Database operations
# Constants
from .constants import (
    DEFAULT_PRIORITY,
    NEXT_PHASE,
    PHASE_NAMES,
    PHASE_ORDER,
    PHASES,
    STATUS_NAMES,
    TYPE_NAMES,
    V2_STATUSES,
    VALID_PROJECT_PHASES,
    VALID_REQUEST_TYPES,
    VALID_STATUSES,
    VALID_VERSIONS,
)
from .db import (
    add_infrastructure,
    add_learning,
    create_project,
    create_request,
    delete_project,
    delete_request,
    get_db,
    get_next_request,
    get_project,
    get_project_by_name,
    get_project_infrastructure,
    get_project_learnings,
    get_request,
    init_db,
    list_projects,
    list_requests,
    update_project,
    update_request_phase,
    update_request_status,
)

# Exceptions
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

# Logging
from .logging_util import (
    BWLogger,
    get_logger,
    init_logger,
)

# Models
from .models import (
    DaemonStatus,
    Infrastructure,
    Learning,
    Project,
    Request,
)

# Export all public symbols
__all__ = [
    # Version
    "__version__",
    # Database
    "init_db",
    "get_db",
    "create_project",
    "get_project",
    "get_project_by_name",
    "list_projects",
    "update_project",
    "delete_project",
    "create_request",
    "get_request",
    "get_next_request",
    "list_requests",
    "update_request_status",
    "update_request_phase",
    "delete_request",
    "add_infrastructure",
    "get_project_infrastructure",
    "add_learning",
    "get_project_learnings",
    # Models
    "Project",
    "Request",
    "Infrastructure",
    "Learning",
    "DaemonStatus",
    # Constants
    "PHASES",
    "PHASE_ORDER",
    "NEXT_PHASE",
    "PHASE_NAMES",
    "V2_STATUSES",
    "VALID_STATUSES",
    "STATUS_NAMES",
    "VALID_REQUEST_TYPES",
    "TYPE_NAMES",
    "VALID_VERSIONS",
    "VALID_PROJECT_PHASES",
    "DEFAULT_PRIORITY",
    # Exceptions
    "BentWookieError",
    "TaskParseError",
    "TaskValidationError",
    "TaskNotFoundError",
    "StageError",
    "ConfigurationError",
    "TemplateError",
    "RaceConditionError",
    "WizardError",
    # Logging
    "BWLogger",
    "get_logger",
    "init_logger",
]
