"""
Train a model from the command line.

Usage:
    python -m scripts.train                           # sklearn baseline
    python -m scripts.train --model neural --epochs 50
    python -m scripts.train --model vae --epochs 200
    python -m scripts.train --model neural --cloud     # run on Modal GPU
"""

import argparse
import logging

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a MediaDive growth model")
    parser.add_argument("--model", choices=["sklearn", "neural", "vae"], default="sklearn")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, nargs="+", default=[256, 128, 64])
    parser.add_argument("--latent-dim", type=int, default=32)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cloud", action="store_true", help="Launch on Modal GPU")
    args = parser.parse_args()

    if args.cloud:
        from src.training.cloud.launch import launch_cloud_training

        result = launch_cloud_training(model_type=args.model, epochs=args.epochs)
        if result:
            log.info("Cloud training result: %s", result)
        return

    from src.training.trainer import TrainConfig, train

    cfg = TrainConfig(
        model_type=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        hidden_dims=args.hidden,
        latent_dim=args.latent_dim,
        dropout=args.dropout,
        seed=args.seed,
    )

    result = train(cfg)
    log.info("Final metrics: %s", result["metrics"])
    log.info("Model saved to: %s", result["save_path"])


if __name__ == "__main__":
    main()
