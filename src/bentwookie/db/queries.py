"""Database query operations for BentWookie V2."""

from datetime import datetime

from .connection import get_db

# =============================================================================
# Project Operations
# =============================================================================


def create_project(
    prjname: str,
    prjphase: str = "define",
    prjdesc: str | None = None,
    prjcodedir: str | None = None,
    prjmodel: str | None = None,
    prjmaxagents: int = 5,
    prjpriority: int = 5,
) -> int:
    """Create a new project.

    Returns:
        The new project ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO project (prjname, prjphase, prjdesc, prjcodedir, prjmodel, prjmaxagents, prjpriority)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (prjname, prjphase, prjdesc, prjcodedir, prjmodel, prjmaxagents, prjpriority),
        )
        return cursor.lastrowid


def get_project(prjid: int) -> dict | None:
    """Get a project by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM project WHERE prjid = ?", (prjid,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_project_by_name(prjname: str) -> dict | None:
    """Get a project by name."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM project WHERE prjname = ?", (prjname,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_projects(phase: str | None = None) -> list[dict]:
    """List all projects, optionally filtered by phase."""
    with get_db() as conn:
        if phase:
            cursor = conn.execute(
                "SELECT * FROM project WHERE prjphase = ? ORDER BY prjtouchts DESC",
                (phase,),
            )
        else:
            cursor = conn.execute("SELECT * FROM project ORDER BY prjtouchts DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_project(prjid: int, **kwargs) -> None:
    """Update a project. Pass field names as keyword arguments."""
    allowed = {"prjname", "prjphase", "prjdesc", "prjcodedir", "prjmodel", "prjmaxagents", "prjpriority"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["prjtouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [prjid]

    with get_db() as conn:
        conn.execute(f"UPDATE project SET {set_clause} WHERE prjid = ?", values)


def delete_project(prjid: int) -> None:
    """Delete a project and all cascading records."""
    with get_db() as conn:
        conn.execute("DELETE FROM project WHERE prjid = ?", (prjid,))


# =============================================================================
# Component Operations
# =============================================================================


def create_component(
    prjid: int,
    cmpname: str,
    cmplevel: str,
    parent_id: int | None = None,
    cmpstatus: str = "draft",
    cmpdesc: str | None = None,
    cmpspec: str | None = None,
    cmporder: int = 0,
) -> int:
    """Create a new component.

    Returns:
        The new component ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO component
               (prjid, parent_id, cmpname, cmplevel, cmpstatus, cmpdesc, cmpspec, cmporder)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (prjid, parent_id, cmpname, cmplevel, cmpstatus, cmpdesc, cmpspec, cmporder),
        )
        return cursor.lastrowid


