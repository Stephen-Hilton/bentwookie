"""SQLite database connection management for BentWookie."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

# Default database path (relative to project root)
_db_path: Path = Path("data/bentwookie.db")


def get_db_path() -> Path:
    """Get the current database path.

    Returns:
        Path to the SQLite database file.
    """
    return _db_path


def set_db_path(path: str | Path) -> None:
    """Set the database path.

    Args:
        path: New path for the database file.
    """
    global _db_path
    _db_path = Path(path)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection context manager.

    Yields:
        SQLite connection with Row factory enabled.

    Example:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM project")
            rows = cursor.fetchall()
    """
    # Ensure parent directory exists
    _db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        _db_path,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database with the schema.

    Creates all tables if they don't exist, and runs migrations for existing databases.
    """
    schema_path = Path(__file__).parent / "schema_v2.sql"

    with get_db() as conn:
        conn.executescript(schema_path.read_text())

    # Run migrations for existing databases
    _run_migrations()


def _run_migrations() -> None:
    """Run database migrations for existing databases.

    Adds new columns and tables if they don't exist.
    """
    # Column migrations
    column_migrations = [
        ("request", "reqplanpath", "TEXT"),
        ("request", "reqtestplanpath", "TEXT"),
        ("request", "reqtestretries", "INTEGER DEFAULT 0"),
        ("request", "reqerror", "TEXT"),
        ("request", "reqcommitenabled", "INTEGER DEFAULT 1"),
        ("request", "reqcommitbranch", "TEXT"),
        ("project", "prjprompt", "TEXT"),
        ("project", "prjclaudemd", "TEXT"),
        ("project", "prjmodel", "TEXT"),
        ("project", "prjcommitenabled", "INTEGER DEFAULT NULL"),
        ("project", "prjcommitbranchmode", "TEXT"),
        ("project", "prjcommitbranchname", "TEXT"),
        # V2 migrations
        ("project", "prjmaxagents", "INTEGER DEFAULT 5"),
        ("project", "prjcodedir", "TEXT"),
        ("project", "prjpriority", "INTEGER DEFAULT 5"),
        # Task queue migrations
        ("document", "docdesc", "TEXT"),
        ("agent_context", "acscopelevel", "TEXT"),
        ("agent_context", "acscopeid", "INTEGER"),
        ("agent_context", "actqid", "INTEGER"),
    ]

    # Table migrations (new tables that might not exist in older DBs)
    table_migrations: list[str] = [
        """
        CREATE TABLE IF NOT EXISTS techstack_catalog (
            tscat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tscat_key TEXT NOT NULL UNIQUE,
            tscat_owner TEXT,
            tscat_desc TEXT,
            tscat_notes TEXT,
            tscat_custom INTEGER DEFAULT 0,
            tscat_touchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS infra_option (
            optid INTEGER PRIMARY KEY AUTOINCREMENT,
            opttype TEXT NOT NULL,
            optname TEXT NOT NULL,
            optprovider TEXT DEFAULT 'local',
            optsortorder INTEGER DEFAULT 0,
            UNIQUE(opttype, optname)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS daemon_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            pid INTEGER,
            loop_name TEXT,
            started_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS request_doc (
            docid INTEGER PRIMARY KEY AUTOINCREMENT,
            reqid INTEGER NOT NULL,
            doc_name TEXT NOT NULL,
            doc_path TEXT NOT NULL,
            doc_phase TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reqid) REFERENCES request(reqid) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_output (
            aoid INTEGER PRIMARY KEY AUTOINCREMENT,
            agtid INTEGER NOT NULL,
            aocontent TEXT NOT NULL,
            aotouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_settings (
            asid INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL CHECK (scope IN ('agent_type', 'agent')),
            scope_key TEXT NOT NULL,
            setting_key TEXT NOT NULL,
            setting_value TEXT NOT NULL,
            astouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scope, scope_key, setting_key)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_context (
            acid INTEGER PRIMARY KEY AUTOINCREMENT,
            agtid INTEGER NOT NULL,
            cmpid INTEGER,
            btid INTEGER,
            accontext TEXT NOT NULL,
            acstatus TEXT DEFAULT 'active',
            acscopelevel TEXT,
            acscopeid INTEGER,
            actqid INTEGER,
            actouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE CASCADE,
            FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE SET NULL,
            FOREIGN KEY (btid) REFERENCES build_task(btid) ON DELETE SET NULL,
            FOREIGN KEY (actqid) REFERENCES task_queue(tqid) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS task_queue (
            tqid INTEGER PRIMARY KEY AUTOINCREMENT,
            prjid INTEGER NOT NULL,
            tqauthor TEXT DEFAULT 'system',
            tqstatus TEXT DEFAULT 'pending' CHECK (tqstatus IN ('pending', 'assigned', 'in_progress', 'complete', 'failed', 'expired', 'cancelled')),
            tqsent_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tqstart_time TIMESTAMP,
            tqexpire_time TIMESTAMP,
            tqagent_type TEXT NOT NULL,
            tqagent_name TEXT,
            tqagent_id INTEGER,
            tqrequest_type TEXT DEFAULT 'task' CHECK (tqrequest_type IN ('task', 'collab')),
            tqworkflow_step INTEGER,
            tqprevious_work TEXT,
            tqinstructions TEXT NOT NULL,
            tqcmpid INTEGER,
            tqpriority INTEGER DEFAULT 5,
            tqretry_count INTEGER DEFAULT 0,
            tqmax_retries INTEGER DEFAULT 3,
            tqpickup_time TIMESTAMP,
            tqcomplete_time TIMESTAMP,
            tqduration_secs REAL,
            tqresult TEXT,
            tqerror TEXT,
            tqcollab_chain_id INTEGER,
            tqcollab_turn INTEGER,
            tqtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
            FOREIGN KEY (tqagent_id) REFERENCES agent(agtid) ON DELETE SET NULL,
            FOREIGN KEY (tqcmpid) REFERENCES component(cmpid) ON DELETE SET NULL
        )
        """,
    ]

    # Index migrations (indexes that might not exist in older DBs)
    index_migrations: list[str] = [
        "CREATE INDEX IF NOT EXISTS idx_techstack_key ON techstack_catalog(tscat_key)",
        "CREATE INDEX IF NOT EXISTS idx_request_doc_reqid ON request_doc(reqid)",
        "CREATE INDEX IF NOT EXISTS idx_agent_output_agtid ON agent_output(agtid)",
        "CREATE INDEX IF NOT EXISTS idx_agent_output_ts ON agent_output(aotouchts)",
        "CREATE INDEX IF NOT EXISTS idx_agent_settings_scope ON agent_settings(scope, scope_key)",
        "CREATE INDEX IF NOT EXISTS idx_agent_context_agtid ON agent_context(agtid)",
        "CREATE INDEX IF NOT EXISTS idx_agent_context_btid ON agent_context(btid)",
        # Task queue indexes
        "CREATE INDEX IF NOT EXISTS idx_tq_prjid ON task_queue(prjid)",
        "CREATE INDEX IF NOT EXISTS idx_tq_status ON task_queue(tqstatus)",
        "CREATE INDEX IF NOT EXISTS idx_tq_agent_type ON task_queue(tqagent_type)",
        "CREATE INDEX IF NOT EXISTS idx_tq_agent_id ON task_queue(tqagent_id)",
        "CREATE INDEX IF NOT EXISTS idx_tq_start_time ON task_queue(tqstart_time)",
        "CREATE INDEX IF NOT EXISTS idx_tq_priority ON task_queue(tqpriority)",
        "CREATE INDEX IF NOT EXISTS idx_tq_workflow_step ON task_queue(tqworkflow_step)",
    ]

    # Singleton row initialization
    singleton_inits = [
        "INSERT OR IGNORE INTO daemon_state (id) VALUES (1)",
    ]

    with get_db() as conn:
        # Run table migrations first
        for table_sql in table_migrations:
            try:
                conn.execute(table_sql)
            except sqlite3.OperationalError:
                pass  # Table might already exist

        # Run index migrations
        for index_sql in index_migrations:
            try:
                conn.execute(index_sql)
            except sqlite3.OperationalError:
                pass  # Index might already exist

        # Initialize singleton rows
        for init_sql in singleton_inits:
            try:
                conn.execute(init_sql)
            except sqlite3.OperationalError:
                pass  # Row might already exist

        # Migrate agent table CHECK constraint for new roles
        # Check the schema SQL to see if new roles are already in the CHECK constraint
        schema_cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='agent'"
        )
        schema_row = schema_cursor.fetchone()
        agent_sql = schema_row[0] if schema_row else ""

        if "testing_agent" not in agent_sql and "agent" in agent_sql:
            # Old CHECK constraint — recreate the table with new roles
            try:
                conn.executescript("""
                    PRAGMA foreign_keys = OFF;
                    CREATE TABLE IF NOT EXISTS agent_new (
                        agtid INTEGER PRIMARY KEY AUTOINCREMENT,
                        prjid INTEGER NOT NULL,
                        agtrole TEXT NOT NULL CHECK (agtrole IN ('business_owner', 'enterprise_architect', 'business_architect', 'service_engineer', 'coding_agent', 'testing_agent')),
                        agtstatus TEXT DEFAULT 'idle',
                        agtname TEXT,
                        agtmodel TEXT,
                        agtshellpid INTEGER,
                        agtcmpid INTEGER,
                        agterror TEXT,
                        agtstarted TIMESTAMP,
                        agttouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
                        FOREIGN KEY (agtcmpid) REFERENCES component(cmpid) ON DELETE SET NULL
                    );
                    INSERT INTO agent_new SELECT * FROM agent;
                    DROP TABLE agent;
                    ALTER TABLE agent_new RENAME TO agent;
                    PRAGMA foreign_keys = ON;
                """)
            except sqlite3.OperationalError:
                pass

        # Run column migrations
        for table, column, coltype in column_migrations:
            # Check if column exists
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]

            if column not in columns:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
                except sqlite3.OperationalError:
                    pass  # Column might already exist in some edge cases

    # Seed techstack catalog from file if table is empty
    _seed_techstack_catalog()


def _seed_techstack_catalog() -> None:
    """Seed the techstack_catalog table from the JSON catalog file if empty."""
    import json

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM techstack_catalog").fetchone()[0]
        if count > 0:
            return  # Already seeded

        catalog_path = Path(__file__).parent.parent / "templates" / "techstack_catalog.json"
        if not catalog_path.exists():
            return

        entries = json.loads(catalog_path.read_text(encoding="utf-8"))
        for entry in entries:
            key = entry.get("key", "").strip()
            if not key:
                continue
            owner = entry.get("owner", "").strip() or None
            desc = entry.get("desc", "").strip() or None
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO techstack_catalog
                       (tscat_key, tscat_owner, tscat_desc, tscat_custom)
                       VALUES (?, ?, ?, 0)""",
                    (key, owner, desc),
                )
            except sqlite3.Error:
                pass  # Skip duplicates or errors


def reset_db() -> None:
    """Reset the database by removing and reinitializing it.

    Warning: This will delete all data!
    """
    if _db_path.exists():
        _db_path.unlink()
    init_db()
