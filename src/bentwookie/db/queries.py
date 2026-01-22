"""Database CRUD operations for BentWookie."""

from datetime import datetime

from .connection import get_db

# =============================================================================
# Project Operations
# =============================================================================


def create_project(
    prjname: str,
    prjversion: str = "poc",
    prjpriority: int = 5,
    prjphase: str = "dev",
    prjdesc: str | None = None,
    prjcodedir: str | None = None,
) -> int:
    """Create a new project.

    Args:
        prjname: Unique project name.
        prjversion: Version string (poc, mvp, v1, etc.).
        prjpriority: Priority level (1-10).
        prjphase: Project phase (dev, qa, uat, prod).
        prjdesc: Optional project description.
        prjcodedir: Optional code directory path.

    Returns:
        The new project ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO project (prjname, prjversion, prjpriority, prjphase, prjdesc, prjcodedir)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (prjname, prjversion, prjpriority, prjphase, prjdesc, prjcodedir),
        )
        return cursor.lastrowid  # type: ignore


def get_project(prjid: int) -> dict | None:
    """Get a project by ID.

    Args:
        prjid: Project ID.

    Returns:
        Project dict or None if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM project WHERE prjid = ?",
            (prjid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_project_by_name(prjname: str) -> dict | None:
    """Get a project by name.

    Args:
        prjname: Project name.

    Returns:
        Project dict or None if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM project WHERE prjname = ?",
            (prjname,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_projects(
    phase: str | None = None,
    order_by: str = "prjpriority",
) -> list[dict]:
    """List all projects.

    Args:
        phase: Optional filter by phase.
        order_by: Column to order by (default: prjpriority).

    Returns:
        List of project dicts.
    """
    with get_db() as conn:
        if phase:
            cursor = conn.execute(
                f"SELECT * FROM project WHERE prjphase = ? ORDER BY {order_by}",
                (phase,),
            )
        else:
            cursor = conn.execute(f"SELECT * FROM project ORDER BY {order_by}")
        return [dict(row) for row in cursor.fetchall()]


def update_project(
    prjid: int,
    prjname: str | None = None,
    prjversion: str | None = None,
    prjpriority: int | None = None,
    prjphase: str | None = None,
    prjdesc: str | None = None,
    prjcodedir: str | None = None,
) -> bool:
    """Update a project.

    Args:
        prjid: Project ID to update.
        prjname: New name (optional).
        prjversion: New version (optional).
        prjpriority: New priority (optional).
        prjphase: New phase (optional).
        prjdesc: New description (optional).
        prjcodedir: New code directory (optional).

    Returns:
        True if project was updated, False if not found.
    """
    updates = []
    values = []

    if prjname is not None:
        updates.append("prjname = ?")
        values.append(prjname)
    if prjversion is not None:
        updates.append("prjversion = ?")
        values.append(prjversion)
    if prjpriority is not None:
        updates.append("prjpriority = ?")
        values.append(prjpriority)
    if prjphase is not None:
        updates.append("prjphase = ?")
        values.append(prjphase)
    if prjdesc is not None:
        updates.append("prjdesc = ?")
        values.append(prjdesc)
    if prjcodedir is not None:
        updates.append("prjcodedir = ?")
        values.append(prjcodedir)

    if not updates:
        return False

    updates.append("prjtouchts = ?")
    values.append(datetime.now())
    values.append(prjid)

    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE project SET {', '.join(updates)} WHERE prjid = ?",
            values,
        )
        return cursor.rowcount > 0


def delete_project(prjid: int) -> bool:
    """Delete a project and all related records.

    Args:
        prjid: Project ID to delete.

    Returns:
        True if project was deleted, False if not found.
    """
    with get_db() as conn:
        # Delete related records first (cascade)
        conn.execute("DELETE FROM learning WHERE prjid = ?", (prjid,))
        conn.execute("DELETE FROM infrastructure WHERE prjid = ?", (prjid,))
        conn.execute("DELETE FROM request WHERE prjid = ?", (prjid,))
        cursor = conn.execute("DELETE FROM project WHERE prjid = ?", (prjid,))
        return cursor.rowcount > 0


# =============================================================================
# Request Operations
# =============================================================================


def create_request(
    prjid: int,
    reqname: str,
    reqprompt: str,
    reqtype: str = "new_feature",
    reqstatus: str = "tbd",
    reqphase: str = "plan",
    reqpriority: int = 5,
    reqcodedir: str | None = None,
) -> int:
    """Create a new request.

    Args:
        prjid: Parent project ID.
        reqname: Request name.
        reqprompt: The prompt/description for this request.
        reqtype: Type (new_feature, bug_fix, enhancement).
        reqstatus: Status (tbd, wip, done, err, tmout).
        reqphase: Phase (plan, dev, test, deploy, verify, document, complete).
        reqpriority: Priority level (1-10).
        reqcodedir: Optional sandbox directory for code changes.

    Returns:
        The new request ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO request
            (prjid, reqname, reqprompt, reqtype, reqstatus, reqphase, reqpriority, reqcodedir)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (prjid, reqname, reqprompt, reqtype, reqstatus, reqphase, reqpriority, reqcodedir),
        )
        return cursor.lastrowid  # type: ignore