def get_component(cmpid: int) -> dict | None:
    """Get a component by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM component WHERE cmpid = ?", (cmpid,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_components(
    prjid: int | None = None,
    parent_id: int | None = None,
    level: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List components with optional filters."""
    conditions = []
    params: list = []

    if prjid is not None:
        conditions.append("prjid = ?")
        params.append(prjid)
    if parent_id is not None:
        conditions.append("parent_id = ?")
        params.append(parent_id)
    if level is not None:
        conditions.append("cmplevel = ?")
        params.append(level)
    if status is not None:
        conditions.append("cmpstatus = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"SELECT * FROM component WHERE {where} ORDER BY cmporder, cmpname",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def get_component_tree(prjid: int) -> list[dict]:
    """Get the full component tree for a project using recursive CTE.

    Returns:
        Flat list with depth column for tree rendering, children grouped
        under their parent via a sort_path column.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """WITH RECURSIVE tree AS (
                SELECT cmpid, parent_id, cmpname, cmplevel, cmpstatus, cmpdesc,
                       cmpspec, is_collapsed, cmporder, 0 AS depth,
                       printf('%04d-%s', cmporder, cmpname) AS sort_path
                FROM component
                WHERE prjid = ? AND parent_id IS NULL
                UNION ALL
                SELECT c.cmpid, c.parent_id, c.cmpname, c.cmplevel, c.cmpstatus,
                       c.cmpdesc, c.cmpspec, c.is_collapsed, c.cmporder, t.depth + 1,
                       t.sort_path || '/' || printf('%04d-%s', c.cmporder, c.cmpname)
                FROM component c
                JOIN tree t ON c.parent_id = t.cmpid
            )
            SELECT cmpid, parent_id, cmpname, cmplevel, cmpstatus, cmpdesc,
                   cmpspec, is_collapsed, cmporder, depth
            FROM tree ORDER BY sort_path""",
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_component_ancestors(cmpid: int) -> list[dict]:
    """Get all ancestors of a component (for breadcrumb navigation)."""
    with get_db() as conn:
        cursor = conn.execute(
            """WITH RECURSIVE ancestors AS (
                SELECT cmpid, parent_id, cmpname, cmplevel, 0 AS depth
                FROM component WHERE cmpid = ?
                UNION ALL
                SELECT c.cmpid, c.parent_id, c.cmpname, c.cmplevel, a.depth + 1
                FROM component c
                JOIN ancestors a ON c.cmpid = a.parent_id
            )
            SELECT * FROM ancestors ORDER BY depth DESC""",
            (cmpid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_component_children(cmpid: int) -> list[dict]:
    """Get direct children of a component."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM component WHERE parent_id = ? ORDER BY cmporder, cmpname",
            (cmpid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def update_component(cmpid: int, **kwargs) -> None:
    """Update a component."""
    allowed = {"cmpname", "cmplevel", "cmpstatus", "cmpdesc", "cmpspec", "is_collapsed", "cmporder", "parent_id"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["cmptouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [cmpid]

    with get_db() as conn:
        conn.execute(f"UPDATE component SET {set_clause} WHERE cmpid = ?", values)


def get_component_with_stats(cmpid: int) -> dict | None:
    """Get a component with child counts, progress, and test summary."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM component WHERE parent_id = c.cmpid) AS child_count,
                      (SELECT COUNT(*) FROM component WHERE parent_id = c.cmpid
                       AND cmpstatus IN ('built', 'tested')) AS children_complete,
                      (SELECT COUNT(*) FROM test_spec WHERE cmpid = c.cmpid) AS test_count,
                      (SELECT COUNT(*) FROM test_result tr
                       JOIN test_spec ts ON tr.tsid = ts.tsid
                       WHERE ts.cmpid = c.cmpid AND tr.trpassed = 1) AS tests_passed,
                      (SELECT agtname FROM agent WHERE agtcmpid = c.cmpid
                       AND agtstatus NOT IN ('terminated') LIMIT 1) AS assigned_agent,
                      p.prjname
               FROM component c
               JOIN project p ON c.prjid = p.prjid
               WHERE c.cmpid = ?""",
            (cmpid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_component(cmpid: int) -> None:
    """Delete a component and all cascading records."""
    with get_db() as conn:
        conn.execute("DELETE FROM component WHERE cmpid = ?", (cmpid,))


# =============================================================================
# Connection Map Operations
# =============================================================================


def create_connection(
    from_cmpid: int,
    to_cmpid: int,
    condesc: str | None = None,
    contype: str = "data",
) -> int:
    """Create a connection between components."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO connection_map (from_cmpid, to_cmpid, condesc, contype) VALUES (?, ?, ?, ?)",
            (from_cmpid, to_cmpid, condesc, contype),
        )
        return cursor.lastrowid


def get_connections_for_component(cmpid: int) -> list[dict]:
    """Get all connections involving a component (both directions)."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT cm.*, c1.cmpname AS from_name, c2.cmpname AS to_name
               FROM connection_map cm
               JOIN component c1 ON cm.from_cmpid = c1.cmpid
               JOIN component c2 ON cm.to_cmpid = c2.cmpid
               WHERE cm.from_cmpid = ? OR cm.to_cmpid = ?""",
            (cmpid, cmpid),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_connection(conid: int) -> None:
    """Delete a connection."""
    with get_db() as conn:
        conn.execute("DELETE FROM connection_map WHERE conid = ?", (conid,))


# =============================================================================
# Dependency Operations
# =============================================================================


def create_dependency(cmpid: int, depends_on_cmpid: int) -> int:
    """Create a dependency edge."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO dependency (cmpid, depends_on_cmpid) VALUES (?, ?)",
            (cmpid, depends_on_cmpid),
        )
        return cursor.lastrowid


def get_dependencies(cmpid: int) -> list[dict]:
    """Get components that a given component depends on."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT d.*, c.cmpname AS depends_on_name, c.cmpstatus AS depends_on_status
               FROM dependency d
               JOIN component c ON d.depends_on_cmpid = c.cmpid
               WHERE d.cmpid = ?""",
            (cmpid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_dependents(cmpid: int) -> list[dict]:
    """Get components that depend on a given component."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT d.*, c.cmpname AS dependent_name
               FROM dependency d
               JOIN component c ON d.cmpid = c.cmpid
               WHERE d.depends_on_cmpid = ?""",
            (cmpid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_dependency_graph(prjid: int) -> dict:
    """Get the full dependency graph for a project.

    Returns:
        Dict with 'nodes' (list of components) and 'edges' (list of dependency pairs).
    """
    with get_db() as conn:
        nodes_cursor = conn.execute(
            "SELECT cmpid, cmpname, cmplevel, cmpstatus FROM component WHERE prjid = ?",
            (prjid,),
        )
        nodes = [dict(row) for row in nodes_cursor.fetchall()]

        edges_cursor = conn.execute(
            """SELECT d.cmpid, d.depends_on_cmpid
               FROM dependency d
               JOIN component c ON d.cmpid = c.cmpid
               WHERE c.prjid = ?""",
            (prjid,),
        )
        edges = [dict(row) for row in edges_cursor.fetchall()]

    return {"nodes": nodes, "edges": edges}


def find_ready_components(prjid: int) -> list[dict]:
    """Find components whose dependencies are all satisfied (status in built/tested).

    These are candidates for assignment to agents.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT c.* FROM component c
               WHERE c.prjid = ?
               AND c.cmpstatus = 'validated'
               AND NOT EXISTS (
                   SELECT 1 FROM dependency d
                   JOIN component dep ON d.depends_on_cmpid = dep.cmpid
                   WHERE d.cmpid = c.cmpid
                   AND dep.cmpstatus NOT IN ('built', 'tested')
               )""",
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_dependency(depid: int) -> None:
    """Delete a dependency."""
    with get_db() as conn:
        conn.execute("DELETE FROM dependency WHERE depid = ?", (depid,))


# =============================================================================
# Agent Operations
# =============================================================================


def create_agent(
    prjid: int,
    agtrole: str,
    agtname: str | None = None,
    agtmodel: str | None = None,
    agtcmpid: int | None = None,
) -> int:
    """Create a new agent."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO agent (prjid, agtrole, agtname, agtmodel, agtcmpid, agtstarted)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (prjid, agtrole, agtname, agtmodel, agtcmpid, datetime.now()),
        )
        return cursor.lastrowid


def get_agent(agtid: int) -> dict | None:
    """Get an agent by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT a.*, c.cmpname, p.prjname
               FROM agent a
               LEFT JOIN component c ON a.agtcmpid = c.cmpid
               LEFT JOIN project p ON a.prjid = p.prjid
               WHERE a.agtid = ?""",
            (agtid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_agents(
    prjid: int | None = None,
    status: str | None = None,
    role: str | None = None,
) -> list[dict]:
    """List agents with optional filters."""
    conditions = []
    params: list = []

    if prjid is not None:
        conditions.append("a.prjid = ?")
        params.append(prjid)
    if status is not None:
        conditions.append("a.agtstatus = ?")
        params.append(status)
    if role is not None:
        conditions.append("a.agtrole = ?")
        params.append(role)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT a.*, c.cmpname, p.prjname
                FROM agent a
                LEFT JOIN component c ON a.agtcmpid = c.cmpid
                LEFT JOIN project p ON a.prjid = p.prjid
                WHERE {where}
                ORDER BY a.agttouchts DESC""",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def update_agent(agtid: int, **kwargs) -> None:
    """Update an agent."""
    allowed = {"agtstatus", "agtname", "agtmodel", "agtshellpid", "agtcmpid", "agterror"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["agttouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [agtid]

    with get_db() as conn:
        conn.execute(f"UPDATE agent SET {set_clause} WHERE agtid = ?", values)


def delete_agent(agtid: int) -> None:
    """Delete an agent."""
    with get_db() as conn:
        conn.execute("DELETE FROM agent WHERE agtid = ?", (agtid,))


def count_active_agents(prjid: int) -> int:
    """Count agents that are actively working for a project."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM agent WHERE prjid = ? AND agtstatus IN ('working', 'waiting', 'idle')",
            (prjid,),
        )
        return cursor.fetchone()[0]


# =============================================================================
# Agent Message Operations
# =============================================================================


def create_message(
    to_agtid: int,
    msgbody: str,
    from_agtid: int | None = None,
    msgtype: str = "normal",
) -> int:
    """Create a new message."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO agent_message (from_agtid, to_agtid, msgtype, msgbody) VALUES (?, ?, ?, ?)",
            (from_agtid, to_agtid, msgtype, msgbody),
        )
        return cursor.lastrowid


def get_message(msgid: int) -> dict | None:
    """Get a message by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT m.*, a1.agtname AS from_name, a2.agtname AS to_name
               FROM agent_message m
               LEFT JOIN agent a1 ON m.from_agtid = a1.agtid
               LEFT JOIN agent a2 ON m.to_agtid = a2.agtid
               WHERE m.msgid = ?""",
            (msgid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_messages(
    to_agtid: int | None = None,
    from_agtid: int | None = None,
    msgtype: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List messages with optional filters."""
    conditions = []
    params: list = []

    if to_agtid is not None:
        conditions.append("m.to_agtid = ?")
        params.append(to_agtid)
    if from_agtid is not None:
        conditions.append("m.from_agtid = ?")
        params.append(from_agtid)
    if msgtype is not None:
        conditions.append("m.msgtype = ?")
        params.append(msgtype)
    if status is not None:
        conditions.append("m.msgstatus = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT m.*, a1.agtname AS from_name, a2.agtname AS to_name
                FROM agent_message m
                LEFT JOIN agent a1 ON m.from_agtid = a1.agtid
                LEFT JOIN agent a2 ON m.to_agtid = a2.agtid
                WHERE {where}
                ORDER BY
                    CASE m.msgtype WHEN 'urgent' THEN 0 ELSE 1 END,
                    m.msgtouchts DESC
                LIMIT ?""",
            params + [limit],
        )
        return [dict(row) for row in cursor.fetchall()]


def dequeue_message(agtid: int) -> dict | None:
    """Get and mark the next pending message for an agent (urgent first)."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT * FROM agent_message
               WHERE to_agtid = ? AND msgstatus = 'queued'
               ORDER BY
                   CASE msgtype WHEN 'urgent' THEN 0 ELSE 1 END,
                   msgtouchts ASC
               LIMIT 1""",
            (agtid,),
        )
        row = cursor.fetchone()
        if row:
            msg = dict(row)
            conn.execute(
                "UPDATE agent_message SET msgstatus = 'delivered' WHERE msgid = ?",
                (msg["msgid"],),
            )
            return msg
        return None


def mark_message_read(msgid: int) -> None:
    """Mark a message as read."""
    with get_db() as conn:
        conn.execute(
            "UPDATE agent_message SET msgstatus = 'read' WHERE msgid = ?",
            (msgid,),
        )


def create_system_log(msgbody: str, related_agtid: int | None = None) -> int:
    """Create a system log message (no sender/receiver required)."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO agent_message (from_agtid, to_agtid, msgtype, msgstatus, msgbody) VALUES (?, ?, 'normal', 'read', ?)",
            (related_agtid, related_agtid, msgbody),
        )
        return cursor.lastrowid


def count_pending_messages(agtid: int | None = None) -> int:
    """Count queued messages, optionally for a specific agent."""
    with get_db() as conn:
        if agtid is not None:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM agent_message WHERE to_agtid = ? AND msgstatus = 'queued'",
                (agtid,),
            )
        else:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM agent_message WHERE msgstatus = 'queued'"
            )
        return cursor.fetchone()[0]


# =============================================================================
# Interview Operations
# =============================================================================


def create_interview(prjid: int, itvtype: str) -> int:
    """Create a new interview session."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO interview (prjid, itvtype) VALUES (?, ?)",
            (prjid, itvtype),
        )
        return cursor.lastrowid


def get_interview(itvid: int) -> dict | None:
    """Get an interview by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT i.*, p.prjname,
                      (SELECT COUNT(*) FROM interview_message WHERE itvid = i.itvid) AS message_count
               FROM interview i
               JOIN project p ON i.prjid = p.prjid
               WHERE i.itvid = ?""",
            (itvid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_interviews(prjid: int | None = None, status: str | None = None) -> list[dict]:
    """List interviews with optional filters."""
    conditions = []
    params: list = []

    if prjid is not None:
        conditions.append("i.prjid = ?")
        params.append(prjid)
    if status is not None:
        conditions.append("i.itvstatus = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT i.*, p.prjname,
                       (SELECT COUNT(*) FROM interview_message WHERE itvid = i.itvid) AS message_count
                FROM interview i
                JOIN project p ON i.prjid = p.prjid
                WHERE {where}
                ORDER BY i.itvtouchts DESC""",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def update_interview(itvid: int, **kwargs) -> None:
    """Update an interview."""
    allowed = {"itvstatus", "itvsummary"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["itvtouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [itvid]

    with get_db() as conn:
        conn.execute(f"UPDATE interview SET {set_clause} WHERE itvid = ?", values)


def delete_interview(itvid: int) -> None:
    """Delete an interview and all its messages."""
    with get_db() as conn:
        conn.execute("DELETE FROM interview WHERE itvid = ?", (itvid,))


# =============================================================================
# Interview Message Operations
# =============================================================================


def create_interview_message(itvid: int, imsgsender: str, imsgcontent: str) -> int:
    """Add a message to an interview."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO interview_message (itvid, imsgsender, imsgcontent) VALUES (?, ?, ?)",
            (itvid, imsgsender, imsgcontent),
        )
        return cursor.lastrowid


def get_interview_messages(itvid: int) -> list[dict]:
    """Get all messages for an interview in chronological order."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM interview_message WHERE itvid = ? ORDER BY imsgtouchts ASC",
            (itvid,),
        )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Test Spec Operations
# =============================================================================


def create_test_spec(
    cmpid: int,
    tsname: str,
    tsdesc: str | None = None,
    tstype: str = "unit",
) -> int:
    """Create a test specification."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO test_spec (cmpid, tsname, tsdesc, tstype) VALUES (?, ?, ?, ?)",
            (cmpid, tsname, tsdesc, tstype),
        )
        return cursor.lastrowid


def get_test_spec(tsid: int) -> dict | None:
    """Get a test spec by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT ts.*, c.cmpname
               FROM test_spec ts
               JOIN component c ON ts.cmpid = c.cmpid
               WHERE ts.tsid = ?""",
            (tsid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_test_specs(cmpid: int | None = None, prjid: int | None = None) -> list[dict]:
    """List test specs, optionally filtered."""
    with get_db() as conn:
        if cmpid is not None:
            cursor = conn.execute(
                """SELECT ts.*, c.cmpname
                   FROM test_spec ts
                   JOIN component c ON ts.cmpid = c.cmpid
                   WHERE ts.cmpid = ?
                   ORDER BY ts.tsname""",
                (cmpid,),
            )
        elif prjid is not None:
            cursor = conn.execute(
                """SELECT ts.*, c.cmpname
                   FROM test_spec ts
                   JOIN component c ON ts.cmpid = c.cmpid
                   WHERE c.prjid = ?
                   ORDER BY c.cmpname, ts.tsname""",
                (prjid,),
            )
        else:
            cursor = conn.execute(
                """SELECT ts.*, c.cmpname
                   FROM test_spec ts
                   JOIN component c ON ts.cmpid = c.cmpid
                   ORDER BY ts.tsname"""
            )
        return [dict(row) for row in cursor.fetchall()]


def update_test_spec(tsid: int, **kwargs) -> None:
    """Update a test spec."""
    allowed = {"tsname", "tsdesc", "tstype", "tsstatus"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["tstouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tsid]

    with get_db() as conn:
        conn.execute(f"UPDATE test_spec SET {set_clause} WHERE tsid = ?", values)


def delete_test_spec(tsid: int) -> None:
    """Delete a test spec."""
    with get_db() as conn:
        conn.execute("DELETE FROM test_spec WHERE tsid = ?", (tsid,))


# =============================================================================
# Build Task Operations
# =============================================================================


def create_build_task(
    cmpid: int,
    bttype: str = "implement",
    btprompt: str | None = None,
) -> int:
    """Create a build task."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO build_task (cmpid, bttype, btprompt) VALUES (?, ?, ?)",
            (cmpid, bttype, btprompt),
        )
        return cursor.lastrowid


def get_build_task(btid: int) -> dict | None:
    """Get a build task by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT bt.*, c.cmpname, a.agtname
               FROM build_task bt
               JOIN component c ON bt.cmpid = c.cmpid
               LEFT JOIN agent a ON bt.agtid = a.agtid
               WHERE bt.btid = ?""",
            (btid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_build_tasks(
    prjid: int | None = None,
    status: str | None = None,
    agtid: int | None = None,
) -> list[dict]:
    """List build tasks with optional filters."""
    conditions = []
    params: list = []

    if prjid is not None:
        conditions.append("c.prjid = ?")
        params.append(prjid)
    if status is not None:
        conditions.append("bt.btstatus = ?")
        params.append(status)
    if agtid is not None:
        conditions.append("bt.agtid = ?")
        params.append(agtid)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT bt.*, c.cmpname, a.agtname
                FROM build_task bt
                JOIN component c ON bt.cmpid = c.cmpid
                LEFT JOIN agent a ON bt.agtid = a.agtid
                WHERE {where}
                ORDER BY bt.bttouchts DESC""",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def update_build_task(btid: int, **kwargs) -> None:
    """Update a build task."""
    allowed = {"agtid", "btstatus", "btprompt", "btresult", "bterror"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["bttouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [btid]

    with get_db() as conn:
        conn.execute(f"UPDATE build_task SET {set_clause} WHERE btid = ?", values)


def get_build_progress(prjid: int) -> dict:
    """Get build progress summary for a project."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT btstatus, COUNT(*) AS cnt
               FROM build_task bt
               JOIN component c ON bt.cmpid = c.cmpid
               WHERE c.prjid = ?
               GROUP BY btstatus""",
            (prjid,),
        )
        counts = {row["btstatus"]: row["cnt"] for row in cursor.fetchall()}
        total = sum(counts.values())
        return {
            "total": total,
            "complete": counts.get("complete", 0),
            "in_progress": counts.get("in_progress", 0) + counts.get("assigned", 0),
            "pending": counts.get("pending", 0),
            "blocked": counts.get("blocked", 0),
            "error": counts.get("error", 0),
            "counts": counts,
        }


# =============================================================================
# Build Plan Operations
# =============================================================================


def create_build_plan(cmpid: int, bpcontent: str, bpstatus: str = "draft") -> int:
    """Create a build plan."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO build_plan (cmpid, bpcontent, bpstatus) VALUES (?, ?, ?)",
            (cmpid, bpcontent, bpstatus),
        )
        return cursor.lastrowid


def get_build_plan(cmpid: int) -> dict | None:
    """Get the build plan for a component."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM build_plan WHERE cmpid = ? ORDER BY bptouchts DESC LIMIT 1",
            (cmpid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_build_plan(bpid: int, **kwargs) -> None:
    """Update a build plan."""
    allowed = {"bpcontent", "bpstatus"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["bptouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [bpid]

    with get_db() as conn:
        conn.execute(f"UPDATE build_plan SET {set_clause} WHERE bpid = ?", values)


# =============================================================================
# Design Amendment Operations
# =============================================================================


def create_design_amendment(
    cmpid: int,
    dareason: str,
    dachange: str,
    agtid: int | None = None,
) -> int:
    """Create a design amendment (append-only)."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO design_amendment (cmpid, agtid, dareason, dachange) VALUES (?, ?, ?, ?)",
            (cmpid, agtid, dareason, dachange),
        )
        return cursor.lastrowid


def list_design_amendments(cmpid: int | None = None, prjid: int | None = None) -> list[dict]:
    """List design amendments."""
    with get_db() as conn:
        if cmpid is not None:
            cursor = conn.execute(
                "SELECT * FROM design_amendment WHERE cmpid = ? ORDER BY datouchts DESC",
                (cmpid,),
            )
        elif prjid is not None:
            cursor = conn.execute(
                """SELECT da.* FROM design_amendment da
                   JOIN component c ON da.cmpid = c.cmpid
                   WHERE c.prjid = ? ORDER BY da.datouchts DESC""",
                (prjid,),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM design_amendment ORDER BY datouchts DESC"
            )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Traceability Operations
# =============================================================================


def create_traceability(
    prjid: int,
    trcgoal: str,
    cmpid: int | None = None,
    trcdesc: str | None = None,
) -> int:
    """Create a traceability mapping."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO traceability (prjid, cmpid, trcgoal, trcdesc) VALUES (?, ?, ?, ?)",
            (prjid, cmpid, trcgoal, trcdesc),
        )
        return cursor.lastrowid


def list_traceability(prjid: int) -> list[dict]:
    """List traceability mappings for a project."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT t.*, c.cmpname
               FROM traceability t
               LEFT JOIN component c ON t.cmpid = c.cmpid
               WHERE t.prjid = ?
               ORDER BY t.trctouchts""",
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Learning Operations
# =============================================================================


def add_learning(
    prjid: int,
    lrndesc: str,
    lrnsource: str | None = None,
    lrnphase: str | None = None,
) -> int:
    """Add a learning."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO learning (prjid, lrndesc, lrnsource, lrnphase) VALUES (?, ?, ?, ?)",
            (prjid, lrndesc, lrnsource, lrnphase),
        )
        return cursor.lastrowid


def get_learning(lrnid: int) -> dict | None:
    """Get a learning by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM learning WHERE lrnid = ?", (lrnid,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_learnings(prjid: int | None = None) -> list[dict]:
    """List learnings, optionally by project."""
    with get_db() as conn:
        if prjid is not None:
            cursor = conn.execute(
                "SELECT * FROM learning WHERE prjid = ? ORDER BY lrntouchts DESC",
                (prjid,),
            )
        else:
            cursor = conn.execute("SELECT * FROM learning ORDER BY lrntouchts DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_learning(lrnid: int, lrndesc: str) -> None:
    """Update a learning."""
    with get_db() as conn:
        conn.execute(
            "UPDATE learning SET lrndesc = ?, lrntouchts = ? WHERE lrnid = ?",
            (lrndesc, datetime.now(), lrnid),
        )


def delete_learning(lrnid: int) -> None:
    """Delete a learning."""
    with get_db() as conn:
        conn.execute("DELETE FROM learning WHERE lrnid = ?", (lrnid,))


# =============================================================================
# Daemon State Operations
# =============================================================================


def set_daemon_state(
    pid: int | None = None,
    dsstatus: str = "running",
    dsphase: str | None = None,
    dsproject_id: int | None = None,
) -> None:
    """Set the daemon state."""
    with get_db() as conn:
        conn.execute(
            """UPDATE daemon_state
               SET pid = ?, dsstatus = ?, dsphase = ?, dsproject_id = ?,
                   started_at = ?, updated_at = ?
               WHERE id = 1""",
            (pid, dsstatus, dsphase, dsproject_id, datetime.now(), datetime.now()),
        )


def get_daemon_state() -> dict | None:
    """Get the current daemon state."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM daemon_state WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else None


def clear_daemon_state() -> None:
    """Clear the daemon state (mark as stopped)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE daemon_state SET pid = NULL, dsstatus = 'stopped', dsphase = NULL, dsproject_id = NULL, updated_at = ? WHERE id = 1",
            (datetime.now(),),
        )


def update_daemon_heartbeat() -> None:
    """Update the daemon heartbeat timestamp."""
    with get_db() as conn:
        conn.execute(
            "UPDATE daemon_state SET updated_at = ? WHERE id = 1",
            (datetime.now(),),
        )


# =============================================================================
# Document Operations
# =============================================================================


def create_document(
    prjid: int,
    docname: str,
    docpath: str,
    cmpid: int | None = None,
    doctype: str | None = None,
    docphase: str | None = None,
    docdesc: str | None = None,
) -> int:
    """Create a document record."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO document (prjid, cmpid, docname, docpath, doctype, docphase, docdesc) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (prjid, cmpid, docname, docpath, doctype, docphase, docdesc),
        )
        return cursor.lastrowid


def get_document(docid: int) -> dict | None:
    """Get a document by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM document WHERE docid = ?", (docid,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_documents(prjid: int | None = None, cmpid: int | None = None) -> list[dict]:
    """List documents with optional filters."""
    with get_db() as conn:
        if cmpid is not None:
            cursor = conn.execute(
                "SELECT * FROM document WHERE cmpid = ? ORDER BY doctouchts DESC",
                (cmpid,),
            )
        elif prjid is not None:
            cursor = conn.execute(
                "SELECT * FROM document WHERE prjid = ? ORDER BY doctouchts DESC",
                (prjid,),
            )
        else:
            cursor = conn.execute("SELECT * FROM document ORDER BY doctouchts DESC")
        return [dict(row) for row in cursor.fetchall()]


def delete_document(docid: int) -> None:
    """Delete a document record."""
    with get_db() as conn:
        conn.execute("DELETE FROM document WHERE docid = ?", (docid,))


# =============================================================================
# Test Result Operations
# =============================================================================


def create_test_result(
    tsid: int,
    trpassed: int = 0,
    troutput: str | None = None,
    trerror: str | None = None,
    agtid: int | None = None,
) -> int:
    """Create a test result."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO test_result (tsid, agtid, trpassed, troutput, trerror) VALUES (?, ?, ?, ?, ?)",
            (tsid, agtid, trpassed, troutput, trerror),
        )
        return cursor.lastrowid


def list_test_results(tsid: int | None = None, prjid: int | None = None) -> list[dict]:
    """List test results."""
    with get_db() as conn:
        if tsid is not None:
            cursor = conn.execute(
                "SELECT * FROM test_result WHERE tsid = ? ORDER BY trtouchts DESC",
                (tsid,),
            )
        elif prjid is not None:
            cursor = conn.execute(
                """SELECT tr.* FROM test_result tr
                   JOIN test_spec ts ON tr.tsid = ts.tsid
                   JOIN component c ON ts.cmpid = c.cmpid
                   WHERE c.prjid = ? ORDER BY tr.trtouchts DESC""",
                (prjid,),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM test_result ORDER BY trtouchts DESC"
            )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Stats / Dashboard Queries
# =============================================================================


def get_project_stats(prjid: int) -> dict:
    """Get statistics for a project."""
    with get_db() as conn:
        cmp_cursor = conn.execute(
            "SELECT cmpstatus, COUNT(*) AS cnt FROM component WHERE prjid = ? GROUP BY cmpstatus",
            (prjid,),
        )
        component_counts = {row["cmpstatus"]: row["cnt"] for row in cmp_cursor.fetchall()}

        agt_cursor = conn.execute(
            "SELECT agtstatus, COUNT(*) AS cnt FROM agent WHERE prjid = ? GROUP BY agtstatus",
            (prjid,),
        )
        agent_counts = {row["agtstatus"]: row["cnt"] for row in agt_cursor.fetchall()}

        total_components = sum(component_counts.values())
        total_agents = sum(agent_counts.values())

        return {
            "total_components": total_components,
            "component_counts": component_counts,
            "total_agents": total_agents,
            "agent_counts": agent_counts,
        }


# =============================================================================
# Agent Output Operations
# =============================================================================


def append_agent_output(agtid: int, aocontent: str) -> int:
    """Append output content for an agent."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO agent_output (agtid, aocontent) VALUES (?, ?)",
            (agtid, aocontent),
        )
        return cursor.lastrowid


def get_agent_output(agtid: int, since_aoid: int | None = None) -> list[dict]:
    """Get agent output, optionally since a given output ID."""
    with get_db() as conn:
        if since_aoid is not None:
            cursor = conn.execute(
                "SELECT * FROM agent_output WHERE agtid = ? AND aoid > ? ORDER BY aoid ASC",
                (agtid, since_aoid),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM agent_output WHERE agtid = ? ORDER BY aoid ASC",
                (agtid,),
            )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Agent Settings Operations (Hierarchical)
# =============================================================================


def set_agent_setting(scope: str, scope_key: str, setting_key: str, setting_value: str) -> int:
    """Set an agent setting (upsert)."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO agent_settings (scope, scope_key, setting_key, setting_value)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(scope, scope_key, setting_key) DO UPDATE SET
               setting_value = excluded.setting_value, astouchts = CURRENT_TIMESTAMP""",
            (scope, scope_key, setting_key, setting_value),
        )
        return cursor.lastrowid


def get_agent_setting(scope: str, scope_key: str, setting_key: str) -> str | None:
    """Get a single agent setting value."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT setting_value FROM agent_settings WHERE scope = ? AND scope_key = ? AND setting_key = ?",
            (scope, scope_key, setting_key),
        )
        row = cursor.fetchone()
        return row["setting_value"] if row else None


def list_agent_settings(scope: str | None = None, scope_key: str | None = None) -> list[dict]:
    """List agent settings with optional filters."""
    conditions = []
    params: list = []

    if scope is not None:
        conditions.append("scope = ?")
        params.append(scope)
    if scope_key is not None:
        conditions.append("scope_key = ?")
        params.append(scope_key)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"SELECT * FROM agent_settings WHERE {where} ORDER BY scope, scope_key, setting_key",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_agent_setting(scope: str, scope_key: str, setting_key: str) -> None:
    """Delete an agent setting."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM agent_settings WHERE scope = ? AND scope_key = ? AND setting_key = ?",
            (scope, scope_key, setting_key),
        )


# =============================================================================
# Agent Context Operations
# =============================================================================


def save_agent_context(
    agtid: int,
    accontext: str,
    cmpid: int | None = None,
    btid: int | None = None,
    acstatus: str = "active",
) -> int:
    """Save an agent's work context."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO agent_context (agtid, cmpid, btid, accontext, acstatus) VALUES (?, ?, ?, ?, ?)",
            (agtid, cmpid, btid, accontext, acstatus),
        )
        return cursor.lastrowid


def get_latest_agent_context(agtid: int) -> dict | None:
    """Get the most recent context for an agent."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM agent_context WHERE agtid = ? ORDER BY actouchts DESC LIMIT 1",
            (agtid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_agent_contexts(agtid: int | None = None, btid: int | None = None) -> list[dict]:
    """List agent contexts with optional filters."""
    conditions = []
    params: list = []

    if agtid is not None:
        conditions.append("agtid = ?")
        params.append(agtid)
    if btid is not None:
        conditions.append("btid = ?")
        params.append(btid)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"SELECT * FROM agent_context WHERE {where} ORDER BY actouchts DESC",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Agent Count by Role
# =============================================================================


# =============================================================================
# Tech Stack Catalog Operations
# =============================================================================


def search_techstack_catalog(query: str = "", limit: int = 50) -> list[dict]:
    """Search the tech stack catalog by key, owner, or description."""
    with get_db() as conn:
        if query:
            pattern = f"%{query}%"
            cursor = conn.execute(
                """SELECT * FROM techstack_catalog
                   WHERE tscat_key LIKE ? OR tscat_owner LIKE ? OR tscat_desc LIKE ?
                   ORDER BY tscat_key
                   LIMIT ?""",
                (pattern, pattern, pattern, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM techstack_catalog ORDER BY tscat_key LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]


def add_techstack_entry(
    tscat_key: str,
    tscat_owner: str | None = None,
    tscat_desc: str | None = None,
    tscat_notes: str | None = None,
) -> int:
    """Add a custom entry to the tech stack catalog."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO techstack_catalog (tscat_key, tscat_owner, tscat_desc, tscat_notes, tscat_custom)
               VALUES (?, ?, ?, ?, 1)""",
            (tscat_key, tscat_owner, tscat_desc, tscat_notes),
        )
        return cursor.lastrowid


def delete_techstack_entry(tscat_id: int) -> None:
    """Delete a tech stack catalog entry (custom entries only)."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM techstack_catalog WHERE tscat_id = ? AND tscat_custom = 1",
            (tscat_id,),
        )


def count_agents_by_role(prjid: int | None = None) -> dict[str, int]:
    """Count active agents grouped by role.

    Returns:
        Dict mapping role name to count of active agents.
    """
    with get_db() as conn:
        if prjid is not None:
            cursor = conn.execute(
                """SELECT agtrole, COUNT(*) AS cnt FROM agent
                   WHERE prjid = ? AND agtstatus NOT IN ('terminated')
                   GROUP BY agtrole""",
                (prjid,),
            )
        else:
            cursor = conn.execute(
                """SELECT agtrole, COUNT(*) AS cnt FROM agent
                   WHERE agtstatus NOT IN ('terminated')
                   GROUP BY agtrole"""
            )
        return {row["agtrole"]: row["cnt"] for row in cursor.fetchall()}


# =============================================================================
# Stats / Dashboard Queries
# =============================================================================


def get_dashboard_stats() -> dict:
    """Get global dashboard statistics."""
    with get_db() as conn:
        prj_count = conn.execute("SELECT COUNT(*) FROM project").fetchone()[0]

        agt_cursor = conn.execute(
            "SELECT agtstatus, COUNT(*) AS cnt FROM agent GROUP BY agtstatus"
        )
        agent_counts = {row["agtstatus"]: row["cnt"] for row in agt_cursor.fetchall()}

        phase_cursor = conn.execute(
            "SELECT prjphase, COUNT(*) AS cnt FROM project GROUP BY prjphase"
        )
        phase_counts = {row["prjphase"]: row["cnt"] for row in phase_cursor.fetchall()}

        pending_msgs = conn.execute(
            "SELECT COUNT(*) FROM agent_message WHERE msgstatus = 'queued'"
        ).fetchone()[0]

        return {
            "projects": prj_count,
            "active_agents": agent_counts.get("working", 0),
            "idle_agents": agent_counts.get("idle", 0),
            "error_agents": agent_counts.get("error", 0),
            "agent_counts": agent_counts,
            "phase_counts": phase_counts,
            "pending_messages": pending_msgs,
        }


# =============================================================================
# Task Queue Operations
# =============================================================================


def enqueue_task(
    prjid: int,
    tqagent_type: str,
    tqinstructions: str,
    tqauthor: str = "system",
    tqrequest_type: str = "task",
    tqworkflow_step: int | None = None,
    tqprevious_work: str | None = None,
    tqcmpid: int | None = None,
    tqpriority: int = 5,
    tqmax_retries: int = 3,
    tqstart_time: str | None = None,
    tqexpire_time: str | None = None,
    tqagent_name: str | None = None,
    tqcollab_chain_id: int | None = None,
    tqcollab_turn: int | None = None,
) -> int:
    """Insert a new task into the task queue.

    Returns:
        The new task queue ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO task_queue
               (prjid, tqauthor, tqagent_type, tqinstructions, tqrequest_type,
                tqworkflow_step, tqprevious_work, tqcmpid, tqpriority,
                tqmax_retries, tqstart_time, tqexpire_time, tqagent_name,
                tqcollab_chain_id, tqcollab_turn)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prjid, tqauthor, tqagent_type, tqinstructions, tqrequest_type,
                tqworkflow_step, tqprevious_work, tqcmpid, tqpriority,
                tqmax_retries, tqstart_time, tqexpire_time, tqagent_name,
                tqcollab_chain_id, tqcollab_turn,
            ),
        )
        return cursor.lastrowid


def get_task(tqid: int) -> dict | None:
    """Get a task by ID with joined agent info."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT tq.*, a.agtname, a.agtrole, a.agtstatus AS agent_status
               FROM task_queue tq
               LEFT JOIN agent a ON tq.tqagent_id = a.agtid
               WHERE tq.tqid = ?""",
            (tqid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_tasks(
    prjid: int | None = None,
    status: str | None = None,
    agent_type: str | None = None,
    workflow_step: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """List tasks with optional filters."""
    conditions = []
    params: list = []

    if prjid is not None:
        conditions.append("tq.prjid = ?")
        params.append(prjid)
    if status is not None:
        conditions.append("tq.tqstatus = ?")
        params.append(status)
    if agent_type is not None:
        conditions.append("tq.tqagent_type = ?")
        params.append(agent_type)
    if workflow_step is not None:
        conditions.append("tq.tqworkflow_step = ?")
        params.append(workflow_step)

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT tq.*, a.agtname, a.agtrole
                FROM task_queue tq
                LEFT JOIN agent a ON tq.tqagent_id = a.agtid
                WHERE {where}
                ORDER BY tq.tqpriority ASC, tq.tqsent_time ASC
                LIMIT ?""",
            params + [limit],
        )
        return [dict(row) for row in cursor.fetchall()]


def update_task(tqid: int, **kwargs) -> None:
    """Generic update for a task queue entry."""
    allowed = {
        "tqstatus", "tqagent_id", "tqpickup_time", "tqcomplete_time",
        "tqduration_secs", "tqresult", "tqerror", "tqretry_count",
        "tqprevious_work", "tqinstructions", "tqpriority",
        "tqagent_name", "tqstart_time", "tqexpire_time",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return

    fields["tqtouchts"] = datetime.now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tqid]

    with get_db() as conn:
        conn.execute(f"UPDATE task_queue SET {set_clause} WHERE tqid = ?", values)


def find_ready_tasks(prjid: int) -> list[dict]:
    """Find tasks that are ready to be assigned.

    Ready = status=pending, start_time<=now or NULL, not expired.
    Ordered by priority ASC, sent_time ASC.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT tq.*, a.agtname
               FROM task_queue tq
               LEFT JOIN agent a ON tq.tqagent_id = a.agtid
               WHERE tq.prjid = ?
                 AND tq.tqstatus = 'pending'
                 AND (tq.tqstart_time IS NULL OR tq.tqstart_time <= CURRENT_TIMESTAMP)
                 AND (tq.tqexpire_time IS NULL OR tq.tqexpire_time > CURRENT_TIMESTAMP)
               ORDER BY tq.tqpriority ASC, tq.tqsent_time ASC""",
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def assign_task(tqid: int, agtid: int) -> None:
    """Assign a task to an agent."""
    with get_db() as conn:
        conn.execute(
            """UPDATE task_queue
               SET tqstatus = 'assigned', tqagent_id = ?, tqpickup_time = ?,
                   tqtouchts = ?
               WHERE tqid = ?""",
            (agtid, datetime.now(), datetime.now(), tqid),
        )


def complete_task(tqid: int, result: str | None = None) -> None:
    """Mark a task as complete and calculate duration."""
    now = datetime.now()
    with get_db() as conn:
        # Get pickup time for duration calc
        row = conn.execute(
            "SELECT tqpickup_time FROM task_queue WHERE tqid = ?", (tqid,)
        ).fetchone()
        duration = None
        if row and row["tqpickup_time"]:
            try:
                pickup = row["tqpickup_time"]
                if isinstance(pickup, str):
                    pickup = datetime.fromisoformat(pickup)
                duration = (now - pickup).total_seconds()
            except (ValueError, TypeError):
                pass

        conn.execute(
            """UPDATE task_queue
               SET tqstatus = 'complete', tqresult = ?, tqcomplete_time = ?,
                   tqduration_secs = ?, tqtouchts = ?
               WHERE tqid = ?""",
            (result, now, duration, now, tqid),
        )


def fail_task(tqid: int, error: str) -> None:
    """Increment retry count and set error. Status stays in_progress if retries remain."""
    now = datetime.now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT tqretry_count, tqmax_retries FROM task_queue WHERE tqid = ?",
            (tqid,),
        ).fetchone()
        if not row:
            return

        new_count = (row["tqretry_count"] or 0) + 1
        max_retries = row["tqmax_retries"] or 3

        if new_count >= max_retries:
            conn.execute(
                """UPDATE task_queue
                   SET tqstatus = 'failed', tqerror = ?, tqretry_count = ?,
                       tqcomplete_time = ?, tqtouchts = ?
                   WHERE tqid = ?""",
                (error, new_count, now, now, tqid),
            )
        else:
            # Reset to pending for retry
            conn.execute(
                """UPDATE task_queue
                   SET tqstatus = 'pending', tqerror = ?, tqretry_count = ?,
                       tqagent_id = NULL, tqpickup_time = NULL, tqtouchts = ?
                   WHERE tqid = ?""",
                (error, new_count, now, tqid),
            )


def expire_overdue_tasks(prjid: int) -> int:
    """Mark expired tasks. Returns count of expired tasks."""
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE task_queue
               SET tqstatus = 'expired', tqtouchts = ?
               WHERE prjid = ?
                 AND tqstatus IN ('pending', 'assigned')
                 AND tqexpire_time IS NOT NULL
                 AND tqexpire_time <= CURRENT_TIMESTAMP""",
            (datetime.now(), prjid),
        )
        return cursor.rowcount


def get_active_task_for_agent(agtid: int) -> dict | None:
    """Get the current in_progress task for an agent."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT * FROM task_queue
               WHERE tqagent_id = ? AND tqstatus IN ('assigned', 'in_progress')
               ORDER BY tqtouchts DESC LIMIT 1""",
            (agtid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_task_queue_stats(prjid: int) -> dict:
    """Get task queue statistics for a project."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT tqstatus, COUNT(*) AS cnt
               FROM task_queue
               WHERE prjid = ?
               GROUP BY tqstatus""",
            (prjid,),
        )
        counts = {row["tqstatus"]: row["cnt"] for row in cursor.fetchall()}
        total = sum(counts.values())

        # Average duration of complete tasks
        dur_row = conn.execute(
            """SELECT AVG(tqduration_secs) AS avg_dur
               FROM task_queue
               WHERE prjid = ? AND tqstatus = 'complete' AND tqduration_secs IS NOT NULL""",
            (prjid,),
        ).fetchone()
        avg_duration = dur_row["avg_dur"] if dur_row and dur_row["avg_dur"] else 0.0

        return {
            "total": total,
            "counts": counts,
            "avg_duration_secs": round(avg_duration, 1),
            "pending": counts.get("pending", 0),
            "in_progress": counts.get("in_progress", 0) + counts.get("assigned", 0),
            "complete": counts.get("complete", 0),
            "failed": counts.get("failed", 0),
            "expired": counts.get("expired", 0),
            "cancelled": counts.get("cancelled", 0),
        }


def dedup_tasks(prjid: int, workflow_step: int, keep_tqid: int) -> int:
    """Cancel duplicate tasks for a workflow step, keeping the specified one."""
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE task_queue
               SET tqstatus = 'cancelled', tqtouchts = ?
               WHERE prjid = ? AND tqworkflow_step = ? AND tqid != ?
                 AND tqstatus IN ('pending', 'assigned')""",
            (datetime.now(), prjid, workflow_step, keep_tqid),
        )
        return cursor.rowcount


def build_task_library(prjid: int) -> str:
    """Build a markdown library summary from project documents."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT docname, docdesc, doctype, docphase
               FROM document WHERE prjid = ?
               ORDER BY docphase, docname""",
            (prjid,),
        )
        docs = cursor.fetchall()

    if not docs:
        return "# Project Library\nNo documents available yet.\n"

    lines = ["# Project Library\n"]
    for doc in docs:
        name = doc["docname"]
        desc = doc["docdesc"] or ""
        dtype = doc["doctype"] or ""
        phase = doc["docphase"] or ""
        lines.append(f"- **{name}** ({dtype}, {phase}): {desc}")

    return "\n".join(lines) + "\n"


def build_swarm_summary(prjid: int) -> str:
    """Build a markdown summary of active agents."""
    agents = list_agents(prjid=prjid)
    active = [a for a in agents if a.get("agtstatus") not in ("terminated",)]

    if not active:
        return "# Active Agents\nNo agents currently active.\n"

    lines = ["# Active Agents\n"]
    for a in active:
        name = a.get("agtname", f"Agent #{a['agtid']}")
        role = a.get("agtrole", "unknown")
        status = a.get("agtstatus", "unknown")
        cmp = a.get("cmpname", "")
        cmp_str = f" → {cmp}" if cmp else ""
        lines.append(f"- **{name}** ({role}) [{status}]{cmp_str}")

    return "\n".join(lines) + "\n"


def calculate_project_progress(prjid: int) -> dict:
    """Calculate overall project progress from the task queue.

    Returns:
        Dict with percent, current_step, by_phase breakdown, and task counts.
    """
    with get_db() as conn:
        # Count tasks by status
        cursor = conn.execute(
            """SELECT tqstatus, COUNT(*) AS cnt
               FROM task_queue WHERE prjid = ?
               GROUP BY tqstatus""",
            (prjid,),
        )
        counts = {row["tqstatus"]: row["cnt"] for row in cursor.fetchall()}
        total = sum(counts.values())
        complete = counts.get("complete", 0)

        # Current step = max completed workflow step
        step_row = conn.execute(
            """SELECT MAX(tqworkflow_step) AS max_step
               FROM task_queue
               WHERE prjid = ? AND tqstatus = 'complete' AND tqworkflow_step IS NOT NULL""",
            (prjid,),
        ).fetchone()
        current_step = step_row["max_step"] if step_row and step_row["max_step"] else 0

        from ..constants import WORKFLOW_TOTAL_STEPS
        percent = int((complete / total) * 100) if total > 0 else 0

    return {
        "percent": percent,
        "current_step": current_step,
        "total_steps": WORKFLOW_TOTAL_STEPS,
        "tasks": {
            "total": total,
            "complete": complete,
            "failed": counts.get("failed", 0),
            "in_progress": counts.get("in_progress", 0) + counts.get("assigned", 0),
            "pending": counts.get("pending", 0),
        },
    }


def save_scoped_context(
    agtid: int,
    scope_level: str,
    scope_id: int,
    tqid: int | None,
    context: str,
    cmpid: int | None = None,
) -> int:
    """Save agent context with scope information."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO agent_context
               (agtid, cmpid, accontext, acstatus, acscopelevel, acscopeid, actqid)
               VALUES (?, ?, ?, 'active', ?, ?, ?)""",
            (agtid, cmpid, context, scope_level, scope_id, tqid),
        )
        return cursor.lastrowid


def get_context_for_scope(scope_level: str, scope_id: int) -> dict | None:
    """Get the most recent context for a given scope."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT * FROM agent_context
               WHERE acscopelevel = ? AND acscopeid = ? AND acstatus = 'active'
               ORDER BY actouchts DESC LIMIT 1""",
            (scope_level, scope_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
