"""
Assemble ML-ready datasets from feature matrices.

Primary tasks:
1. **Growth prediction** – (strain, media_composition) → binary growth label
2. **Media generation** – (genome, media_composition) → media vector (CVAE)
3. **Curriculum learning** – stratified by organism type (bacteria → archea → fungi → ...)
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import DEFAULT_SEED, DEFAULT_TEST_SIZE, DEFAULT_VAL_SIZE, PROCESSED_DIR, DB_PATH
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

def build_genome_media_dataset(
    embedding_method: str = "kmer_128",
    organism_type: str | None = None,
    test_size: float = DEFAULT_TEST_SIZE,
    val_size: float = DEFAULT_VAL_SIZE,
    seed: int = DEFAULT_SEED,
    save: bool = True,
) -> dict[str, Any]:
    """
    Build dataset for Conditional VAE training: (genome_embedding, media) pairs.

    Each sample pairs a genome with a media it can grow in.
    This enables learning organism-specific media preferences.

    Args:
        embedding_method: Genome embedding method ('kmer_128', 'kmer_256', 'stats')
        organism_type: Filter to specific organism type (optional). 
                      If None, includes all types.
        test_size: Fraction for test set
        val_size: Fraction for validation set
        seed: Random seed
        save: Whether to save processed arrays

    Returns:
        Dict with keys: X_train, X_val, X_test, C_train, C_val, C_test,
        y_train, y_val, y_test (organism types), samples DataFrame
    """
    import pickle

    log.info(
        "Building genome-media dataset (method=%s, organism_type=%s)...",
        embedding_method,
        organism_type or "all",
    )

    # 1. Media composition matrix
    comp_df, media_ids, idx_map = build_composition_matrix()
    comp_scaled = log_scale_concentrations(comp_df)

    # 2. Query genome-media growth pairs
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if organism_type:
            cursor.execute(
                """
                SELECT gg.genome_id, gg.media_id, gg.growth, g.organism_type
                FROM genome_growth gg
                JOIN genomes g ON gg.genome_id = g.genome_id
                WHERE gg.growth = 1 AND g.organism_type = ?
                """,
                (organism_type,),
            )
        else:
            cursor.execute(
                """
                SELECT gg.genome_id, gg.media_id, gg.growth, g.organism_type
                FROM genome_growth gg
                JOIN genomes g ON gg.genome_id = g.genome_id
                WHERE gg.growth = 1
                """
            )

        growth_pairs = [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()

    if not growth_pairs:
        raise ValueError(f"No genome-media growth pairs found (organism_type={organism_type})")

    log.info("Found %d positive genome-media pairs", len(growth_pairs))

    # 3. Filter to genomes with precomputed embeddings
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT DISTINCT genome_id
            FROM genome_embeddings
            WHERE embedding_model = ?
            """,
            (embedding_method,),
        )
        genomes_with_embeddings = {row[0] for row in cursor.fetchall()}

    finally:
        conn.close()

    log.info("Genomes with precomputed embeddings: %d", len(genomes_with_embeddings))

    # Filter pairs to those with embeddings
    pairs_filtered = [p for p in growth_pairs if p["genome_id"] in genomes_with_embeddings]
    log.info("Pairs after filtering: %d", len(pairs_filtered))

    if not pairs_filtered:
        raise ValueError(f"No genome embeddings found for method={embedding_method}")

    # 4. Load embeddings and build feature matrix
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    X_list = []  # media compositions
    C_list = []  # genome embeddings
    organism_types = []
    samples_data = []

    for pair in pairs_filtered:
        genome_id = pair["genome_id"]
        media_id = pair["media_id"]

        if media_id not in comp_scaled.index:
            continue  # Skip if media not in composition matrix

        # Load genome embedding
        cursor.execute(
            "SELECT embedding FROM genome_embeddings WHERE genome_id = ? AND embedding_model = ?",
            (genome_id, embedding_method),
        )
        row = cursor.fetchone()
        if not row:
            continue

        embedding = pickle.loads(row[0])

        # Get media composition
        x = comp_scaled.loc[media_id].values

        X_list.append(x)
        C_list.append(embedding)
        organism_types.append(pair["organism_type"])
        samples_data.append(
            {
                "genome_id": genome_id,
                "media_id": media_id,
                "organism_type": pair["organism_type"],
            }
        )

    conn.close()

    if not X_list:
        raise ValueError("No valid genome-media samples after filtering")

    X = np.array(X_list, dtype=np.float32)
    C = np.array(C_list, dtype=np.float32)
    y = np.array([ORGANISM_TYPES.get(t, {}).get("priority", 999) for t in organism_types])

    samples = pd.DataFrame(samples_data)
    log.info("Final dataset: %d samples  X.shape=%s  C.shape=%s", len(X), X.shape, C.shape)

    # 5. Stratified split by organism type
    indices = np.arange(len(X))
    X_temp, X_test, C_temp, C_test, y_temp, y_test, idx_temp, idx_test = train_test_split(
        X,
        C,
        y,
        indices,
        test_size=test_size,
        random_state=seed,
        stratify=y,
    )

    relative_val = val_size / (1 - test_size)
    X_train, X_val, C_train, C_val, y_train, y_val, idx_train, idx_val = train_test_split(
        X_temp,
        C_temp,
        y_temp,
        idx_temp,
        test_size=relative_val,
        random_state=seed,
        stratify=y_temp,
    )

    log.info(
        "Split sizes — train: %d  val: %d  test: %d",
        len(X_train),
        len(X_val),
        len(X_test),
    )

    result = {
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "C_train": C_train,
        "C_val": C_val,
        "C_test": C_test,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "samples": samples,
        "composition_df": comp_scaled,
        "embedding_method": embedding_method,
    }

    if save:
        out = PROCESSED_DIR / f"genome_media_cvae"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "X_train.npy", X_train)
        np.save(out / "X_val.npy", X_val)
        np.save(out / "X_test.npy", X_test)
        np.save(out / "C_train.npy", C_train)
        np.save(out / "C_val.npy", C_val)
        np.save(out / "C_test.npy", C_test)
        np.save(out / "y_train.npy", y_train)
        np.save(out / "y_val.npy", y_val)
        np.save(out / "y_test.npy", y_test)
        samples.to_parquet(out / "samples.parquet")
        log.info("Saved CVAE dataset to %s", out)

    return result


ORGANISM_TYPES = {
    "bacteria": {"suffix": "bacteria", "priority": 1},
    "archea": {"suffix": "archea", "priority": 2},
    "fungi": {"suffix": "fungi", "priority": 3},
    "protist": {"suffix": "protist", "priority": 4},
    "virus": {"suffix": "virus", "priority": 5},
}