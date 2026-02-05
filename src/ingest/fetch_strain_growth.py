import json
import sqlite3
import time
from pathlib import Path

from src.api.client import get

RAW_DIR = Path("data/raw/strain_growth")
DB_PATH = Path("data/mediadive.db")

LIMIT = 200
DELAY = 0.5


def fetch_all_growth_data():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    offset = 0
    page = 0

    while True:
        print(f"Fetching growth observations page {page}")

        resp = get("/growth", params={"limit": LIMIT, "offset": offset})
        data = resp.get("data", [])

        if not data:
            break

        with open(RAW_DIR / f"growth_offset_{offset}.json", "w") as f:
            json.dump(data, f, indent=2)

        for g in data:
            conn.execute(
                """
                INSERT OR IGNORE INTO strain_growth
                (strain_id, media_id, growth_observed)
                VALUES (?, ?, ?)
                """,
                (
                    g["strain_id"],
                    g["media_id"],
                    g["growth"],
                ),
            )

        conn.commit()
        offset += LIMIT
        page += 1
        time.sleep(DELAY)

    conn.close()
    print("Finished ingesting strain growth data")


if __name__ == "__main__":
    fetch_all_growth_data()
