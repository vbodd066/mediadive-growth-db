"""
Reusable read-only query helpers against the MediaDive SQLite DB.

Every function returns plain Python data structures (lists of dicts)
so callers don't need to know about sqlite3 cursors.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from src.config import DB_PATH

log = logging.getLogger(__name__)


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Context-managed SQLite connection with row-factory enabled."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _rows(sql: str, params: tuple = (), db_path: Path | None = None) -> list[dict[str, Any]]:
    """Run a query and return results as a list of dicts."""
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ── Media ────────────────────────────────────────────────────

def get_all_media(db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows("SELECT * FROM media", db_path=db_path)


def get_media_ids(db_path: Path | None = None) -> list[str]:
    with connect(db_path) as conn:
        return [r[0] for r in conn.execute("SELECT media_id FROM media").fetchall()]


def get_media_ids_without_detail(db_path: Path | None = None) -> list[str]:
    """Return media IDs that haven't had their /medium/:id detail fetched yet."""
    with connect(db_path) as conn:
        return [
            r[0]
            for r in conn.execute(
                "SELECT media_id FROM media WHERE fetched_detail = 0"
            ).fetchall()
        ]


# ── Ingredients ──────────────────────────────────────────────

def get_all_ingredients(db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows("SELECT * FROM ingredients", db_path=db_path)


def get_ingredient_index(db_path: Path | None = None) -> dict[int, str]:
    """Return {ingredient_id: ingredient_name} mapping."""
    with connect(db_path) as conn:
        rows = conn.execute("SELECT ingredient_id, ingredient_name FROM ingredients").fetchall()
    return {r[0]: r[1] for r in rows}


# ── Compositions ─────────────────────────────────────────────

def get_media_composition(media_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return the flattened molecular composition for a single medium."""
    return _rows(
        "SELECT * FROM media_composition WHERE media_id = ?",
        (media_id,),
        db_path,
    )


def get_full_composition_matrix(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return every (media_id, ingredient_id, g_per_l) triple."""
    return _rows(
        "SELECT media_id, ingredient_id, g_per_l FROM media_composition",
        db_path=db_path,
    )


# ── Solutions ────────────────────────────────────────────────

def get_solutions_for_medium(media_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows(
        """
        SELECT s.* FROM solutions s
        JOIN media_solutions ms ON s.solution_id = ms.solution_id
        WHERE ms.media_id = ?
        """,
        (media_id,),
        db_path,
    )


def get_solution_recipe(solution_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows(
        "SELECT * FROM solution_recipe WHERE solution_id = ? ORDER BY recipe_order",
        (solution_id,),
        db_path,
    )


# ── Strains ──────────────────────────────────────────────────

def get_all_strains(db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows("SELECT * FROM strains", db_path=db_path)


# ── Growth observations ──────────────────────────────────────

def get_all_growth(db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows("SELECT * FROM strain_growth", db_path=db_path)


def get_growth_for_strain(strain_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows(
        "SELECT * FROM strain_growth WHERE strain_id = ?",
        (strain_id,),
        db_path,
    )


# ── Ingest tracking ─────────────────────────────────────────

def mark_task_done(task: str, db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ingest_log (task, status, updated_at)
            VALUES (?, 'done', datetime('now'))
            ON CONFLICT(task) DO UPDATE SET status='done', updated_at=datetime('now')
            """,
            (task,),
        )
        conn.commit()


def mark_task_error(task: str, error: str, db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ingest_log (task, status, updated_at, error_message)
            VALUES (?, 'error', datetime('now'), ?)
            ON CONFLICT(task) DO UPDATE SET status='error', updated_at=datetime('now'), error_message=?
            """,
            (task, error, error),
        )
        conn.commit()


def is_task_done(task: str, db_path: Path | None = None) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status FROM ingest_log WHERE task = ?", (task,)
        ).fetchone()
    return row is not None and row[0] == "done"


# ── Summary stats ────────────────────────────────────────────

def table_counts(db_path: Path | None = None) -> dict[str, int]:
    """Quick row counts for all tables."""
    tables = [
        "media", "ingredients", "solutions", "media_solutions",
        "solution_recipe", "solution_steps", "media_composition",
        "strains", "strain_growth",
    ]
    counts: dict[str, int] = {}
    with connect(db_path) as conn:
        for t in tables:
            counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608
    return counts