def get_request(reqid: int) -> dict | None:
    """Get a request by ID.

    Args:
        reqid: Request ID.

    Returns:
        Request dict or None if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM request WHERE reqid = ?",
            (reqid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_next_request() -> dict | None:
    """Get the next request to process.

    Returns the highest priority request with status 'tbd',
    ordered by priority (ascending = higher priority) and timestamp.

    Returns:
        Request dict or None if no requests are pending.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT r.*, p.prjname, p.prjphase as project_phase, p.prjcodedir
            FROM request r
            JOIN project p ON r.prjid = p.prjid
            WHERE r.reqstatus = 'tbd'
            ORDER BY r.reqpriority ASC, r.reqtouchts ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_requests(
    prjid: int | None = None,
    status: str | None = None,
    phase: str | None = None,
    order_by: str = "reqpriority",
) -> list[dict]:
    """List requests with optional filters.

    Args:
        prjid: Optional filter by project ID.
        status: Optional filter by status.
        phase: Optional filter by phase.
        order_by: Column to order by (default: reqpriority).

    Returns:
        List of request dicts.
    """
    conditions = []
    values = []

    if prjid is not None:
        conditions.append("r.prjid = ?")
        values.append(prjid)
    if status is not None:
        conditions.append("r.reqstatus = ?")
        values.append(status)
    if phase is not None:
        conditions.append("r.reqphase = ?")
        values.append(phase)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        cursor = conn.execute(
            f"""
            SELECT r.*, p.prjname
            FROM request r
            JOIN project p ON r.prjid = p.prjid
            {where_clause}
            ORDER BY {order_by}
            """,
            values,
        )
        return [dict(row) for row in cursor.fetchall()]


