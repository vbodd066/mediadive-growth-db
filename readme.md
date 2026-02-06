# MediaDive Growth DB

**ML pipeline for predicting and generating viable microbial growth media from metagenomics data.**

The goal is to build a foundational model that can propose culture media formulations for previously unculturable microbes — using metagenomic signals to determine what key factors (composition, pH, carbon/nitrogen sources, trace elements) are required for successful cultivation.

---

## 🚀 Quick Start (Pick Your Path)

### Path 1: Just Run It (5 min)
```bash
make integrate-mediadive-ncbi  # Link MediaDive to NCBI genomes
make integrate-stats           # View results
make train-cvae-all            # Train model
```

### Path 2: Understand First (30 min)
1. Read: [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) (Path 2)
2. Read: [`docs/guides/mediadive_ncbi_linking.md`](docs/guides/mediadive_ncbi_linking.md)
3. Run commands above

### Path 3: Customize & Deep Dive (1-2 hours)
1. Read: [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) (Path 3)
2. Read: [`docs/guides/`](docs/guides/) for specialized guides
3. Modify and run

---

## 📚 Documentation

**All documentation is in [`docs/`](docs/) folder:**

| Document | Purpose | Time |
|----------|---------|------|
| **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** | Entry point with 3 paths | 5 min |
| **[docs/INDEX.md](docs/INDEX.md)** | Complete navigation hub | 2 min |
| **[docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md)** | All CLI commands & Python API | 10 min |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues & solutions | 5-10 min |
| **[docs/guides/mediadive_ncbi_linking.md](docs/guides/mediadive_ncbi_linking.md)** | Data integration guide | 20 min |
| **[docs/guides/CVAE_GUIDE.md](docs/guides/CVAE_GUIDE.md)** | Model architecture details | 20 min |
| **[docs/guides/api_reference.md](docs/guides/api_reference.md)** | Data source APIs | 20 min |

👉 **New to the project?** Start with [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md)

---

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

## Setup

```bash
# 1. Clone and install
git clone <repo-url> && cd mediadive-growth-db
pip install -e ".[ml,viz,dev]"

# 2. Copy environment config
cp .env.example .env
# Edit .env to add NCBI_EMAIL (required), NCBI_API_KEY (optional)

# 3. Initialize database
make init-db
```

## Available Pipelines

### MediaDive-NCBI Integration (Latest - Recommended)
```bash
# Link MediaDive strains to NCBI genomes, propagate growth data, build dataset
make integrate-mediadive-ncbi

# Check results
make integrate-stats

# Build features and train
make features
make train-cvae-all
```
📖 **Full guide**: [`docs/guides/mediadive_ncbi_linking.md`](docs/guides/mediadive_ncbi_linking.md)

### Multi-organism Ingestion (BacDive, NCBI, PubMed)
```bash
# Ingest all organism types with growth conditions
make ingest-all-organisms

# Or selectively:
make ingest-bacteria-bacdive      # BacDive bacteria
make ingest-fungi-ncbi             # NCBI fungi
make ingest-protists-ncbi          # NCBI protists
```

### Traditional MediaDive Only
```bash
# Ingest media data
make ingest

# Build ML-ready features
make features

# Train models
make train                                          # sklearn baseline
```

## Project Structure

