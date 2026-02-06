"""
Ingest ingredient master data from the MediaDive REST API.

Endpoints used:
    GET /ingredients?limit=N&offset=M  → paginated ingredient list
    GET /ingredient/:id                → full detail (synonyms, roles, media list)
"""

from __future__ import annotations

import logging

from src.api.client import paginate
from src.db.queries import connect, is_task_done, mark_task_done

log = logging.getLogger(__name__)


def fetch_ingredient_list(db_path=None) -> int:
    """Fetch all ingredients from the paginated /ingredients endpoint."""
    task = "ingredient_list"
    if is_task_done(task, db_path):
        log.info("Skipping %s (already done)", task)
        with connect(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]

    total = 0
    with connect(db_path) as conn:
        for page in paginate("/ingredients", limit=200):
            for ing in page:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ingredients
                        (ingredient_id, ingredient_name, chebi_id, cas_rn,
                         pubchem_id, molar_mass, formula, density)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ing["id"],
                        ing["name"],
                        ing.get("ChEBI"),
                        ing.get("CAS-RN"),
                        ing.get("PubChem"),
                        ing.get("mass"),
                        ing.get("formula"),
                        ing.get("density"),
                    ),
                )
            conn.commit()
            total += len(page)

    mark_task_done(task, db_path)
    log.info("Fetched %d ingredients.", total)
    return total


if __name__ == "__main__":
    fetch_ingredient_list()
