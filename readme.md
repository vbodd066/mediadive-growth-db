# MediaDive Growth DB

**ML pipeline for predicting and generating viable microbial growth media from metagenomics data.**

The goal is to build a foundational model that can propose culture media formulations for previously unculturable microbes — using metagenomic signals to determine what key factors (composition, pH, carbon/nitrogen sources, trace elements) are required for successful cultivation.

## Architecture

```
Data Layer          ML Layer              Research Layer
───────────         ────────              ──────────────
MediaDive API  →  Feature Engineering  →  Notebooks / EDA
    ↓                   ↓
SQLite DB         Processed Datasets
                        ↓
                  Model Training
                  ├── Growth Predictor (sklearn / neural)
                  └── Media Generator (VAE)
                        ↓
                  Evaluation & Analysis
```

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd mediadive-growth-db
pip install -e ".[ml,viz,dev]"

# 2. Copy environment config
cp .env.example .env

# 3. Ingest data from MediaDive API
make ingest

# 4. Build ML-ready features
make features

# 5. Train a model
make train                                          # sklearn baseline
python -m scripts.train --model neural --epochs 50  # neural net
python -m scripts.train --model vae --epochs 200    # generative VAE

# 6. Run tests
make test
```

## Project Structure

```
mediadive-growth-db/
├── pyproject.toml          # Packaging, deps, tool config
├── Makefile                # Common commands
├── .env.example            # Environment template
│
├── src/
│   ├── config.py           # Centralized configuration
│   ├── api/
│   │   └── client.py       # MediaDive REST client (retries, rate-limiting)
│   ├── db/
│   │   ├── schema.sql      # SQLite schema
│   │   ├── init_db.py      # DB initialization
│   │   └── queries.py      # Reusable read queries
│   ├── ingest/
│   │   ├── fetch_media.py
│   │   ├── fetch_ingredients.py
│   │   ├── fetch_media_ingredients.py
│   │   └── fetch_strain_growth.py
│   ├── features/
│   │   ├── media_vectors.py      # Media → composition vectors
│   │   ├── strain_features.py    # Strain-level features
│   │   └── build_dataset.py      # Assemble train/val/test splits
│   ├── models/
│   │   ├── base.py               # Abstract model interface
│   │   ├── growth_predictor.py   # sklearn + neural classifiers
│   │   ├── media_generator.py    # VAE for novel media generation
│   │   └── evaluate.py           # Metrics & reporting
│   └── training/
│       ├── trainer.py            # Unified training runner
│       └── cloud/
│           └── launch.py         # Modal GPU launcher
│
├── scripts/
│   ├── run_ingest.py       # Full ingestion pipeline
│   ├── build_features.py   # Feature building CLI
│   └── train.py            # Training entry point
│
├── tests/
│   ├── conftest.py              # Shared fixtures (test DB)
│   ├── test_api_client.py
│   ├── test_db.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_data_integrity.py   # Post-ingest data validation
│
├── notebooks/                    # EDA & prototyping (future)
└── data/
    ├── raw/                # Raw API JSON snapshots
    ├── interim/            # Intermediate processing
    ├── processed/          # ML-ready .npy / .parquet
    └── models/             # Trained model artifacts
```

## Models

### Growth Predictor (Classification)
Given a media composition vector → predict whether a strain will grow (binary).

- **Tier 1**: Gradient Boosted Trees via sklearn (fast iteration, strong baseline)
- **Tier 2**: Feed-forward neural network with BatchNorm + Dropout (extensible to multi-modal inputs)

### Media Generator (VAE)
Learn a smooth latent space over viable media compositions, then sample novel formulations.

- **Phase 1**: Unconditional VAE over composition vectors
- **Phase 2**: Conditional VAE — condition on strain taxonomy
- **Phase 3**: Condition on metagenomic embeddings (the endgame)

## Roadmap

- [x] Data ingestion from MediaDive REST API
- [x] SQLite storage with structured schema
- [x] Feature engineering pipeline (composition matrices, strain features)
- [x] Growth prediction models (sklearn + neural)
- [x] Media generation model (VAE)
- [x] Test suite (unit + integration + data integrity)
- [x] Cloud training support (Modal)
- [ ] EDA notebooks
- [ ] Hyperparameter sweep (Optuna / W&B Sweeps)
- [ ] Metagenomic feature integration
- [ ] Conditional VAE with strain embeddings
- [ ] Transformer-based sequence model for media recipes
- [ ] Wet-lab validation loop

## Data Source

[MediaDive](https://mediadive.dsmz.de/) — a comprehensive database of microbial growth media maintained by DSMZ (German Collection of Microorganisms and Cell Cultures).
