"""Database module for BentWookie V2."""

from .connection import get_db, get_db_path, init_db, reset_db, set_db_path
from .queries import (
    # Project operations
    create_project,
    get_project,
    get_project_by_name,
    list_projects,
    update_project,
    delete_project,
    # Component operations
    create_component,
    get_component,
    list_components,
    get_component_tree,
    get_component_ancestors,
    get_component_children,
    get_component_with_stats,
    update_component,
    delete_component,
    # Connection map operations
    create_connection,
    get_connections_for_component,
    delete_connection,
    # Dependency operations
    create_dependency,
    get_dependencies,
    get_dependents,
    get_dependency_graph,
    find_ready_components,
    delete_dependency,
    # Agent operations
    create_agent,
    get_agent,
    list_agents,
    update_agent,
    delete_agent,
    count_active_agents,
    # Agent message operations
    create_message,
    create_system_log,
    get_message,
    list_messages,
    dequeue_message,
    mark_message_read,
    count_pending_messages,
    # Interview operations
    create_interview,
    get_interview,
    list_interviews,
    update_interview,
    delete_interview,
    # Interview message operations
    create_interview_message,
    get_interview_messages,
    # Test spec operations
    create_test_spec,
    get_test_spec,
    list_test_specs,
    update_test_spec,
    delete_test_spec,
    # Build task operations
    create_build_task,
    get_build_task,
    list_build_tasks,
    update_build_task,
    get_build_progress,
    # Build plan operations
    create_build_plan,
    get_build_plan,
    update_build_plan,
    # Design amendment operations
    create_design_amendment,
    list_design_amendments,
    # Traceability operations
    create_traceability,
    list_traceability,
    # Learning operations
    add_learning,
    get_learning,
    list_learnings,
    update_learning,
    delete_learning,
    # Daemon state operations
    set_daemon_state,
    get_daemon_state,
    clear_daemon_state,
    update_daemon_heartbeat,
    # Document operations
    create_document,
    get_document,
    list_documents,
    delete_document,
    # Test result operations
    create_test_result,
    list_test_results,
    # Agent output operations
    append_agent_output,
    get_agent_output,
    # Agent settings operations (hierarchical)
    set_agent_setting,
    get_agent_setting,
    list_agent_settings,
    delete_agent_setting,
    # Agent context operations
    save_agent_context,
    get_latest_agent_context,
    list_agent_contexts,
    # Tech stack catalog operations
    search_techstack_catalog,
    add_techstack_entry,
    delete_techstack_entry,
    # Agent count by role
    count_agents_by_role,
    # Stats / dashboard
    get_project_stats,
    get_dashboard_stats,
    # Task queue operations
    enqueue_task,
    get_task,
    list_tasks,
    update_task,
    find_ready_tasks,
    assign_task,
    complete_task,
    fail_task,
    expire_overdue_tasks,
    get_active_task_for_agent,
    get_task_queue_stats,
    dedup_tasks,
    build_task_library,
    build_swarm_summary,
    calculate_project_progress,
    save_scoped_context,
    get_context_for_scope,
)

__all__ = [
    # Connection
    "get_db",
    "init_db",
    "reset_db",
    "get_db_path",
    "set_db_path",
    # Project
    "create_project",
    "get_project",
    "get_project_by_name",
    "list_projects",
    "update_project",
    "delete_project",
    # Component
    "create_component",
    "get_component",
    "list_components",
    "get_component_tree",
    "get_component_ancestors",
    "get_component_children",
    "get_component_with_stats",
    "update_component",
    "delete_component",
    # Connection map
    "create_connection",
    "get_connections_for_component",
    "delete_connection",
    # Dependency
    "create_dependency",
    "get_dependencies",
    "get_dependents",
    "get_dependency_graph",
    "find_ready_components",
    "delete_dependency",
    # Agent
    "create_agent",
    "get_agent",
    "list_agents",
    "update_agent",
    "delete_agent",
    "count_active_agents",
    # Agent message
    "create_message",
    "create_system_log",
    "get_message",
    "list_messages",
    "dequeue_message",
    "mark_message_read",
    "count_pending_messages",
    # Interview
    "create_interview",
    "get_interview",
    "list_interviews",
    "update_interview",
    "delete_interview",
    # Interview message
    "create_interview_message",
    "get_interview_messages",
    # Test spec
    "create_test_spec",
    "get_test_spec",
    "list_test_specs",
    "update_test_spec",
    "delete_test_spec",
    # Build task
    "create_build_task",
    "get_build_task",
    "list_build_tasks",
    "update_build_task",
    "get_build_progress",
    # Build plan
    "create_build_plan",
    "get_build_plan",
    "update_build_plan",
    # Design amendment
    "create_design_amendment",
    "list_design_amendments",
    # Traceability
    "create_traceability",
    "list_traceability",
    # Learning
    "add_learning",
    "get_learning",
    "list_learnings",
    "update_learning",
    "delete_learning",
    # Daemon state
    "set_daemon_state",
    "get_daemon_state",
    "clear_daemon_state",
    "update_daemon_heartbeat",
    # Document
    "create_document",
    "get_document",
    "list_documents",
    "delete_document",
    # Test result
    "create_test_result",
    "list_test_results",
    # Agent output
    "append_agent_output",
    "get_agent_output",
    # Agent settings (hierarchical)
    "set_agent_setting",
    "get_agent_setting",
    "list_agent_settings",
    "delete_agent_setting",
    # Agent context
    "save_agent_context",
    "get_latest_agent_context",
    "list_agent_contexts",
    # Tech stack catalog
    "search_techstack_catalog",
    "add_techstack_entry",
    "delete_techstack_entry",
    # Agent count by role
    "count_agents_by_role",
    # Stats
    "get_project_stats",
    "get_dashboard_stats",
    # Task queue
    "enqueue_task",
    "get_task",
    "list_tasks",
    "update_task",
    "find_ready_tasks",
    "assign_task",
    "complete_task",
    "fail_task",
    "expire_overdue_tasks",
    "get_active_task_for_agent",
    "get_task_queue_stats",
    "dedup_tasks",
    "build_task_library",
    "build_swarm_summary",
    "calculate_project_progress",
    "save_scoped_context",
    "get_context_for_scope",
]
