"""
Ingest media records from the MediaDive REST API.

Endpoints used:
    GET /media?limit=N&offset=M   → paginated media list
    GET /medium/:id               → full recipe (solutions, steps)
    GET /medium-composition/:id   → molecular composition (g/L, mmol/L)
    GET /medium-strains/:id       → strain associations + growth flags
"""

from __future__ import annotations

import logging

from src.api.client import get_detail, paginate
from src.db.queries import connect, is_task_done, mark_task_done, mark_task_error

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Step 1: Media list  (/media)
# ═══════════════════════════════════════════════════════════════

def fetch_media_list(db_path=None) -> int:
    """Fetch every medium from the paginated /media endpoint. Returns count."""
    task = "media_list"
    if is_task_done(task, db_path):
        log.info("Skipping %s (already done)", task)
        with connect(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]

    total = 0
    with connect(db_path) as conn:
        for page in paginate("/media", limit=200):
            for m in page:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO media
                        (media_id, media_name, is_complex, source, link, min_pH, max_pH,
                         reference, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(m["id"]),
                        m["name"],
                        1 if m.get("complex_medium") else 0,
                        m.get("source"),
                        m.get("link"),
                        m.get("min_pH"),
                        m.get("max_pH"),
                        m.get("reference"),
                        m.get("description"),
                    ),
                )
            conn.commit()
            total += len(page)

    mark_task_done(task, db_path)
    log.info("Fetched %d media records.", total)
    return total


# ═══════════════════════════════════════════════════════════════
#  Step 2: Medium detail — recipes + solutions  (/medium/:id)
# ═══════════════════════════════════════════════════════════════

