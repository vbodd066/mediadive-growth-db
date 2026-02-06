"""
Build ML-ready feature matrices from the ingested database.

Usage:
    python -m scripts.build_features
"""

import logging

from src.features.build_dataset import build_growth_prediction_dataset

log = logging.getLogger(__name__)


def main() -> None:
    log.info("═══ Building Feature Datasets ═══")
    result = build_growth_prediction_dataset(save=True)
    log.info(
        "Dataset built — train=%d  val=%d  test=%d",
        len(result["X_train"]),
        len(result["X_val"]),
        len(result["X_test"]),
    )
    log.info("═══ Done ═══")


if __name__ == "__main__":
    main()
