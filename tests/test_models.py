"""Tests for model classes."""

from pathlib import Path

import numpy as np
import pytest


@pytest.mark.unit
class TestSklearnGrowthPredictor:
    def test_fit_predict(self) -> None:
        from src.models.growth_predictor import SklearnGrowthPredictor

        np.random.seed(42)
        X = np.random.randn(100, 10).astype(np.float32)
        y = (X[:, 0] > 0).astype(int)

        model = SklearnGrowthPredictor()
        model.fit(X, y)

        preds = model.predict(X)
        assert preds.shape == (100,)
        assert set(np.unique(preds)) <= {0, 1}

    def test_predict_proba_range(self) -> None:
        from src.models.growth_predictor import SklearnGrowthPredictor

        np.random.seed(42)
        X = np.random.randn(50, 5).astype(np.float32)
        y = (X[:, 0] > 0).astype(int)

        model = SklearnGrowthPredictor()
        model.fit(X, y)

        proba = model.predict_proba(X)
        assert proba.min() >= 0.0
        assert proba.max() <= 1.0

    def test_save_load(self, tmp_path: Path) -> None:
        from src.models.growth_predictor import SklearnGrowthPredictor

        np.random.seed(42)
        X = np.random.randn(50, 5).astype(np.float32)
        y = (X[:, 0] > 0).astype(int)

        model = SklearnGrowthPredictor()
        model.fit(X, y)
        preds_before = model.predict(X)

        save_path = tmp_path / "model.pkl"
        model.save(save_path)

        loaded = SklearnGrowthPredictor.load(save_path)
        preds_after = loaded.predict(X)

        np.testing.assert_array_equal(preds_before, preds_after)

    def test_feature_importances(self) -> None:
        from src.models.growth_predictor import SklearnGrowthPredictor

        np.random.seed(42)
        X = np.random.randn(50, 5).astype(np.float32)
        y = (X[:, 0] > 0).astype(int)

        model = SklearnGrowthPredictor()
        model.fit(X, y)

        imp = model.feature_importances()
        assert imp is not None
        assert len(imp) == 5


@pytest.mark.unit
class TestEvaluationMetrics:
    def test_classification_metrics(self) -> None:
        from src.models.evaluate import classification_metrics

        y_true = np.array([1, 0, 1, 1, 0])
        y_pred = np.array([1, 0, 0, 1, 0])
        y_proba = np.array([0.9, 0.1, 0.4, 0.8, 0.2])

        metrics = classification_metrics(y_true, y_pred, y_proba)
        assert "accuracy" in metrics
        assert "f1" in metrics
        assert "auc_roc" in metrics
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["auc_roc"] <= 1

    def test_reconstruction_metrics(self) -> None:
        from src.models.evaluate import reconstruction_metrics

        X = np.random.randn(10, 5).astype(np.float32)
        X_recon = X + np.random.randn(10, 5).astype(np.float32) * 0.1

        metrics = reconstruction_metrics(X, X_recon)
        assert "mse" in metrics
        assert "mean_cosine_similarity" in metrics
        assert metrics["mse"] > 0
        assert metrics["mean_cosine_similarity"] > 0.5  # should be close for small noise
