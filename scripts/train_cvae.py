#!/usr/bin/env python3
"""
Build genome dataset and train Conditional VAE for media generation.

This script demonstrates the full pipeline:
1. Compute genome embeddings (k-mer profiles)
2. Build genome-media dataset
3. Train CVAE with curriculum learning (bacteria → archea → fungi → ...)
4. Generate novel media formulations for unseen organisms

Usage:
    python -m scripts.train_cvae --help
    python -m scripts.train_cvae --organism bacteria --epochs 100
    python -m scripts.train_cvae --all-organisms --curriculum
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.features.build_dataset import build_genome_media_dataset
from src.features.genome_features import compute_all_genome_embeddings
from src.training.trainer import TrainConfig, train

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
log = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train Conditional VAE for media generation from genomes"
    )
    parser.add_argument(
        "--organism",
        default=None,
        help="Filter to specific organism type (bacteria, archea, fungi, protist, virus)",
    )
    parser.add_argument(
        "--all-organisms",
        action="store_true",
        help="Train on all organism types (curriculum learning)",
    )
    parser.add_argument(
        "--embedding-method",
        default="kmer_128",
        help="Genome embedding method: kmer_64, kmer_128, kmer_256, stats",
    )
    parser.add_argument(
        "--compute-embeddings",
        action="store_true",
        help="Compute genome embeddings first",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Training epochs per phase",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size",
    )
    parser.add_argument(
        "--latent-dim",
        type=int,
        default=32,
        help="VAE latent dimension",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=1.0,
        help="KL weight (beta-VAE)",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )

    args = parser.parse_args()

    # ── Step 1: Compute embeddings ────────────────────────
    if args.compute_embeddings:
        log.info("Computing genome embeddings with method: %s", args.embedding_method)
        n_computed = compute_all_genome_embeddings(method=args.embedding_method)
        log.info("Computed %d new embeddings", n_computed)

    # ── Step 2: Build dataset ────────────────────────────
    try:
        if args.all_organisms:
            log.info("Building dataset for all organisms...")
            dataset = build_genome_media_dataset(
                embedding_method=args.embedding_method,
                organism_type=None,
            )
        elif args.organism:
            log.info("Building dataset for organism type: %s", args.organism)
            dataset = build_genome_media_dataset(
                embedding_method=args.embedding_method,
                organism_type=args.organism,
            )
        else:
            # Default to bacteria
            log.info("Building dataset for bacteria (default)...")
            dataset = build_genome_media_dataset(
                embedding_method=args.embedding_method,
                organism_type="bacteria",
            )

        log.info(
            "Dataset built: %d train, %d val, %d test samples",
            len(dataset["X_train"]),
            len(dataset["X_val"]),
            len(dataset["X_test"]),
        )

    except Exception as e:
        log.error("Failed to build dataset: %s", e)
        return 1

    # ── Step 3: Train CVAE ───────────────────────────────
    try:
        curriculum_phases = ["bacteria", "archea", "fungi", "protist"] if args.all_organisms else []

        cfg = TrainConfig(
            model_type="cvae",
            epochs=args.epochs,
            batch_size=args.batch_size,
            latent_dim=args.latent_dim,
            beta=args.beta,
            lr=args.lr,
            seed=args.seed,
            curriculum_phases=curriculum_phases,
            embedding_method=args.embedding_method,
        )

        result = train(cfg)

        log.info("Training complete!")
        log.info("Model saved to: %s", result["save_path"])
        log.info("Metrics: %s", result["metrics"])

        return 0

    except Exception as e:
        log.error("Training failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
