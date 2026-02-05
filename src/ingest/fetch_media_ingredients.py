import json
import sqlite3
import time
from pathlib import Path

from src.api.client import get

RAW_DIR = Path("data/raw/media_ingredients")
DB_PATH = Path("data/mediadive.db")

DELAY = 0.3


def fetch_all_media_ingredients():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    media_ids = [
        row[0]
        for row in conn.execute("SELECT media_id FROM media").fetchall()
    ]

    print(f"Found {len(media_ids)} media to process")

    for i, media_id in enumerate(media_ids):
        print(f"[{i+1}/{len(media_ids)}] Fetching composition for {media_id}")

        resp = get(f"/media/{media_id}/ingredients")
        data = resp.get("data", [])

        with open(RAW_DIR / f"{media_id}.json", "w") as f:
            json.dump(data, f, indent=2)

        for row in data:
            conn.execute(
                """
                INSERT OR IGNORE INTO media_ingredients
                (media_id, ingredient_id, concentration_value, concentration_unit, concentration_missing)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    row["ingredient_id"],
                    row.get("concentration"),
                    row.get("unit"),
                    row.get("concentration") is None,
                ),
            )

        conn.commit()
        time.sleep(DELAY)

    conn.close()
    print("Finished ingesting media compositions")


if __name__ == "__main__":
    fetch_all_media_ingredients()