```
mediadive-growth-db/
├── pyproject.toml          # Packaging, deps, tool config
├── Makefile                # Common commands
├── DATA_SOURCES.md         # Guide to BacDive, NCBI, PubMed integration
├── .env.example            # Environment template
│
├── src/
│   ├── config.py           # Centralized configuration
│   ├── api/
│   │   └── client.py       # MediaDive REST client (retries, rate-limiting)
│   ├── db/
│   │   ├── schema.sql      # SQLite schema (extended with genomes, embeddings)
│   │   ├── init_db.py      # DB initialization
│   │   └── queries.py      # Reusable read queries
│   ├── ingest/
│   │   ├── fetch_media.py
│   │   ├── fetch_ingredients.py
│   │   ├── fetch_media_ingredients.py
│   │   ├── fetch_strain_growth.py
│   │   ├── fetch_bacdive.py              # NEW: BacDive API integration
│   │   ├── fetch_ncbi_organisms.py       # NEW: NCBI E-utilities (fungi/protists)
│   │   └── enrich_growth_conditions.py   # NEW: Literature mining + curation
│   ├── features/
│   │   ├── media_vectors.py      # Media → composition vectors
│   │   ├── strain_features.py    # Strain-level features
│   │   ├── genome_features.py    # NEW: K-mer embeddings for genomes
│   │   └── build_dataset.py      # NEW: Genome-media dataset builder
│   ├── models/
│   │   ├── base.py               # Abstract model interface
│   │   ├── growth_predictor.py   # sklearn + neural classifiers
│   │   ├── media_generator.py    # VAE + NEW: ConditionalMediaVAE
│   │   └── evaluate.py           # Metrics & reporting
│   └── training/
│       ├── trainer.py            # Unified training runner
│       └── cloud/
│           └── launch.py         # Modal GPU launcher
│
├── scripts/
│   ├── run_ingest.py              # Full ingestion pipeline
│   ├── build_features.py          # Feature building CLI
│   ├── train.py                   # Training entry point
│   └── ingest_all_organisms.py    # NEW: Multi-source ingest orchestrator
│
├── tests/
│   ├── conftest.py              # Shared fixtures (test DB)
│   ├── test_api_client.py
│   ├── test_db.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_data_integrity.py   # Post-ingest data validation
│
├── notebooks/
│   ├── mediadive_deep_learning_models.ipynb     # NEW: CVAE training
│   └── top_media_analysis.ipynb                 # EDA & prototyping
│
└── data/
    ├── raw/                # Raw API JSON + genome data
    │   ├── media/
    │   ├── ingredients/
    │   ├── bacdive/        # NEW: BacDive cache
    │   └── strains/
    ├── interim/            # Intermediate processing
    ├── processed/          # ML-ready .npy / .parquet
    ├── models/             # Trained model artifacts
    └── releases/           # Dataset releases
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

### Conditional Media VAE (NEW)

**Purpose**: Generate organism-specific growth media by conditioning on genome-derived features.

**Architecture**:
- **Input**: Genome k-mer embeddings (concatenated 4/7/8-mer profiles) + normalized media composition
- **Encoder**: Maps (genome, media) → latent distribution q(z|genome, media)
- **Decoder**: Maps latent z + genome → media reconstruction
- **Conditioning**: Genome embeddings injected at encoder input and decoder output for fine-grained control

**Training Strategy**: Curriculum learning
```
Phase 1: Bacteria (30K strains from BacDive)
    ↓ (evaluate per-organism accuracy)
Phase 2: Archaea (add thermophiles, halophiles)
    ↓
Phase 3: Fungi (Saccharomyces, Aspergillus, Candida)
    ↓
Phase 4: Protists (Tetrahymena, Paramecium)
```

**Features**:
- Multi-organism training reduces overfitting to bacterial genomes
- Curriculum prevents optimization collapse on rare organisms
- Enables zero-shot media prediction for novel organisms

**Module**: [src/models/media_generator.py](src/models/media_generator.py) → `ConditionalMediaVAE` class

## Roadmap

- [x] Data ingestion from MediaDive REST API
- [x] SQLite storage with structured schema
- [x] Feature engineering pipeline (composition matrices, strain features)
- [x] Growth prediction models (sklearn + neural)
- [x] Media generation model (VAE)
- [x] Test suite (unit + integration + data integrity)
- [x] Cloud training support (Modal)
- [x] **BacDive API integration** (bacterial culturomics, 30K+ strains)
- [x] **NCBI E-utilities integration** (fungal & protist genomes)
- [x] **Growth condition enrichment** (taxonomy inference + literature mining)
- [x] **Conditional VAE with genome embeddings**
- [x] **Multi-organism training pipeline** (curriculum learning)
- [x] **Genome feature extraction** (k-mer embeddings)
- [ ] EDA notebooks (in progress)
- [ ] Hyperparameter sweep (Optuna / W&B Sweeps)
- [ ] Transformer-based sequence model for media recipes
- [ ] Wet-lab validation loop
- [ ] Active learning feedback from experimental results
- [ ] Zero-shot media prediction for uncultured organisms

## Data Sources

This project integrates data from multiple authoritative public databases:

| Database | Organisms | Records | Data |
|----------|-----------|---------|------|
| **BacDive** | Bacteria + Archaea | 30,000+ | Strains, growth conditions, media |
| **NCBI Assembly** | Fungi, Protists, Archaea | 1,000s | Genome metadata, taxonomy |
| **PubMed** | All | — | Growth parameters from literature |
| **MediaDive** | Bacterial | 10,000+ | Growth media formulations |

**See [`docs/guides/api_reference.md`](docs/guides/api_reference.md) for complete API documentation.**

### Setup Instructions

```bash
# 1. NCBI registration (optional, for higher rate limits)
# Create account: https://www.ncbi.nlm.nih.gov/account/
# Get API key: Account Settings → API Key
# Add to .env: NCBI_API_KEY=your_key

# 2. Set your email (required for NCBI)
# Edit .env: NCBI_EMAIL=your.email@example.com

