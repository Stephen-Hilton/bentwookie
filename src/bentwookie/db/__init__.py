"""Database module for BentWookie."""

from .connection import get_db, get_db_path, init_db, set_db_path
from .queries import (
    # Infrastructure operations (project-level)
    add_infrastructure,
    # Infrastructure option operations (wizard)
    add_infra_option,
    delete_infra_option,
    delete_infra_option_by_id,
    get_infra_options,
    get_infra_options_by_type,
    seed_default_infra_options,
    # Learning operations
    add_learning,
    # Request infrastructure operations
    add_request_infrastructure,
    # Project operations
    create_project,
    # Request operations
    create_request,
    delete_infrastructure,
    delete_learning,
    delete_project,
    delete_request,
    delete_request_infrastructure,
    get_effective_infrastructure,
    get_learning,
    get_learnings_with_global,
    get_next_request,
    get_project,
    get_project_by_name,
    get_project_infrastructure,
    get_project_learnings,
    get_request,
    get_request_infrastructure,
    list_all_learnings,
    list_projects,
    list_requests,
    update_infrastructure,
    update_learning,
    update_project,
    update_request,
    increment_request_test_retries,
    reset_request_test_retries,
    update_request_codedir,
    update_request_docpath,
    update_request_infrastructure,
    update_request_phase,
    update_request_planpath,
    update_request_status,
    update_request_testplanpath,
)

__all__ = [
    # Connection
    "get_db",
    "init_db",
    "get_db_path",
    "set_db_path",
    # Project operations
    "create_project",
    "get_project",
    "get_project_by_name",
    "list_projects",
    "update_project",
    "delete_project",
    # Request operations
    "create_request",
    "get_request",
    "get_next_request",
    "list_requests",
    "update_request",
    "update_request_status",
    "update_request_phase",
    "update_request_docpath",
    "update_request_codedir",
    "update_request_planpath",
    "update_request_testplanpath",
    "increment_request_test_retries",
    "reset_request_test_retries",
    "delete_request",
    # Infrastructure operations (project-level)
    "add_infrastructure",
    "get_project_infrastructure",
    "update_infrastructure",
    "delete_infrastructure",
    # Request infrastructure operations
    "add_request_infrastructure",
    "get_request_infrastructure",
    "update_request_infrastructure",
    "delete_request_infrastructure",
    "get_effective_infrastructure",
    # Learning operations
    "add_learning",
    "get_learning",
    "get_project_learnings",
    "get_learnings_with_global",
    "list_all_learnings",
    "update_learning",
    "delete_learning",
    # Infrastructure option operations (wizard)
    "add_infra_option",
    "get_infra_options",
    "get_infra_options_by_type",
    "delete_infra_option",
    "delete_infra_option_by_id",
    "seed_default_infra_options",
]
