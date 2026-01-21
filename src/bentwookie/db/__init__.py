"""Database module for BentWookie."""

from .connection import get_db, get_db_path, init_db, set_db_path
from .queries import (
    # Infrastructure operations
    add_infrastructure,
    # Learning operations
    add_learning,
    # Project operations
    create_project,
    # Request operations
    create_request,
    delete_infrastructure,
    delete_learning,
    delete_project,
    delete_request,
    get_next_request,
    get_project,
    get_project_by_name,
    get_project_infrastructure,
    get_project_learnings,
    get_request,
    list_projects,
    list_requests,
    update_project,
    update_request_codedir,
    update_request_docpath,
    update_request_phase,
    update_request_status,
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
    "update_request_status",
    "update_request_phase",
    "update_request_docpath",
    "update_request_codedir",
    "delete_request",
    # Infrastructure operations
    "add_infrastructure",
    "get_project_infrastructure",
    "delete_infrastructure",
    # Learning operations
    "add_learning",
    "get_project_learnings",
    "delete_learning",
]