# 3. Run ingestion
make integrate-mediadive-ncbi
```

---

## Verification & Testing

### Verify Integration Works

```bash
# Quick verification script (checks files, imports, Makefile targets)
bash VERIFY_INTEGRATION.sh
```

**What it does**:
- ✅ Checks all required files exist
- ✅ Verifies Makefile targets are defined
- ✅ Tests Python imports work
- ✅ Shows quick start commands

**Is it necessary?** No, optional. Use it to verify the system is set up correctly before running the full pipeline.

### Run Tests

```bash
make test
```

Tests check:
- API client connectivity
- Database schema integrity
- Feature extraction correctness
- Model architectures
- Data ingestion quality
---

## Project Structure

```
mediadive-growth-db/
├── README.md               ← You are here
├── Makefile                ← Common commands
├── pyproject.toml          ← Dependencies
│
├── docs/                   ← 📚 All documentation
│   ├── GETTING_STARTED.md  ← Start here!
│   ├── INDEX.md            ← Navigation hub
│   ├── COMMAND_REFERENCE.md
│   ├── TROUBLESHOOTING.md
│   ├── guides/             ← Detailed guides
│   └── archive/            ← Historical docs
│
├── src/                    ← Source code
│   ├── api/                ← MediaDive API client
│   ├── db/                 ← Database & schema
│   ├── ingest/             ← Data ingestion (MediaDive, BacDive, NCBI)
│   ├── features/           ← Feature engineering
│   ├── models/             ← ML models (CVAE, predictors)
│   └── training/           ← Training pipelines
│
├── scripts/                ← CLI entry points
│   ├── run_ingest.py
│   ├── integrate_mediadive_ncbi.py
│   ├── train_cvae.py
│   └── ingest_all_organisms.py
│
├── notebooks/              ← Jupyter notebooks
│   ├── mediadive_deep_learning_models.ipynb
│   └── top_media_analysis.ipynb
│
├── tests/                  ← Test suite
│   ├── test_api_client.py
│   ├── test_db.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_data_integrity.py
│
└── data/                   ← Data directory
    ├── raw/                ← Raw API cache & genomes
    ├── interim/            ← Intermediate processing
    ├── processed/          ← ML-ready datasets
    ├── models/             ← Trained models
    └── releases/           ← Public releases
```

---

## Common Commands

```bash
# Setup
pip install -e ".[ml,viz,dev]"
make init-db

# Data ingestion
make integrate-mediadive-ncbi          # Latest: link MediaDive to NCBI
make ingest-all-organisms              # Alternative: multi-source ingest
make ingest                            # Legacy: MediaDive only

# Feature engineering
make features
make build-genome-embeddings

# Training
make train-cvae-all                    # Full curriculum learning
make train-cvae --organism bacteria    # Single organism
make train                             # sklearn baseline

# Verification
bash VERIFY_INTEGRATION.sh
make test

# Stats & debugging
make integrate-stats
make integrate-stats --verbose
```

👉 **Full reference**: [`docs/COMMAND_REFERENCE.md`](docs/COMMAND_REFERENCE.md)

---

## Getting Help

| Need | Resource |
|------|----------|
| **Getting started** | [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) |
| **All commands** | [`docs/COMMAND_REFERENCE.md`](docs/COMMAND_REFERENCE.md) |
| **Stuck?** | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) |
| **Full navigation** | [`docs/INDEX.md`](docs/INDEX.md) |
| **Integration guide** | [`docs/guides/mediadive_ncbi_linking.md`](docs/guides/mediadive_ncbi_linking.md) |
| **API reference** | [`docs/guides/api_reference.md`](docs/guides/api_reference.md) |
| **CVAE details** | [`docs/guides/CVAE_GUIDE.md`](docs/guides/CVAE_GUIDE.md) |

---

## Roadmap

- [x] Data ingestion from MediaDive REST API
- [x] SQLite storage with structured schema
- [x] Feature engineering pipeline (composition matrices, strain features)
- [x] Growth prediction models (sklearn + neural)
- [x] Media generation model (VAE)
- [x] Test suite (unit + integration + data integrity)
- [x] Cloud training support (Modal)
- [x] **BacDive API integration** (bacterial culturomics, 30K+ strains)
- [x] **NCBI E-utilities integration** (fungal & protist genomes)
- [x] **Growth condition enrichment** (taxonomy inference + literature mining)
- [x] **Conditional VAE with genome embeddings**
- [x] **Multi-organism training pipeline** (curriculum learning)
- [x] **Genome feature extraction** (k-mer embeddings)
- [x] **MediaDive-NCBI integration** (link + propagate + dataset)
- [ ] EDA notebooks (in progress)
- [ ] Hyperparameter sweep (Optuna / W&B Sweeps)
- [ ] Transformer-based sequence model for media recipes
- [ ] Wet-lab validation loop
- [ ] Active learning feedback from experimental results
- [ ] Zero-shot media prediction for uncultured organisms

---

**Status**: ✅ Production Ready  
**Last Updated**: 2024  
**Questions?** Start with [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) or [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)