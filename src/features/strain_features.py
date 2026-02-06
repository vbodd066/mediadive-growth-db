"""
Build strain-level features from growth observations.

For each strain, we derive features from:
- Which media it grows on → aggregate composition profile
- Growth success rate across media
- Media-type preferences (defined vs complex)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.db.queries import get_all_growth, get_all_media

log = logging.getLogger(__name__)


def build_strain_growth_matrix(db_path: Any = None) -> pd.DataFrame:
    """
    Build a (strain × media) binary growth matrix.

    Returns
    -------
    pd.DataFrame with strain_id as index, media_id as columns, values {0, 1}.
    """
    growth = get_all_growth(db_path)
    log.info("Building strain-growth matrix from %d observations", len(growth))

    df = pd.DataFrame(growth)
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        index="strain_id",
        columns="media_id",
        values="growth",
        aggfunc="max",
        fill_value=0,
    )
    log.info("Growth matrix shape: %s", pivot.shape)
    return pivot


def strain_summary_features(db_path: Any = None) -> pd.DataFrame:
    """
    Compute per-strain summary statistics.

    Features:
    - n_media_tested : number of media tested
    - n_media_grew   : number of media where growth observed
    - growth_rate    : fraction of tested media with growth
    - pct_complex    : fraction of successful media that are complex
    """
    growth = get_all_growth(db_path)
    media_list = get_all_media(db_path)
    media_is_complex = {m["media_id"]: bool(m["is_complex"]) for m in media_list}

    records: list[dict[str, Any]] = []
    # Group by strain
    strain_map: dict[int, list[dict]] = {}
    for g in growth:
        strain_map.setdefault(g["strain_id"], []).append(g)

    for sid, obs in strain_map.items():
        tested = len(obs)
        grew = [o for o in obs if o["growth"]]
        n_grew = len(grew)
        pct_complex = (
            np.mean([1 if media_is_complex.get(o["media_id"]) else 0 for o in grew])
            if n_grew > 0
            else 0.0
        )
        records.append(
            {
                "strain_id": sid,
                "n_media_tested": tested,
                "n_media_grew": n_grew,
                "growth_rate": n_grew / tested if tested else 0.0,
                "pct_complex": pct_complex,
            }
        )

    df = pd.DataFrame(records).set_index("strain_id")
    log.info("Strain summary features: %d strains", len(df))
    return df
