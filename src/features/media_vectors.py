"""
Build sparse and dense media-composition vectors.

Each medium becomes a fixed-length vector where dimensions correspond to
ingredients and values are (log-scaled) concentrations.  This is the core
representation that downstream models consume.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.db.queries import get_all_ingredients, get_full_composition_matrix

log = logging.getLogger(__name__)


def build_ingredient_index(db_path: Any = None) -> dict[int, int]:
    """
    Map ingredient_id → dense column index (0 .. N-1).

    Returns
    -------
    dict mapping raw ingredient_id to a sequential integer index.
    """
    ingredients = get_all_ingredients(db_path)
    return {ing["ingredient_id"]: i for i, ing in enumerate(sorted(ingredients, key=lambda x: x["ingredient_id"]))}


def build_composition_matrix(db_path: Any = None) -> tuple[pd.DataFrame, list[str], dict[int, int]]:
    """
    Build a (media × ingredient) concentration matrix.

    Returns
    -------
    df : pd.DataFrame
        Rows = media_id, columns = ingredient index, values = concentration
        (0.0 where ingredient absent).
    media_ids : list[str]
        Ordered list of media IDs (row labels).
    idx_map : dict[int, int]
        ingredient_id → column index mapping.
    """
    idx_map = build_ingredient_index(db_path)
    n_ingredients = len(idx_map)

    triples = get_full_composition_matrix(db_path)
    log.info("Building composition matrix from %d triples across %d ingredients", len(triples), n_ingredients)

    # Group by media_id
    media_dict: dict[str, np.ndarray] = {}
    for row in triples:
        mid = row["media_id"]
        if mid not in media_dict:
            media_dict[mid] = np.zeros(n_ingredients, dtype=np.float32)
        col = idx_map.get(row["ingredient_id"])
        if col is not None:
            val = row["g_per_l"]
            media_dict[mid][col] = val if val is not None else 0.0

    media_ids = sorted(media_dict.keys())
    matrix = np.stack([media_dict[m] for m in media_ids])

    df = pd.DataFrame(matrix, index=media_ids)
    df.index.name = "media_id"
    log.info("Composition matrix shape: %s", df.shape)
    return df, media_ids, idx_map


def log_scale_concentrations(df: pd.DataFrame) -> pd.DataFrame:
    """Apply log1p scaling to handle wide concentration ranges."""
    return pd.DataFrame(
        np.log1p(df.values),
        index=df.index,
        columns=df.columns,
    )


def binary_presence(df: pd.DataFrame) -> pd.DataFrame:
    """Convert concentration matrix to binary presence/absence."""
    return (df > 0).astype(np.float32)
