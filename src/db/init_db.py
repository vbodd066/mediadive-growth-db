"""
Initialize (or migrate) the SQLite database from the schema file.

Uses CREATE TABLE IF NOT EXISTS — safe to re-run without data loss.
"""

import logging
import sqlite3
from pathlib import Path

from src.config import DB_PATH

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init_db(db_path: Path | None = None) -> Path:
    """Create the database and apply the schema.  Returns the resolved path."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    existed = path.exists()
    log.info("%s database at %s", "Migrating" if existed else "Creating", path)

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.close()
    log.info("Database ready.")
    return path


if __name__ == "__main__":
    init_db()
