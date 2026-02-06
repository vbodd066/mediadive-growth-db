"""
Model evaluation utilities.

Centralizes metric computation, classification reports, and
plotting for consistent experiment comparison.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger(__name__)


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray | None = None) -> dict[str, float]:
    """
    Compute standard binary classification metrics.

    Returns dict with: accuracy, precision, recall, f1, mcc, auc_roc (if proba given).
    """
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        matthews_corrcoef,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    metrics: dict[str, float] = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "mcc": matthews_corrcoef(y_true, y_pred),
    }

    if y_proba is not None and len(np.unique(y_true)) > 1:
        metrics["auc_roc"] = roc_auc_score(y_true, y_proba)

    return metrics


def reconstruction_metrics(X_true: np.ndarray, X_recon: np.ndarray) -> dict[str, float]:
    """
    Evaluate media-composition reconstruction quality.

    Relevant for the VAE / generative model.
    """
    mse = float(np.mean((X_true - X_recon) ** 2))
    cosine_sims = []
    for a, b in zip(X_true, X_recon):
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        cosine_sims.append(float(np.dot(a, b) / denom) if denom > 0 else 0.0)

    return {
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "mean_cosine_similarity": float(np.mean(cosine_sims)),
    }


def print_metrics(metrics: dict[str, float], header: str = "Metrics") -> None:
    """Pretty-print a metrics dictionary."""
    log.info("── %s ──", header)
    for k, v in metrics.items():
        log.info("  %-25s %.4f", k, v)


def evaluate_growth_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, float]:
    """Full evaluation of a growth-prediction model."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)
    metrics = classification_metrics(y_test, y_pred, y_proba)
    print_metrics(metrics, header=f"{model.name} — Test Set")
    return metrics
