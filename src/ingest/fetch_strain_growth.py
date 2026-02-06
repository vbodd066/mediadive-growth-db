"""
Ingest strain detail data from the MediaDive REST API.

Endpoints used:
    GET /strain/id/:id  → strain detail + per-medium growth observations

Growth observations are primarily harvested via /medium-strains/:id
(see fetch_media.py). This module provides a complementary path
to fetch growth from the strain side + enrich strain records with
extra fields (growth_rate, growth_quality, modification).
"""

from __future__ import annotations

import logging

from src.api.client import get_detail
from src.db.queries import connect, is_task_done, mark_task_done, mark_task_error

log = logging.getLogger(__name__)


def fetch_strain_detail(strain_id: int, db_path=None) -> int:
    """
    Fetch detail for one strain from /strain/id/:id.

    Upserts the strain record and inserts any growth observations
    not already present (including growth_rate / growth_quality).
    Returns count of growth rows processed.
    """
    task = f"strain_detail:{strain_id}"
    if is_task_done(task, db_path):
        return 0

    try:
        data = get_detail(f"/strain/id/{strain_id}")
    except Exception as e:
        log.debug("Failed to fetch strain %d: %s", strain_id, e)
        mark_task_error(task, str(e), db_path)
        return 0

    with connect(db_path) as conn:
        # Upsert strain metadata
        conn.execute(
            """
            INSERT INTO strains (strain_id, species, ccno)
            VALUES (?, ?, ?)
            ON CONFLICT(strain_id) DO UPDATE SET
                species = COALESCE(excluded.species, strains.species),
                ccno    = COALESCE(excluded.ccno, strains.ccno)
            """,
            (data["id"], data.get("species"), data.get("ccno")),
        )

        # Growth observations from this strain's perspective
        media_list = data.get("media") or []
        for m in media_list:
            conn.execute(
                """
                INSERT INTO strain_growth
                    (strain_id, media_id, growth, growth_rate, growth_quality, modification)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(strain_id, media_id) DO UPDATE SET
                    growth_rate    = COALESCE(excluded.growth_rate, strain_growth.growth_rate),
                    growth_quality = COALESCE(excluded.growth_quality, strain_growth.growth_quality),
                    modification   = COALESCE(excluded.modification, strain_growth.modification)
                """,
                (
                    strain_id,
                    str(m["medium_id"]),
                    1 if m.get("growth") else 0,
                    m.get("growth_rate"),
                    m.get("growth_quality"),
                    m.get("modification"),
                ),
            )
        conn.commit()

    mark_task_done(task, db_path)
    return len(media_list)


def fetch_all_strain_details(db_path=None) -> int:
    """Fetch detail for every strain already discovered in the DB."""
    with connect(db_path) as conn:
        ids = [r[0] for r in conn.execute("SELECT strain_id FROM strains").fetchall()]

    log.info("Fetching detail for %d strains...", len(ids))
    total = 0

    for i, sid in enumerate(ids):
        if (i + 1) % 500 == 0 or i == 0:
            log.info("  [%d/%d] strain %d", i + 1, len(ids), sid)
        total += fetch_strain_detail(sid, db_path)

    log.info("Strain detail fetch complete: %d growth observations enriched.", total)
    return total


if __name__ == "__main__":
    fetch_all_strain_details()
