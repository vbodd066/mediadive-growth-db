import sqlite3
from pathlib import Path

DB_PATH = Path("data/mediadive.db")
SCHEMA_PATH = Path("src/db/schema.sql")

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.close()

if __name__ == "__main__":
    init_db()
