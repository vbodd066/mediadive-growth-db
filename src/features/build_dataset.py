"""
Assemble ML-ready datasets from feature matrices.

Two primary tasks:
1. **Growth prediction** – (strain, media_composition) → binary growth label
2. **Media generation** – future: strain profile → optimal media vector
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import DEFAULT_SEED, DEFAULT_TEST_SIZE, DEFAULT_VAL_SIZE, PROCESSED_DIR
from src.features.media_vectors import build_composition_matrix, log_scale_concentrations
from src.features.strain_features import build_strain_growth_matrix

log = logging.getLogger(__name__)


def build_growth_prediction_dataset(
    db_path: Any = None,
    test_size: float = DEFAULT_TEST_SIZE,
    val_size: float = DEFAULT_VAL_SIZE,
    seed: int = DEFAULT_SEED,
    save: bool = True,
) -> dict[str, pd.DataFrame | np.ndarray]:
    """
    Build the (X, y) dataset for growth prediction.

    Each sample is a (strain_id, media_id) pair.
    X = media composition vector (log-scaled concentrations).
    y = binary growth label.

    Returns dict with keys: X_train, X_val, X_test, y_train, y_val, y_test,
    plus metadata DataFrames.
    """
    log.info("Building growth-prediction dataset...")

    # 1. Composition matrix  (media × ingredients)
    comp_df, media_ids, idx_map = build_composition_matrix(db_path)
    comp_scaled = log_scale_concentrations(comp_df)

    # 2. Growth matrix  (strain × media)
    growth_mat = build_strain_growth_matrix(db_path)

    if growth_mat.empty:
        raise ValueError("No growth observations found — run the ingest pipeline first.")

    # 3. Flatten into (strain, media, label) rows
    overlapping_media = list(set(growth_mat.columns) & set(comp_scaled.index))
    log.info("Overlapping media between composition and growth: %d", len(overlapping_media))

    rows: list[dict[str, Any]] = []
    for strain_id in growth_mat.index:
        for media_id in overlapping_media:
            rows.append(
                {
                    "strain_id": strain_id,
                    "media_id": media_id,
                    "label": int(growth_mat.loc[strain_id, media_id]),
                }
            )

    samples = pd.DataFrame(rows)
    log.info("Total samples: %d  (positive=%.1f%%)", len(samples), samples["label"].mean() * 100)

    # 4. Attach composition features
    X = np.stack([comp_scaled.loc[mid].values for mid in samples["media_id"]])
    y = samples["label"].values

    # 5. Split: train / val / test  (stratified)
    X_temp, X_test, y_temp, y_test, idx_temp, idx_test = train_test_split(
        X, y, samples.index, test_size=test_size, random_state=seed, stratify=y,
    )
    relative_val = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val, idx_train, idx_val = train_test_split(
        X_temp, y_temp, idx_temp, test_size=relative_val, random_state=seed, stratify=y_temp,
    )

    log.info(
        "Split sizes — train: %d  val: %d  test: %d",
        len(X_train), len(X_val), len(X_test),
    )

    result = {
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "samples": samples,
        "composition_df": comp_scaled,
        "idx_map": idx_map,
    }

    if save:
        out = PROCESSED_DIR / "growth_prediction"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "X_train.npy", X_train)
        np.save(out / "X_val.npy", X_val)
        np.save(out / "X_test.npy", X_test)
        np.save(out / "y_train.npy", y_train)
        np.save(out / "y_val.npy", y_val)
        np.save(out / "y_test.npy", y_test)
        samples.to_parquet(out / "samples.parquet")
        log.info("Saved processed dataset to %s", out)

    return result
