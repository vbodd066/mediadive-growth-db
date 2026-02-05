import json
import sqlite3
import time
from pathlib import Path

from src.api.client import get

RAW_DIR = Path("data/raw/media")
DB_PATH = Path("data/mediadive.db")

LIMIT = 100
DELAY = 0.5  # seconds


def fetch_all_media():
    print("Creating output directories...")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Opening database...")
    conn = sqlite3.connect(DB_PATH)

    offset = 0
    page = 0

    while True:
        print(f"\nRequesting page {page} (offset={offset}, limit={LIMIT})")

        resp = get("/media", params={"limit": LIMIT, "offset": offset})

        # MediaDive REST wraps results in a dict
        if not isinstance(resp, dict) or "data" not in resp:
            raise RuntimeError(f"Unexpected response structure: {resp}")

        data = resp["data"]

        if len(data) == 0:
            print("No more media returned. Done.")
            break

        # Save raw snapshot
        raw_path = RAW_DIR / f"media_offset_{offset}.json"
        with open(raw_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Fetched {len(data)} media records")

        # Insert into DB
        for m in data:
            conn.execute(
                """
                INSERT OR IGNORE INTO media
                (media_id, media_name, media_type, source, min_pH, max_pH)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    m["id"],
                    m["name"],
                    "complex" if m.get("complex_medium") else "defined",
                    m.get("source"),
                    m.get("min_pH"),
                    m.get("max_pH"),
                ),
            )

        conn.commit()

        offset += LIMIT
        page += 1
        time.sleep(DELAY)

    conn.close()
    print("\nFinished fetching all media.")


if __name__ == "__main__":
    print("=== fetch_media module executed ===")
    fetch_all_media()