def update_request_status(reqid: int, status: str) -> bool:
    """Update a request's status.

    Args:
        reqid: Request ID.
        status: New status (tbd, wip, done, err, tmout).

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqstatus = ?, reqtouchts = ? WHERE reqid = ?",
            (status, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def update_request_error(reqid: int, error: str | None) -> bool:
    """Update a request's error message.

    Args:
        reqid: Request ID.
        error: Error message, or None to clear.

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqerror = ?, reqtouchts = ? WHERE reqid = ?",
            (error, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def update_request_phase(reqid: int, phase: str) -> bool:
    """Update a request's phase.

    Args:
        reqid: Request ID.
        phase: New phase (plan, dev, test, deploy, verify, document, complete).

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqphase = ?, reqtouchts = ? WHERE reqid = ?",
            (phase, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def update_request_docpath(reqid: int, docpath: str) -> bool:
    """Update a request's documentation path.

    Args:
        reqid: Request ID.
        docpath: Path to documentation file.

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqdocpath = ?, reqtouchts = ? WHERE reqid = ?",
            (docpath, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def update_request_codedir(reqid: int, codedir: str) -> bool:
    """Update a request's code directory.

    Args:
        reqid: Request ID.
        codedir: Path to code sandbox directory.

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqcodedir = ?, reqtouchts = ? WHERE reqid = ?",
            (codedir, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def update_request_planpath(reqid: int, planpath: str) -> bool:
    """Update a request's plan document path.

    Args:
        reqid: Request ID.
        planpath: Path to PLAN document.

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqplanpath = ?, reqtouchts = ? WHERE reqid = ?",
            (planpath, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def update_request_testplanpath(reqid: int, testplanpath: str) -> bool:
    """Update a request's test plan document path.

    Args:
        reqid: Request ID.
        testplanpath: Path to TESTPLAN document.

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqtestplanpath = ?, reqtouchts = ? WHERE reqid = ?",
            (testplanpath, datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def increment_request_test_retries(reqid: int) -> int:
    """Increment a request's test retry counter.

    Args:
        reqid: Request ID.

    Returns:
        New retry count.
    """
    with get_db() as conn:
        conn.execute(
            "UPDATE request SET reqtestretries = reqtestretries + 1, reqtouchts = ? WHERE reqid = ?",
            (datetime.now(), reqid),
        )
        cursor = conn.execute("SELECT reqtestretries FROM request WHERE reqid = ?", (reqid,))
        row = cursor.fetchone()
        return row[0] if row else 0


def reset_request_test_retries(reqid: int) -> bool:
    """Reset a request's test retry counter to 0.

    Args:
        reqid: Request ID.

    Returns:
        True if request was updated, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE request SET reqtestretries = 0, reqtouchts = ? WHERE reqid = ?",
            (datetime.now(), reqid),
        )
        return cursor.rowcount > 0


def delete_request(reqid: int) -> bool:
    """Delete a request.

    Args:
        reqid: Request ID to delete.

    Returns:
        True if request was deleted, False if not found.
    """
    with get_db() as conn:
        # Delete related request infrastructure first
        conn.execute("DELETE FROM request_infrastructure WHERE reqid = ?", (reqid,))
        cursor = conn.execute("DELETE FROM request WHERE reqid = ?", (reqid,))
        return cursor.rowcount > 0


def update_request(
    reqid: int,
    reqname: str | None = None,
    reqprompt: str | None = None,
    reqtype: str | None = None,
    reqpriority: int | None = None,
    reqcodedir: str | None = None,
) -> bool:
    """Update a request (full field updates).

    Note: prjid is not updatable - requests are locked to their project.

    Args:
        reqid: Request ID to update.
        reqname: New name (optional).
        reqprompt: New prompt (optional).
        reqtype: New type (optional).
        reqpriority: New priority (optional).
        reqcodedir: New code directory (optional).

    Returns:
        True if request was updated, False if not found.
    """
    updates = []
    values = []

    if reqname is not None:
        updates.append("reqname = ?")
        values.append(reqname)
    if reqprompt is not None:
        updates.append("reqprompt = ?")
        values.append(reqprompt)
    if reqtype is not None:
        updates.append("reqtype = ?")
        values.append(reqtype)
    if reqpriority is not None:
        updates.append("reqpriority = ?")
        values.append(reqpriority)
    if reqcodedir is not None:
        updates.append("reqcodedir = ?")
        values.append(reqcodedir)

    if not updates:
        return False

    updates.append("reqtouchts = ?")
    values.append(datetime.now())
    values.append(reqid)

    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE request SET {', '.join(updates)} WHERE reqid = ?",
            values,
        )
        return cursor.rowcount > 0


# =============================================================================
# Infrastructure Operations
# =============================================================================


def add_infrastructure(
    prjid: int,
    inftype: str,
    infprovider: str = "local",
    infval: str | None = None,
    infnote: str | None = None,
) -> int:
    """Add infrastructure configuration to a project.

    Args:
        prjid: Project ID.
        inftype: Infrastructure type (compute, storage, queue, access, ui).
        infprovider: Provider (local, container, aws, gcp, azure).
        infval: Provider-specific value.
        infnote: Optional note.

    Returns:
        The new infrastructure ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO infrastructure (prjid, inftype, infprovider, infval, infnote)
            VALUES (?, ?, ?, ?, ?)
            """,
            (prjid, inftype, infprovider, infval, infnote),
        )
        return cursor.lastrowid  # type: ignore


