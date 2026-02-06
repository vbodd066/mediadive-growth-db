"""
Abstract base class for all MediaDive models.

Enforces a consistent interface so that models can be swapped,
evaluated, and serialized uniformly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np


class BaseModel(ABC):
    """Interface all MediaDive models must implement."""

    name: str = "base"

    @abstractmethod
    def fit(self, X_train: np.ndarray, y_train: np.ndarray, **kwargs: Any) -> dict[str, Any] | None:
        """Train the model. Returns training history dict if applicable."""
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predictions (class labels or generated vectors)."""
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability estimates (where applicable)."""
        ...

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist the model to disk."""
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> "BaseModel":
        """Load a model from disk."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
