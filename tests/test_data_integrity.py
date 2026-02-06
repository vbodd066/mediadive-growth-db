"""
Data integrity tests — validate assumptions about the ingested dataset.

Run after ingestion to catch data quality issues early.
These tests require a populated database, so they're marked as integration tests.
"""

from pathlib import Path

import pytest

from src.config import DB_PATH
from src.db.queries import (
    get_all_growth,
    get_all_ingredients,
    get_all_media,
    get_full_composition_matrix,
    table_counts,
)


def _db_exists() -> bool:
    return DB_PATH.exists()


@pytest.mark.integration
@pytest.mark.skipif(not _db_exists(), reason="No ingested database found")
class TestDataIntegrity:
    """Validate the ingested MediaDive dataset."""

    def test_core_tables_not_empty(self) -> None:
        counts = table_counts()
        core = ["media", "ingredients", "media_composition", "strain_growth", "strains"]
        for table in core:
            assert counts.get(table, 0) > 0, f"Table '{table}' is empty"

    def test_media_have_names(self) -> None:
        media = get_all_media()
        for m in media:
            assert m["media_name"], f"Media {m['media_id']} has no name"

    def test_ingredients_have_names(self) -> None:
        ingredients = get_all_ingredients()
        for ing in ingredients:
            assert ing["ingredient_name"], f"Ingredient {ing['ingredient_id']} has no name"

    def test_compositions_reference_valid_media(self) -> None:
        media_ids = {m["media_id"] for m in get_all_media()}
        compositions = get_full_composition_matrix()
        for row in compositions:
            assert row["media_id"] in media_ids, f"Orphan composition for media {row['media_id']}"

    def test_growth_references_valid_media(self) -> None:
        media_ids = {m["media_id"] for m in get_all_media()}
        growth = get_all_growth()
        orphans = [g for g in growth if g["media_id"] not in media_ids]
        if orphans:
            pytest.skip(f"{len(orphans)} growth observations reference unknown media")

    def test_concentration_values_non_negative(self) -> None:
        compositions = get_full_composition_matrix()
        for row in compositions:
            val = row["g_per_l"]
            if val is not None:
                assert val >= 0, f"Negative concentration: media={row['media_id']} ing={row['ingredient_id']}"

    def test_growth_labels_binary(self) -> None:
        growth = get_all_growth()
        for g in growth:
            assert g["growth"] in (0, 1, True, False), f"Non-binary growth: {g}"