def get_project_infrastructure(prjid: int) -> list[dict]:
    """Get all infrastructure for a project.

    Args:
        prjid: Project ID.

    Returns:
        List of infrastructure dicts.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM infrastructure WHERE prjid = ?",
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_infrastructure(infid: int) -> bool:
    """Delete an infrastructure record.

    Args:
        infid: Infrastructure ID to delete.

    Returns:
        True if record was deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM infrastructure WHERE infid = ?", (infid,))
        return cursor.rowcount > 0


def update_infrastructure(
    infid: int,
    infprovider: str | None = None,
    infval: str | None = None,
    infnote: str | None = None,
) -> bool:
    """Update an infrastructure record.

    Args:
        infid: Infrastructure ID to update.
        infprovider: New provider (optional).
        infval: New value (optional).
        infnote: New note (optional).

    Returns:
        True if record was updated, False if not found.
    """
    updates = []
    values = []

    if infprovider is not None:
        updates.append("infprovider = ?")
        values.append(infprovider)
    if infval is not None:
        updates.append("infval = ?")
        values.append(infval)
    if infnote is not None:
        updates.append("infnote = ?")
        values.append(infnote)

    if not updates:
        return False

    values.append(infid)

    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE infrastructure SET {', '.join(updates)} WHERE infid = ?",
            values,
        )
        return cursor.rowcount > 0


# =============================================================================
# Request Infrastructure Operations
# =============================================================================


def add_request_infrastructure(
    reqid: int,
    inftype: str,
    infprovider: str = "local",
    infval: str | None = None,
    infnote: str | None = None,
) -> int:
    """Add infrastructure configuration override to a request.

    Args:
        reqid: Request ID.
        inftype: Infrastructure type (compute, storage, queue, access, ui).
        infprovider: Provider (local, container, aws, gcp, azure).
        infval: Provider-specific value.
        infnote: Optional note.

    Returns:
        The new request infrastructure ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO request_infrastructure (reqid, inftype, infprovider, infval, infnote)
            VALUES (?, ?, ?, ?, ?)
            """,
            (reqid, inftype, infprovider, infval, infnote),
        )
        return cursor.lastrowid  # type: ignore


def get_request_infrastructure(reqid: int) -> list[dict]:
    """Get all infrastructure overrides for a request.

    Args:
        reqid: Request ID.

    Returns:
        List of request infrastructure dicts.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM request_infrastructure WHERE reqid = ?",
            (reqid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_request_infrastructure(rinfid: int) -> bool:
    """Delete a request infrastructure record.

    Args:
        rinfid: Request infrastructure ID to delete.

    Returns:
        True if record was deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM request_infrastructure WHERE rinfid = ?", (rinfid,)
        )
        return cursor.rowcount > 0


def update_request_infrastructure(
    rinfid: int,
    infprovider: str | None = None,
    infval: str | None = None,
    infnote: str | None = None,
) -> bool:
    """Update a request infrastructure record.

    Args:
        rinfid: Request infrastructure ID to update.
        infprovider: New provider (optional).
        infval: New value (optional).
        infnote: New note (optional).

    Returns:
        True if record was updated, False if not found.
    """
    updates = []
    values = []

    if infprovider is not None:
        updates.append("infprovider = ?")
        values.append(infprovider)
    if infval is not None:
        updates.append("infval = ?")
        values.append(infval)
    if infnote is not None:
        updates.append("infnote = ?")
        values.append(infnote)

    if not updates:
        return False

    values.append(rinfid)

    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE request_infrastructure SET {', '.join(updates)} WHERE rinfid = ?",
            values,
        )
        return cursor.rowcount > 0


