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
) -> int:
    """Create a new project.

    Args:
        prjname: Unique project name.
        prjversion: Version string (poc, mvp, v1, etc.).
        prjpriority: Priority level (1-10).
        prjphase: Project phase (dev, qa, uat, prod).
        prjdesc: Optional project description.

    Returns:
        The new project ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO project (prjname, prjversion, prjpriority, prjphase, prjdesc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (prjname, prjversion, prjpriority, prjphase, prjdesc),
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
) -> bool:
    """Update a project.

    Args:
        prjid: Project ID to update.
        prjname: New name (optional).
        prjversion: New version (optional).
        prjpriority: New priority (optional).
        prjphase: New phase (optional).
        prjdesc: New description (optional).

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
            SELECT r.*, p.prjname, p.prjphase as project_phase
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


def delete_request(reqid: int) -> bool:
    """Delete a request.

    Args:
        reqid: Request ID to delete.

    Returns:
        True if request was deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM request WHERE reqid = ?", (reqid,))
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


# =============================================================================
# Learning Operations
# =============================================================================


def add_learning(prjid: int, lrndesc: str) -> int:
    """Add a learning to a project.

    Args:
        prjid: Project ID.
        lrndesc: Learning description (max 255 chars recommended).

    Returns:
        The new learning ID.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO learning (prjid, lrndesc) VALUES (?, ?)",
            (prjid, lrndesc),
        )
        return cursor.lastrowid  # type: ignore


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
