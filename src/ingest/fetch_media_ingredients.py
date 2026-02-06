"""
Ingest solution data from the MediaDive REST API.

Endpoints used:
    GET /solutions?limit=N&offset=M   → paginated solutions list (non-main)
    GET /solutions?all=1&limit=N&offset=M → all solutions including main
    GET /solution/:id                  → full recipe + steps for one solution
"""

from __future__ import annotations

import logging

from src.api.client import get_detail, paginate
from src.db.queries import connect, is_task_done, mark_task_done, mark_task_error

log = logging.getLogger(__name__)


def fetch_solution_list(db_path=None) -> int:
    """Fetch all solutions (including main) from the paginated endpoint."""
    task = "solution_list"
    if is_task_done(task, db_path):
        log.info("Skipping %s (already done)", task)
        with connect(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]

    total = 0
    with connect(db_path) as conn:
        for page in paginate("/solutions", limit=200, extra_params={"all": 1}):
            for sol in page:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO solutions (solution_id, solution_name, volume_ml)
                    VALUES (?, ?, ?)
                    """,
                    (sol["id"], sol.get("name", ""), sol.get("volume")),
                )
            conn.commit()
            total += len(page)

    mark_task_done(task, db_path)
    log.info("Fetched %d solutions.", total)
    return total


def fetch_solution_detail(solution_id: int, db_path=None) -> int:
    """Fetch recipe lines + preparation steps for one solution."""
    task = f"solution_detail:{solution_id}"
    if is_task_done(task, db_path):
        return 0

    try:
        data = get_detail(f"/solution/{solution_id}")
    except Exception as e:
        log.warning("Failed to fetch solution %d: %s", solution_id, e)
        mark_task_error(task, str(e), db_path)
        return 0

    recipe = data.get("recipe") or []
    steps = data.get("steps") or []

    with connect(db_path) as conn:
        for item in recipe:
            conn.execute(
                """
                INSERT OR IGNORE INTO solution_recipe
                    (solution_id, recipe_order, ingredient_id, ingredient_name,
                     amount, unit, g_per_l, mmol_per_l, is_optional,
                     condition, sub_solution_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    solution_id,
                    item.get("recipe_order", 0),
                    item.get("compound_id"),
                    item.get("compound", ""),
                    item.get("amount"),
                    item.get("unit"),
                    item.get("g_l"),
                    item.get("mmol_l"),
                    1 if item.get("optional") else 0,
                    item.get("condition"),
                    item.get("solution_id"),  # sub-solution reference
                ),
            )

        for i, step in enumerate(steps):
            conn.execute(
                """
                INSERT OR IGNORE INTO solution_steps (solution_id, step_order, step_text)
                VALUES (?, ?, ?)
                """,
                (solution_id, i + 1, step.get("step", "")),
            )

        conn.commit()

    mark_task_done(task, db_path)
    return len(recipe)


def fetch_all_solution_details(db_path=None) -> int:
    """Fetch detail for every solution in the DB."""
    with connect(db_path) as conn:
        ids = [r[0] for r in conn.execute("SELECT solution_id FROM solutions").fetchall()]

    log.info("Fetching recipe details for %d solutions...", len(ids))
    total = 0

    for i, sid in enumerate(ids):
        if (i + 1) % 200 == 0 or i == 0:
            log.info("  [%d/%d] solution %d", i + 1, len(ids), sid)
        total += fetch_solution_detail(sid, db_path)

    log.info("Solution detail fetch complete: %d recipe lines.", total)
    return total


if __name__ == "__main__":
    fetch_solution_list()
    fetch_all_solution_details()
