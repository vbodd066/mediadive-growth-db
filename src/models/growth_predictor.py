"""
Growth-prediction models.

Tier 1 (baseline):  sklearn classifiers — fast to iterate, strong baselines.
Tier 2 (deep):      PyTorch neural network — when data/complexity warrants it.

The neural model is designed to later accept additional strain-level
features (e.g. metagenomic embeddings) alongside media composition.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from src.models.base import BaseModel

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Tier 1 — Scikit-learn baselines
# ═══════════════════════════════════════════════════════════════

class SklearnGrowthPredictor(BaseModel):
    """
    Wraps any sklearn classifier to predict binary growth from
    media-composition vectors.
    """

    name = "sklearn_growth"

    def __init__(self, estimator: Any = None) -> None:
        if estimator is None:
            from sklearn.ensemble import GradientBoostingClassifier

            estimator = GradientBoostingClassifier(
                n_estimators=300,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                random_state=42,
            )
        self.estimator = estimator

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, **kwargs: Any) -> None:
        log.info("Fitting %s  X=%s", self.estimator.__class__.__name__, X_train.shape)
        self.estimator.fit(X_train, y_train)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict_proba(X)[:, 1]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.estimator, f)
        log.info("Saved sklearn model → %s", path)

    @classmethod
    def load(cls, path: Path) -> "SklearnGrowthPredictor":
        with open(path, "rb") as f:
            est = pickle.load(f)  # noqa: S301
        obj = cls(estimator=est)
        log.info("Loaded sklearn model ← %s", path)
        return obj

    def feature_importances(self) -> np.ndarray | None:
        """Return feature importances if the estimator supports it."""
        if hasattr(self.estimator, "feature_importances_"):
            return self.estimator.feature_importances_
        return None


# ═══════════════════════════════════════════════════════════════
#  Tier 2 — PyTorch neural growth predictor
# ═══════════════════════════════════════════════════════════════

class NeuralGrowthPredictor(BaseModel):
    """
    Feed-forward network for growth prediction.

    Architecture:
        media_vector → [Linear → ReLU → Dropout] × N → Linear → σ

    Designed so that an additional strain embedding can be concatenated
    to the input later (metagenomics features).
    """

    name = "neural_growth"

    def __init__(
        self,
        input_dim: int = 0,
        hidden_dims: list[int] | None = None,
        dropout: float = 0.3,
        lr: float = 1e-3,
    ) -> None:
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims or [256, 128, 64]
        self.dropout = dropout
        self.lr = lr
        self._model: Any = None  # torch.nn.Module (lazy import)

    def _build(self) -> None:
        import torch
        import torch.nn as nn

        layers: list[nn.Module] = []
        prev = self.input_dim
        for h in self.hidden_dims:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.BatchNorm1d(h), nn.Dropout(self.dropout)]
            prev = h
        layers.append(nn.Linear(prev, 1))
        self._model = nn.Sequential(*layers)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        epochs: int = 100,
        batch_size: int = 64,
        **kwargs: Any,
    ) -> dict[str, list[float]]:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        self.input_dim = X_train.shape[1]
        self._build()
        assert self._model is not None

        device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        self._model.to(device)
        log.info("Training on %s  input_dim=%d  epochs=%d", device, self.input_dim, epochs)

        optimizer = torch.optim.AdamW(self._model.parameters(), lr=self.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.BCEWithLogitsLoss()

        train_ds = TensorDataset(
            torch.tensor(X_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        )
        train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

        for epoch in range(1, epochs + 1):
            self._model.train()
            epoch_loss = 0.0
            for xb, yb in train_dl:
                xb, yb = xb.to(device), yb.to(device)
                logits = self._model(xb).squeeze(-1)
                loss = criterion(logits, yb)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(xb)

            scheduler.step()
            avg_train = epoch_loss / len(train_ds)
            history["train_loss"].append(avg_train)

            # Validation
            if X_val is not None and y_val is not None:
                val_loss = self._eval_loss(X_val, y_val, criterion, device)
                history["val_loss"].append(val_loss)
                if epoch % 10 == 0 or epoch == 1:
                    log.info("Epoch %3d/%d  train=%.4f  val=%.4f", epoch, epochs, avg_train, val_loss)
            else:
                if epoch % 10 == 0 or epoch == 1:
                    log.info("Epoch %3d/%d  train=%.4f", epoch, epochs, avg_train)

        return history

    def _eval_loss(self, X: np.ndarray, y: np.ndarray, criterion: Any, device: Any) -> float:
        import torch

        self._model.eval()  # type: ignore[union-attr]
        with torch.no_grad():
            xt = torch.tensor(X, dtype=torch.float32).to(device)
            yt = torch.tensor(y, dtype=torch.float32).to(device)
            logits = self._model(xt).squeeze(-1)  # type: ignore[union-attr]
            return criterion(logits, yt).item()

    def predict(self, X: np.ndarray) -> np.ndarray:
        proba = self.predict_proba(X)
        return (proba >= 0.5).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        import torch

        assert self._model is not None, "Model not trained yet."
        self._model.eval()
        device = next(self._model.parameters()).device
        with torch.no_grad():
            xt = torch.tensor(X, dtype=torch.float32).to(device)
            logits = self._model(xt).squeeze(-1)
            return torch.sigmoid(logits).cpu().numpy()

    def save(self, path: Path) -> None:
        import torch

        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self._model.state_dict(),  # type: ignore[union-attr]
                "input_dim": self.input_dim,
                "hidden_dims": self.hidden_dims,
                "dropout": self.dropout,
                "lr": self.lr,
            },
            path,
        )
        log.info("Saved neural model → %s", path)

    @classmethod
    def load(cls, path: Path) -> "NeuralGrowthPredictor":
        import torch

        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        obj = cls(
            input_dim=ckpt["input_dim"],
            hidden_dims=ckpt["hidden_dims"],
            dropout=ckpt["dropout"],
            lr=ckpt["lr"],
        )
        obj._build()
        obj._model.load_state_dict(ckpt["state_dict"])  # type: ignore[union-attr]
        log.info("Loaded neural model ← %s", path)
        return obj
