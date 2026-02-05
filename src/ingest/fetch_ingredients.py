import json
import sqlite3
import time
from pathlib import Path

from src.api.client import get

RAW_DIR = Path("data/raw/ingredients")
DB_PATH = Path("data/mediadive.db")

LIMIT = 200
DELAY = 0.5


def fetch_all_ingredients():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    offset = 0
    page = 0

    while True:
        print(f"Fetching ingredients page {page}")

        resp = get("/ingredients", params={"limit": LIMIT, "offset": offset})
        data = resp.get("data", [])

        if not data:
            break

        with open(RAW_DIR / f"ingredients_offset_{offset}.json", "w") as f:
            json.dump(data, f, indent=2)

        for ing in data:
            conn.execute(
                """
                INSERT OR IGNORE INTO ingredients
                (ingredient_id, ingredient_name, ingredient_class, formula, kegg_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ing["id"],
                    ing["name"],
                    ing.get("class"),
                    ing.get("formula"),
                    ing.get("kegg_id"),
                ),
            )

        conn.commit()
        offset += LIMIT
        page += 1
        time.sleep(DELAY)

    conn.close()
    print("Finished ingesting ingredients")


if __name__ == "__main__":
    fetch_all_ingredients()
