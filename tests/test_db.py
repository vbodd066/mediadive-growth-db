"""Tests for DB initialization and query helpers."""

from pathlib import Path

import pytest

from src.db.init_db import init_db
from src.db.queries import (
    get_all_growth,
    get_all_ingredients,
    get_all_media,
    get_full_composition_matrix,
    get_ingredient_index,
    get_media_ids,
    table_counts,
)


@pytest.mark.unit
class TestInitDb:
    def test_creates_database(self, tmp_path: Path) -> None:
        db_path = tmp_path / "new.db"
        init_db(db_path)
        assert db_path.exists()

    def test_schema_creates_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "new.db"
        init_db(db_path)
        counts = table_counts(db_path)
        expected_tables = {
            "media", "ingredients", "solutions", "media_solutions",
            "solution_recipe", "solution_steps", "media_composition",
            "strains", "strain_growth",
        }
        assert set(counts.keys()) == expected_tables
        assert all(v == 0 for v in counts.values())

    def test_idempotent_reinit(self, tmp_db: Path) -> None:
        """Re-running init_db should not destroy existing data."""
        init_db(tmp_db)
        media = get_all_media(tmp_db)
        assert len(media) == 3  # data survives re-init


@pytest.mark.unit
class TestQueries:
    def test_get_all_media(self, tmp_db: Path) -> None:
        media = get_all_media(tmp_db)
        assert len(media) == 3
        assert media[0]["media_name"] is not None

    def test_get_media_ids(self, tmp_db: Path) -> None:
        ids = get_media_ids(tmp_db)
        assert set(ids) == {"M1", "M2", "M3"}

    def test_get_all_ingredients(self, tmp_db: Path) -> None:
        ingredients = get_all_ingredients(tmp_db)
        assert len(ingredients) == 5
        names = {i["ingredient_name"] for i in ingredients}
        assert "Glucose" in names

    def test_get_ingredient_index(self, tmp_db: Path) -> None:
        idx = get_ingredient_index(tmp_db)
        assert len(idx) == 5
        assert all(isinstance(k, int) for k in idx)

    def test_get_full_composition_matrix(self, tmp_db: Path) -> None:
        triples = get_full_composition_matrix(tmp_db)
        assert len(triples) == 11  # matches seed data

    def test_get_all_growth(self, tmp_db: Path) -> None:
        growth = get_all_growth(tmp_db)
        assert len(growth) == 6

    def test_table_counts(self, tmp_db: Path) -> None:
        counts = table_counts(tmp_db)
        assert counts["media"] == 3
        assert counts["ingredients"] == 5
        assert counts["media_composition"] == 11
        assert counts["strain_growth"] == 6
        assert counts["strains"] == 2
