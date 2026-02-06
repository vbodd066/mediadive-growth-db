"""
Cloud training launcher via Modal.

Modal lets you run GPU workloads on-demand without managing infrastructure.
See: https://modal.com/docs

Usage:
    modal run src/training/cloud/launch.py
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# ── Lazy Modal setup (only imported when actually launching) ────

try:
    import modal

    app = modal.App("mediadive-growth")

    image = (
        modal.Image.debian_slim(python_version="3.11")
        .pip_install(
            "torch>=2.2",
            "numpy>=1.26",
            "pandas>=2.1",
            "scikit-learn>=1.4",
            "scipy>=1.12",
            "requests>=2.31",
            "python-dotenv>=1.0",
        )
        .copy_local_dir("src", "/root/src")
        .copy_local_dir("data/processed", "/root/data/processed")
    )

    @app.function(
        image=image,
        gpu="T4",
        timeout=3600,
        secrets=[modal.Secret.from_name("mediadive-secrets")],
    )
    def train_remote(model_type: str = "neural", epochs: int = 100) -> dict:
        """Run training on a cloud GPU via Modal."""
        import sys
        sys.path.insert(0, "/root")

        from src.training.trainer import TrainConfig, train

        cfg = TrainConfig(model_type=model_type, epochs=epochs)
        result = train(cfg)
        return {
            "metrics": result["metrics"],
            "elapsed_seconds": result["elapsed_seconds"],
        }

    HAS_MODAL = True

except ImportError:
    HAS_MODAL = False
    log.debug("Modal not installed — cloud training unavailable.")


def launch_cloud_training(model_type: str = "neural", epochs: int = 100) -> dict | None:
    """Launch training on Modal (if available)."""
    if not HAS_MODAL:
        log.error("Modal is not installed. Run: pip install modal")
        return None

    log.info("Launching cloud training: model=%s epochs=%d", model_type, epochs)
    with modal.enable_output():  # type: ignore[union-attr]
        with app.run():  # type: ignore[union-attr]
            result = train_remote.remote(model_type=model_type, epochs=epochs)  # type: ignore[union-attr]
    return result  # type: ignore[return-value]
