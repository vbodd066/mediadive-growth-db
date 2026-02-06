"""
Unified training runner.

Handles:
- Dataset loading (from saved .npy or building fresh)
- Model instantiation
- Training loop dispatch
- Evaluation + metric logging
- Artifact saving
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from src.config import DEFAULT_BATCH_SIZE, DEFAULT_EPOCHS, DEFAULT_LR, DEFAULT_SEED, MODELS_DIR, PROCESSED_DIR
from src.models.base import BaseModel
from src.models.evaluate import evaluate_growth_model
from src.models.growth_predictor import NeuralGrowthPredictor, SklearnGrowthPredictor
from src.models.media_generator import MediaVAE

log = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    """Training hyperparameters."""

    model_type: str = "sklearn"  # "sklearn" | "neural" | "vae"
    epochs: int = DEFAULT_EPOCHS
    batch_size: int = DEFAULT_BATCH_SIZE
    lr: float = DEFAULT_LR
    seed: int = DEFAULT_SEED
    hidden_dims: list[int] = field(default_factory=lambda: [256, 128, 64])
    latent_dim: int = 32
    dropout: float = 0.3
    beta: float = 1.0
    wandb_enabled: bool = False


def load_processed_dataset(base: Path | None = None) -> dict[str, np.ndarray]:
    """Load pre-built .npy arrays from the processed directory."""
    d = base or (PROCESSED_DIR / "growth_prediction")
    return {
        "X_train": np.load(d / "X_train.npy"),
        "X_val": np.load(d / "X_val.npy"),
        "X_test": np.load(d / "X_test.npy"),
        "y_train": np.load(d / "y_train.npy"),
        "y_val": np.load(d / "y_val.npy"),
        "y_test": np.load(d / "y_test.npy"),
    }


def train(cfg: TrainConfig | None = None) -> dict[str, Any]:
    """
    Run a full training pipeline.

    Returns dict with: model, metrics, history, elapsed_seconds.
    """
    cfg = cfg or TrainConfig()
    np.random.seed(cfg.seed)

    log.info("Loading dataset...")
    data = load_processed_dataset()
    X_train, y_train = data["X_train"], data["y_train"]
    X_val, y_val = data["X_val"], data["y_val"]
    X_test, y_test = data["X_test"], data["y_test"]

    log.info(
        "Dataset: train=%d  val=%d  test=%d  features=%d",
        len(X_train), len(X_val), len(X_test), X_train.shape[1],
    )

    # ── Instantiate model ───────────────────────────────────
    model: BaseModel
    if cfg.model_type == "sklearn":
        model = SklearnGrowthPredictor()
    elif cfg.model_type == "neural":
        model = NeuralGrowthPredictor(
            input_dim=X_train.shape[1],
            hidden_dims=cfg.hidden_dims,
            dropout=cfg.dropout,
            lr=cfg.lr,
        )
    elif cfg.model_type == "vae":
        model = MediaVAE(
            input_dim=X_train.shape[1],
            latent_dim=cfg.latent_dim,
            hidden_dims=cfg.hidden_dims[:2],
            beta=cfg.beta,
            lr=cfg.lr,
        )
    else:
        raise ValueError(f"Unknown model_type: {cfg.model_type}")

    # ── Train ───────────────────────────────────────────────
    log.info("Training %s...", model.name)
    t0 = time.time()
    history: dict[str, Any] = {}

    if cfg.model_type == "sklearn":
        model.fit(X_train, y_train)
    elif cfg.model_type == "neural":
        history = model.fit(
            X_train, y_train, X_val=X_val, y_val=y_val,
            epochs=cfg.epochs, batch_size=cfg.batch_size,
        ) or {}
    elif cfg.model_type == "vae":
        history = model.fit(
            X_train, None, X_val=X_val,
            epochs=cfg.epochs, batch_size=cfg.batch_size,
        ) or {}

    elapsed = time.time() - t0
    log.info("Training complete in %.1f seconds.", elapsed)

    # ── Evaluate ────────────────────────────────────────────
    if cfg.model_type in ("sklearn", "neural"):
        metrics = evaluate_growth_model(model, X_test, y_test)
    else:
        from src.models.evaluate import reconstruction_metrics

        recon = model.predict(X_test)
        metrics = reconstruction_metrics(X_test, recon)

    # ── Save ────────────────────────────────────────────────
    suffix = ".pkl" if cfg.model_type == "sklearn" else ".pt"
    save_path = MODELS_DIR / f"{model.name}{suffix}"
    model.save(save_path)

    return {
        "model": model,
        "metrics": metrics,
        "history": history,
        "elapsed_seconds": elapsed,
        "save_path": save_path,
    }
