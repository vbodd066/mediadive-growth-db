"""
Shared test fixtures for the MediaDive test suite.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite DB with the MediaDive schema populated with test data."""
    db_path = tmp_path / "test.db"
    schema_path = Path(__file__).resolve().parent.parent / "src" / "db" / "schema.sql"

    conn = sqlite3.connect(db_path)
    with open(schema_path) as f:
        conn.executescript(f.read())

    # ── Seed test data ──────────────────────────────────────
    # 3 media
    conn.executemany(
        "INSERT INTO media (media_id, media_name, is_complex, min_pH, max_pH) VALUES (?,?,?,?,?)",
        [
            ("M1", "Nutrient Broth", 1, 6.8, 7.2),
            ("M2", "Minimal Salts", 0, 7.0, 7.0),
            ("M3", "Rich Medium", 1, 6.5, 7.5),
        ],
    )

    # 5 ingredients
    conn.executemany(
        "INSERT INTO ingredients (ingredient_id, ingredient_name, formula) VALUES (?,?,?)",
        [
            (1, "Glucose", "C6H12O6"),
            (2, "Peptone", None),
            (3, "NaCl", "NaCl"),
            (4, "KH2PO4", "KH2PO4"),
            (5, "MgSO4", "MgSO4"),
        ],
    )

    # Media molecular compositions (media_composition table)
    conn.executemany(
        "INSERT INTO media_composition (media_id, ingredient_id, ingredient_name, g_per_l) VALUES (?,?,?,?)",
        [
            ("M1", 1, "Glucose", 5.0),
            ("M1", 2, "Peptone", 10.0),
            ("M1", 3, "NaCl", 5.0),
            ("M2", 1, "Glucose", 2.0),
            ("M2", 4, "KH2PO4", 1.0),
            ("M2", 5, "MgSO4", 0.5),
            ("M3", 1, "Glucose", 10.0),
            ("M3", 2, "Peptone", 20.0),
            ("M3", 3, "NaCl", 5.0),
            ("M3", 4, "KH2PO4", 2.0),
            ("M3", 5, "MgSO4", 1.0),
        ],
    )

    # Strains
    conn.executemany(
        "INSERT INTO strains (strain_id, species, domain) VALUES (?,?,?)",
        [
            (101, "Bacillus subtilis", "B"),
            (102, "Escherichia coli", "B"),
        ],
    )

    # Growth observations (2 strains)
    conn.executemany(
        "INSERT INTO strain_growth (strain_id, media_id, growth) VALUES (?,?,?)",
        [
            (101, "M1", True),
            (101, "M2", False),
            (101, "M3", True),
            (102, "M1", False),
            (102, "M2", True),
            (102, "M3", True),
        ],
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_composition_matrix() -> np.ndarray:
    """A small (3 × 5) composition matrix for unit tests."""
    return np.array(
        [
            [5.0, 10.0, 5.0, 0.0, 0.0],  # M1
            [2.0, 0.0, 0.0, 1.0, 0.5],   # M2
            [10.0, 20.0, 5.0, 2.0, 1.0],  # M3
        ],
        dtype=np.float32,
    )


@pytest.fixture
def sample_labels() -> np.ndarray:
    """Binary growth labels matching sample_composition_matrix."""
    return np.array([1, 0, 1, 0, 1, 1], dtype=np.int64)