def get_effective_infrastructure(reqid: int) -> dict[str, dict]:
    """Get merged infrastructure (project + request overrides).

    Returns infrastructure configuration for a request, merging project-level
    settings with request-level overrides. Request settings take precedence.

    Args:
        reqid: Request ID.

    Returns:
        Dict mapping inftype -> infrastructure dict.
    """
    req = get_request(reqid)
    if not req:
        return {}

    project_infra = get_project_infrastructure(req["prjid"])
    request_infra = get_request_infrastructure(reqid)

    # Start with project infrastructure, keyed by inftype
    effective: dict[str, dict] = {}
    for i in project_infra:
        effective[i["inftype"]] = {
            "inftype": i["inftype"],
            "infprovider": i["infprovider"],
            "infval": i["infval"],
            "infnote": i["infnote"],
            "source": "project",
        }

    # Override with request infrastructure
    for ri in request_infra:
        effective[ri["inftype"]] = {
            "inftype": ri["inftype"],
            "infprovider": ri["infprovider"],
            "infval": ri["infval"],
            "infnote": ri["infnote"],
            "source": "request",
        }

    return effective


# =============================================================================
# Learning Operations
# =============================================================================


def add_learning(prjid: int, lrndesc: str) -> int:
    """Add a learning to a project.

    Args:
        prjid: Project ID. Use -1 for global learnings that apply to all projects.
        lrndesc: Learning description (max 255 chars recommended).

    Returns:
        The new learning ID.
    """
    with get_db() as conn:
        # For global learnings (prjid=-1), temporarily disable foreign key checks
        if prjid == -1:
            conn.execute("PRAGMA foreign_keys = OFF")

        cursor = conn.execute(
            "INSERT INTO learning (prjid, lrndesc) VALUES (?, ?)",
            (prjid, lrndesc),
        )
        lastrowid = cursor.lastrowid

        # Re-enable foreign keys if we disabled them
        if prjid == -1:
            conn.execute("PRAGMA foreign_keys = ON")

        return lastrowid  # type: ignore


def get_project_learnings(prjid: int) -> list[dict]:
    """Get all learnings for a project.

    Args:
        prjid: Project ID.

    Returns:
        List of learning dicts, ordered by timestamp descending.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM learning WHERE prjid = ? ORDER BY lrntouchts DESC",
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_learning(lrnid: int) -> bool:
    """Delete a learning record.

    Args:
        lrnid: Learning ID to delete.

    Returns:
        True if record was deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM learning WHERE lrnid = ?", (lrnid,))
        return cursor.rowcount > 0