def fetch_medium_detail(media_id: str, db_path=None) -> None:
    """
    Fetch the full recipe for one medium and persist solutions + recipe lines.
    """
    task = f"medium_detail:{media_id}"
    if is_task_done(task, db_path):
        return

    try:
        data = get_detail(f"/medium/{media_id}")
    except Exception as e:
        log.warning("Failed to fetch detail for medium %s: %s", media_id, e)
        mark_task_error(task, str(e), db_path)
        return

    solutions = data.get("solutions") or []

    with connect(db_path) as conn:
        for sol in solutions:
            sol_id = sol["id"]
            conn.execute(
                """
                INSERT OR IGNORE INTO solutions (solution_id, solution_name, volume_ml)
                VALUES (?, ?, ?)
                """,
                (sol_id, sol.get("name", ""), sol.get("volume")),
            )
            conn.execute(
                "INSERT OR IGNORE INTO media_solutions (media_id, solution_id) VALUES (?, ?)",
                (media_id, sol_id),
            )

            # Recipe lines
            for item in sol.get("recipe") or []:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO solution_recipe
                        (solution_id, recipe_order, ingredient_id, ingredient_name,
                         amount, unit, g_per_l, mmol_per_l, is_optional,
                         condition, sub_solution_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sol_id,
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

            # Preparation steps
            for i, step in enumerate(sol.get("steps") or []):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO solution_steps (solution_id, step_order, step_text)
                    VALUES (?, ?, ?)
                    """,
                    (sol_id, i + 1, step.get("step", "")),
                )

        conn.execute(
            "UPDATE media SET fetched_detail = 1 WHERE media_id = ?",
            (media_id,),
        )
        conn.commit()

    mark_task_done(task, db_path)


def fetch_all_medium_details(db_path=None) -> int:
    """Fetch detail for every medium that hasn't been fetched yet."""
    from src.db.queries import get_media_ids_without_detail

    ids = get_media_ids_without_detail(db_path)
    log.info("Fetching detail for %d media...", len(ids))

    for i, mid in enumerate(ids):
        if (i + 1) % 50 == 0 or i == 0:
            log.info("  [%d/%d] medium %s", i + 1, len(ids), mid)
        fetch_medium_detail(mid, db_path)

    log.info("Medium detail fetch complete.")
    return len(ids)


# ═══════════════════════════════════════════════════════════════
#  Step 3: Molecular composition  (/medium-composition/:id)
# ═══════════════════════════════════════════════════════════════

def fetch_medium_composition(media_id: str, db_path=None) -> int:
    """Fetch and store the flattened molecular composition for one medium."""
    task = f"composition:{media_id}"
    if is_task_done(task, db_path):
        return 0

    try:
        data = get_detail(f"/medium-composition/{media_id}")
    except Exception as e:
        log.warning("Failed to fetch composition for medium %s: %s", media_id, e)
        mark_task_error(task, str(e), db_path)
        return 0

    # data is a list of ingredient dicts
    items = data if isinstance(data, list) else []
    with connect(db_path) as conn:
        for item in items:
            conn.execute(
                """
                INSERT OR IGNORE INTO media_composition
                    (media_id, ingredient_id, ingredient_name, g_per_l, mmol_per_l, is_optional)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    item["id"],
                    item.get("name", ""),
                    item.get("g_l"),
                    item.get("mmol_l"),
                    1 if item.get("optional") else 0,
                ),
            )
        conn.commit()

    mark_task_done(task, db_path)
    return len(items)


def fetch_all_compositions(db_path=None) -> int:
    """Fetch composition for every medium."""
    from src.db.queries import get_media_ids

    ids = get_media_ids(db_path)
    log.info("Fetching compositions for %d media...", len(ids))
    total = 0

    for i, mid in enumerate(ids):
        if (i + 1) % 100 == 0 or i == 0:
            log.info("  [%d/%d] composition for %s", i + 1, len(ids), mid)
        total += fetch_medium_composition(mid, db_path)

    log.info("Composition fetch complete: %d rows.", total)
    return total


# ═══════════════════════════════════════════════════════════════
#  Step 4: Strain associations  (/medium-strains/:id)
# ═══════════════════════════════════════════════════════════════

def fetch_medium_strains(media_id: str, db_path=None) -> int:
    """Fetch all strain–growth associations for one medium."""
    task = f"medium_strains:{media_id}"
    if is_task_done(task, db_path):
        return 0

    try:
        data = get_detail(f"/medium-strains/{media_id}")
    except Exception as e:
        log.warning("Failed to fetch strains for medium %s: %s", media_id, e)
        mark_task_error(task, str(e), db_path)
        return 0

    items = data if isinstance(data, list) else []
    with connect(db_path) as conn:
        for s in items:
            # Upsert strain
            conn.execute(
                """
                INSERT INTO strains (strain_id, species, ccno, bacdive_id, domain)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(strain_id) DO UPDATE SET
                    species   = COALESCE(excluded.species, strains.species),
                    ccno      = COALESCE(excluded.ccno, strains.ccno),
                    bacdive_id= COALESCE(excluded.bacdive_id, strains.bacdive_id),
                    domain    = COALESCE(excluded.domain, strains.domain)
                """,
                (
                    s["id"],
                    s.get("species"),
                    s.get("ccno"),
                    s.get("bacdive_id"),
                    s.get("domain"),
                ),
            )
            # Growth observation
            conn.execute(
                """
                INSERT OR IGNORE INTO strain_growth
                    (strain_id, media_id, growth)
                VALUES (?, ?, ?)
                """,
                (s["id"], media_id, 1 if s.get("growth") else 0),
            )
        conn.commit()

    mark_task_done(task, db_path)
    return len(items)


def fetch_all_medium_strains(db_path=None) -> int:
    """Fetch strain associations for every medium."""
    from src.db.queries import get_media_ids

    ids = get_media_ids(db_path)
    log.info("Fetching strain associations for %d media...", len(ids))
    total = 0

    for i, mid in enumerate(ids):
        if (i + 1) % 100 == 0 or i == 0:
            log.info("  [%d/%d] strains for %s", i + 1, len(ids), mid)
        total += fetch_medium_strains(mid, db_path)

    log.info("Strain-growth fetch complete: %d associations.", total)
    return total


if __name__ == "__main__":
    fetch_media_list()
    fetch_all_medium_details()
    fetch_all_compositions()
    fetch_all_medium_strains()
