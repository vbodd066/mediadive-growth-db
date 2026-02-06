"""Tests for the feature engineering pipeline."""

from pathlib import Path

import numpy as np
import pytest

from src.features.media_vectors import (
    binary_presence,
    build_composition_matrix,
    build_ingredient_index,
    log_scale_concentrations,
)
from src.features.strain_features import build_strain_growth_matrix, strain_summary_features


@pytest.mark.unit
class TestMediaVectors:
    def test_build_ingredient_index(self, tmp_db: Path) -> None:
        idx = build_ingredient_index(tmp_db)
        assert len(idx) == 5
        # Values should be sequential 0..4
        assert set(idx.values()) == {0, 1, 2, 3, 4}

    def test_build_composition_matrix_shape(self, tmp_db: Path) -> None:
        df, media_ids, idx_map = build_composition_matrix(tmp_db)
        assert df.shape == (3, 5)  # 3 media × 5 ingredients
        assert len(media_ids) == 3
        assert len(idx_map) == 5

    def test_build_composition_matrix_values(self, tmp_db: Path) -> None:
        df, _, _ = build_composition_matrix(tmp_db)
        # All values should be non-negative
        assert (df.values >= 0).all()
        # Should have non-zero entries
        assert df.values.sum() > 0

    def test_log_scale_concentrations(self, sample_composition_matrix: np.ndarray) -> None:
        import pandas as pd

        df = pd.DataFrame(sample_composition_matrix)
        scaled = log_scale_concentrations(df)
        # log1p(0) == 0
        assert scaled.values[0, 3] == 0.0
        # log1p(x) > 0 for x > 0
        assert (scaled.values[sample_composition_matrix > 0] > 0).all()
        # log1p(x) < x for x > 0
        assert (scaled.values[sample_composition_matrix > 0] < sample_composition_matrix[sample_composition_matrix > 0]).all()

    def test_binary_presence(self, sample_composition_matrix: np.ndarray) -> None:
        import pandas as pd

        df = pd.DataFrame(sample_composition_matrix)
        binary = binary_presence(df)
        assert set(np.unique(binary.values)) <= {0.0, 1.0}


@pytest.mark.unit
class TestStrainFeatures:
    def test_growth_matrix_shape(self, tmp_db: Path) -> None:
        gm = build_strain_growth_matrix(tmp_db)
        assert gm.shape[0] == 2   # 2 strains
        assert gm.shape[1] == 3   # 3 media

    def test_strain_summary(self, tmp_db: Path) -> None:
        summary = strain_summary_features(tmp_db)
        assert len(summary) == 2
        assert "growth_rate" in summary.columns
        assert "n_media_grew" in summary.columns
        # Strain 101 grew on M1 and M3 → growth_rate = 2/3
        row = summary.loc[101]
        assert row["n_media_grew"] == 2
        assert abs(row["growth_rate"] - 2 / 3) < 1e-6