def get_learning(lrnid: int) -> dict | None:
    """Get a learning by ID.

    Args:
        lrnid: Learning ID.

    Returns:
        Learning dict or None if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT l.*, p.prjname FROM learning l LEFT JOIN project p ON l.prjid = p.prjid WHERE l.lrnid = ?",
            (lrnid,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_learning(lrnid: int, lrndesc: str) -> bool:
    """Update a learning's description.

    Args:
        lrnid: Learning ID to update.
        lrndesc: New description.

    Returns:
        True if learning was updated, False if not found.
    """
    from datetime import datetime

    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE learning SET lrndesc = ?, lrntouchts = ? WHERE lrnid = ?",
            (lrndesc, datetime.now(), lrnid),
        )
        return cursor.rowcount > 0


def list_all_learnings(prjid: int | None = None) -> list[dict]:
    """List all learnings, optionally filtered by project.

    Args:
        prjid: Optional project ID filter. Use -1 for global only.

    Returns:
        List of learning dicts with project name.
    """
    with get_db() as conn:
        if prjid is not None:
            cursor = conn.execute(
                """
                SELECT l.*, COALESCE(p.prjname, 'Global') as prjname
                FROM learning l
                LEFT JOIN project p ON l.prjid = p.prjid
                WHERE l.prjid = ?
                ORDER BY l.lrntouchts DESC
                """,
                (prjid,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT l.*, COALESCE(p.prjname, 'Global') as prjname
                FROM learning l
                LEFT JOIN project p ON l.prjid = p.prjid
                ORDER BY l.prjid, l.lrntouchts DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def get_learnings_with_global(prjid: int) -> list[dict]:
    """Get learnings for a project including global learnings (prjid=-1).

    This is used when building prompts for the LLM - it merges
    project-specific learnings with global learnings that apply
    to all projects.

    Args:
        prjid: Project ID.

    Returns:
        List of learning dicts, ordered by timestamp descending.
        Includes both project-specific (prjid) and global (prjid=-1) learnings.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT l.*, COALESCE(p.prjname, 'Global') as prjname,
                   CASE WHEN l.prjid = -1 THEN 'global' ELSE 'project' END as scope
            FROM learning l
            LEFT JOIN project p ON l.prjid = p.prjid
            WHERE l.prjid = ? OR l.prjid = -1
            ORDER BY l.lrntouchts DESC
            """,
            (prjid,),
        )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Infrastructure Option Operations (Wizard Selectable Options)
# =============================================================================


def add_infra_option(
    opttype: str,
    optname: str,
    optprovider: str = "local",
    optsortorder: int = 0,
) -> int:
    """Add an infrastructure option for the wizard.

    Args:
        opttype: Option type (compute, storage, queue, access).
        optname: Display name (e.g., "AWS Lambda", "Local").
        optprovider: Provider hint (local, aws, gcp, azure, container).
        optsortorder: Sort order (lower = first).

    Returns:
        The new option ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO infra_option (opttype, optname, optprovider, optsortorder)
            VALUES (?, ?, ?, ?)
            """,
            (opttype.lower(), optname, optprovider.lower(), optsortorder),
        )
        return cursor.lastrowid  # type: ignore


def get_infra_options(opttype: str | None = None) -> list[dict]:
    """Get infrastructure options, optionally filtered by type.

    Args:
        opttype: Optional filter by type (compute, storage, queue, access).

    Returns:
        List of option dicts, ordered by type and sort order.
    """
    with get_db() as conn:
        if opttype:
            cursor = conn.execute(
                """
                SELECT * FROM infra_option
                WHERE opttype = ?
                ORDER BY optsortorder, optname
                """,
                (opttype.lower(),),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM infra_option
                ORDER BY opttype, optsortorder, optname
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def get_infra_options_by_type(opttype: str) -> list[str]:
    """Get infrastructure option names for a specific type.

    This is a convenience function for the wizard that returns
    just the option names as a list.

    Args:
        opttype: Option type (compute, storage, queue, access).

    Returns:
        List of option names, ordered by sort order.
    """
    options = get_infra_options(opttype)
    return [opt["optname"] for opt in options]


def delete_infra_option(opttype: str, optname: str) -> bool:
    """Delete an infrastructure option.

    Args:
        opttype: Option type.
        optname: Option name.

    Returns:
        True if option was deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM infra_option WHERE opttype = ? AND optname = ?",
            (opttype.lower(), optname),
        )
        return cursor.rowcount > 0


def delete_infra_option_by_id(optid: int) -> bool:
    """Delete an infrastructure option by ID.

    Args:
        optid: Option ID.

    Returns:
        True if option was deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM infra_option WHERE optid = ?",
            (optid,),
        )
        return cursor.rowcount > 0


def seed_default_infra_options() -> int:
    """Seed the default infrastructure options if none exist.

    This populates the infra_option table with the default options
    from constants.py if the table is empty.

    Returns:
        Number of options added.
    """
    from ..constants import (
        ACCESS_OPTIONS,
        COMPUTE_OPTIONS,
        QUEUE_OPTIONS,
        STORAGE_OPTIONS,
    )

    # Check if any options exist
    existing = get_infra_options()
    if existing:
        return 0

    count = 0
    defaults = {
        "compute": COMPUTE_OPTIONS,
        "storage": STORAGE_OPTIONS,
        "queue": QUEUE_OPTIONS,
        "access": ACCESS_OPTIONS,
    }

    for opttype, options in defaults.items():
        for i, optname in enumerate(options):
            # Determine provider from option name
            provider = "local"
            name_lower = optname.lower()
            if "aws" in name_lower:
                provider = "aws"
            elif "gcp" in name_lower or "google" in name_lower:
                provider = "gcp"
            elif "azure" in name_lower:
                provider = "azure"
            elif "container" in name_lower or "docker" in name_lower:
                provider = "container"

            add_infra_option(
                opttype=opttype,
                optname=optname,
                optprovider=provider,
                optsortorder=i,
            )
            count += 1

    return count
