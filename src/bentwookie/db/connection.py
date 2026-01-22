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
    schema_path = Path(__file__).parent / "schema.sql"

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
    ]

    # Table migrations (new tables that might not exist in older DBs)
    table_migrations = [
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
    ]

    with get_db() as conn:
        # Run table migrations first
        for table_sql in table_migrations:
            try:
                conn.execute(table_sql)
            except sqlite3.OperationalError:
                pass  # Table might already exist

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


def reset_db() -> None:
    """Reset the database by removing and reinitializing it.

    Warning: This will delete all data!
    """
    if _db_path.exists():
        _db_path.unlink()
    init_db()
