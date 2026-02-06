"""
Run the full data ingestion pipeline.

Usage:
    python -m scripts.run_ingest             # full pipeline
    python -m scripts.run_ingest --step 1    # only media list
    python -m scripts.run_ingest --step 1-3  # media list + details + ingredients

Steps:
    1. Media list        (/media)
    2. Medium detail     (/medium/:id)         — solutions, recipes, steps
    3. Ingredients list  (/ingredients)
    4. Compositions      (/medium-composition/:id)
    5. Solutions list    (/solutions?all=1)
    6. Solution detail   (/solution/:id)       — recipe lines + steps
    7. Strain assoc.     (/medium-strains/:id) — strains + growth
    8. Strain detail     (/strain/id/:id)      — enriches growth observations

All steps are idempotent — they skip work already marked done in ingest_log.
"""

import argparse
import logging
import sys

import src  # noqa: F401 — triggers logging setup

from src.db.init_db import init_db
from src.db.queries import table_counts

log = logging.getLogger(__name__)


def _parse_steps(raw: str | None) -> set[int]:
    """Parse a step spec like '1', '1-3', or '2,5,7' into a set of ints."""
    if raw is None:
        return set(range(1, 9))
    out: set[int] = set()
    for part in raw.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaDive data ingestion")
    parser.add_argument("--step", type=str, default=None, help="Steps to run: 1-8, e.g. '1-3' or '2,5'")
    parser.add_argument("--db", type=str, default=None, help="Override DB path")
    args = parser.parse_args()

    steps = _parse_steps(args.step)
    db_path = init_db()

    log.info("═══ MediaDive Data Ingestion Pipeline ═══")
    log.info("Steps to run: %s", sorted(steps))

    if 1 in steps:
        from src.ingest.fetch_media import fetch_media_list

        log.info("Step 1/8: Fetching media list...")
        n = fetch_media_list(db_path)
        log.info("  → %d media records", n)

    if 2 in steps:
        from src.ingest.fetch_media import fetch_all_medium_details

        log.info("Step 2/8: Fetching medium details (solutions, recipes)...")
        n = fetch_all_medium_details(db_path)
        log.info("  → processed %d media", n)

    if 3 in steps:
        from src.ingest.fetch_ingredients import fetch_ingredient_list

        log.info("Step 3/8: Fetching ingredients...")
        n = fetch_ingredient_list(db_path)
        log.info("  → %d ingredients", n)

    if 4 in steps:
        from src.ingest.fetch_media import fetch_all_compositions

        log.info("Step 4/8: Fetching molecular compositions...")
        n = fetch_all_compositions(db_path)
        log.info("  → %d composition rows", n)

    if 5 in steps:
        from src.ingest.fetch_media_ingredients import fetch_solution_list

        log.info("Step 5/8: Fetching solutions list...")
        n = fetch_solution_list(db_path)
        log.info("  → %d solutions", n)

    if 6 in steps:
        from src.ingest.fetch_media_ingredients import fetch_all_solution_details

        log.info("Step 6/8: Fetching solution details...")
        n = fetch_all_solution_details(db_path)
        log.info("  → %d recipe lines", n)

    if 7 in steps:
        from src.ingest.fetch_media import fetch_all_medium_strains

        log.info("Step 7/8: Fetching strain-growth associations...")
        n = fetch_all_medium_strains(db_path)
        log.info("  → %d associations", n)

    if 8 in steps:
        from src.ingest.fetch_strain_growth import fetch_all_strain_details

        log.info("Step 8/8: Enriching strain detail...")
        n = fetch_all_strain_details(db_path)
        log.info("  → %d growth observations enriched", n)

    # ── Summary ──
    counts = table_counts(db_path)
    log.info("═══ Ingestion complete ═══")
    for table, count in sorted(counts.items()):
        log.info("  %-20s %d rows", table, count)


if __name__ == "__main__":
    main()
