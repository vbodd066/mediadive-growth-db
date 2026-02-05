import json
import sqlite3
import time
from pathlib import Path

from src.api.client import get

RAW_DIR = Path("data/raw/strains")
DB_PATH = Path("data/mediadive.db")

DELAY = 0.3


def fetch_strain_by_id(strain_id: int):
    """Fetch a single strain by numeric ID."""
    return get(f"/strain/id/{strain_id}")


def ingest_strains(start_id=1, end_id=50000):
    """
    Iterates over strain IDs and ingests strain-level growth data.
    Adjust end_id based on API coverage / rate limits.
    """

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    for strain_id in range(start_id, end_id + 1):
        print(f"Fetching strain {strain_id}")

        try:
            resp = fetch_strain_by_id(strain_id)
        except Exception as e:
            # 404s or API errors are expected
            continue

        if not resp or "id" not in resp:
            continue

        # Save raw snapshot
        with open(RAW_DIR / f"strain_{strain_id}.json", "w") as f:
            json.dump(resp, f, indent=2)

        media_list = resp.get("media", [])

        for m in media_list:
            medium_id = str(m.get("medium_id"))  # normalize to TEXT

            conn.execute(
                """
                INSERT OR IGNORE INTO strain_growth
                (strain_id, media_id, growth_observed)
                VALUES (?, ?, ?)
                """,
                (
                    resp["id"],
                    medium_id,
                    bool(m.get("growth")),
                ),
            )

        conn.commit()
        time.sleep(DELAY)

    conn.close()
    print("Finished ingesting strain data")


if __name__ == "__main__":
    ingest_strains()

