# Conditional VAE for Microbial Media Generation

## Overview

The **Conditional Variational Autoencoder (CVAE)** is a significant upgrade to the MediaDive system that enables **organism-aware media generation**. Instead of learning generic media compositions, the CVAE learns to generate viable culture media *conditioned* on genomic features of the target organism.

### Key Innovation

**Traditional VAE:** media → latent space → media (learns average, generic media)

**CVAE (this system):** (media, genome_embedding) → latent space → media (learns organism-specific preferences)

This allows the model to:
- Propose specialized media for bacteria
- Adapt to metabolic characteristics of archea
- Generate different formulations for fungi vs. protists
- Support curriculum learning to gradually introduce organism diversity

---

## Architecture

### Conditional VAE Design

```
                    ENCODER                           DECODER
                    ───────                           ───────

Input: media_composition (m)              |          latent (z) + genome_embedding (g)
       genome_embedding (g)               |               ↓
                                          |    [Linear(32 + 256 → 128)]
       [Concatenate: m + g]               |               ↓
              ↓                           |    [ReLU, BatchNorm]
       [Linear(X + 256 → 256)]            |               ↓
              ↓                           |    [Linear(128 → 64)]
       [ReLU, BatchNorm]                  |               ↓
              ↓                           |    [ReLU, BatchNorm]
       [Linear(256 → 128)]                |               ↓
              ↓                           |    [Linear(64 → X)]
       [ReLU, BatchNorm]                  |               ↓
              ↓                           |    [ReLU] (non-negative concentrations)
       [Linear(128 → h)]                  |               ↓
              ↓                    +---+  |   reconstructed media
    ┌─────────────────────────┐  |   |  |
    │  μ (mean)    σ (logvar) │  │ z │  │
    │  (32-dim)    (32-dim)   │  │ ~ │  |
    └─────────────────────────┘  | N │  │
                                 │(0,1)│ │
                                 +---+  │
```

### Key Components

1. **Encoder**: Compresses (media, genome) pairs to latent distribution
2. **Latent Space**: 32-dimensional learned representations
3. **Decoder**: Reconstructs media from latent + genome conditioning
4. **Reparameterization Trick**: Enables backprop through stochastic sampling
5. **Beta-VAE**: Weighted KL divergence term for latent space quality

---

## Data Pipeline

### Step 1: Genome Ingestion

```python
from src.ingest.fetch_genomes import store_genome_metadata, store_genome_growth_observation

# Add a bacterial genome
store_genome_metadata(
    genome_id="GCF_000005845.2",
    organism_name="Escherichia coli str. K-12 substr. MG1655",
    organism_type="bacteria",
    taxid=511145,
    gc_content=50.8,
    sequence_length=4641652,
    strain_id=12345
)

# Record growth observation
store_genome_growth_observation(
    genome_id="GCF_000005845.2",
    media_id="48",  # LB medium
    growth=True,
    confidence=0.95,
    source="literature"
)
```

**Genome Storage Structure:**
```
data/raw/
├── genomes/
│   ├── bacteria/
│   │   ├── GCF_000005845.2.fasta
│   │   └── GCF_000006945.1.fasta
│   ├── archea/
│   │   └── GCF_001715635.1.fasta
│   └── fungi/
│       └── GCF_000146045.2.fasta
└── genomes_metadata/
    ├── GCF_000005845.2.json
    └── ...
```

### Step 2: Genome Embedding Extraction

Compute k-mer profiles or other genomic features:

```python
from src.features.genome_features import compute_all_genome_embeddings

# Compute 128-dim k-mer embeddings for all genomes
n_computed = compute_all_genome_embeddings(method="kmer_128")
print(f"Computed {n_computed} embeddings")
```

**Supported Embedding Methods:**

| Method | Dimension | Characteristics |
|--------|-----------|-----------------|
| `kmer_64` | 256 | 4-mers normalized frequencies |
| `kmer_128` | 4096 | 7-mers normalized frequencies |
| `kmer_256` | 65536 | 8-mers normalized frequencies |
| `stats` | 4 | [GC%, AT%, log_length, N_count] |

**K-mer Approach Benefits:**
- Computationally efficient (no external ML models needed)
- Captures sequence composition bias
- Organism-specific signature
- Works without annotation

### Step 3: Dataset Building

Create (genome, media) training pairs:

```python
from src.features.build_dataset import build_genome_media_dataset

# Build dataset for bacteria
dataset = build_genome_media_dataset(
    embedding_method="kmer_128",
    organism_type="bacteria",  # or None for all
    test_size=0.15,
    val_size=0.15,
    seed=42,
    save=True  # Saves to data/processed/genome_media_cvae/
)

print(f"Training samples: {len(dataset['X_train'])}")
print(f"Media dim: {dataset['X_train'].shape[1]}")
print(f"Genome embedding dim: {dataset['C_train'].shape[1]}")
```

**Output Structure:**
```
data/processed/genome_media_cvae/
├── X_train.npy  # Media compositions (N_train, 256)
├── X_val.npy    # Media compositions (N_val, 256)
├── X_test.npy   # Media compositions (N_test, 256)
├── C_train.npy  # Genome embeddings (N_train, 4096)
├── C_val.npy    # Genome embeddings (N_val, 4096)
├── C_test.npy   # Genome embeddings (N_test, 4096)
├── y_train.npy  # Organism type (priority encoded)
├── y_val.npy
├── y_test.npy
└── samples.parquet  # Metadata
```

---

## Training

### Basic CVAE Training

```python
from src.training.trainer import TrainConfig, train

cfg = TrainConfig(
    model_type="cvae",
    epochs=100,
    batch_size=64,
    latent_dim=32,
    beta=1.0,  # KL weight
    lr=1e-3,
    curriculum_phases=["bacteria"],  # Just train on bacteria
)

result = train(cfg)
print(f"Training time: {result['elapsed_seconds']:.1f}s")
print(f"Model saved: {result['save_path']}")
```

### Curriculum Learning (Multi-Organism)

Train on progressively harder organism types:

```bash
# Train on bacteria first, then expand to archea, fungi
make train-cvae-all
```

Or programmatically:

```python
cfg = TrainConfig(
    model_type="cvae",
    epochs=100,
    batch_size=64,
    curriculum_phases=["bacteria", "archea", "fungi", "protist"],
)

result = train(cfg)
```

**Why Curriculum Learning?**
- Bacteria have well-characterized media → easier to learn
- Archea have different metabolic requirements → harder
- Gradual introduction prevents catastrophic forgetting
- Model learns to differentiate organism types
- Better generalization to novel organisms

### Training Monitoring

```
Epoch   1/100  loss=0.8234  recon=0.6123  kl=0.2111 [bacteria]
Epoch  20/100  loss=0.2156  recon=0.1876  kl=0.0280 [bacteria]
Epoch 100/100  loss=0.0845  recon=0.0731  kl=0.0114 [bacteria]
```

**Metrics:**
- **train_loss**: Total loss (reconstruction + β × KL)
- **recon_loss**: MSE between original and reconstructed media
- **kl_loss**: KL divergence regularization

---

## Media Generation

### Single Organism Generation

Generate novel media for a specific organism:

```python
import numpy as np
from src.models.media_generator import ConditionalMediaVAE
from src.features.genome_features import load_genome_embedding

# Load trained model
model = ConditionalMediaVAE.load("data/models/conditional_media_vae.pt")

# Get genome embedding
genome_emb = load_genome_embedding(
    genome_id="GCF_000005845.2",  # E. coli
    method="kmer_128"
)

# Generate 10 novel media formulations
novel_media = model.generate(
    n_samples=10,
    condition=genome_emb.reshape(1, -1)  # (1, 4096)
)
# novel_media shape: (10, 256) - 10 media compositions

# Convert back to readable format (ingredient concentrations)
from src.features.media_vectors import get_ingredient_names
ingredients = get_ingredient_names()
for i, media in enumerate(novel_media):
    print(f"Media {i+1}:")
    for ing_idx, conc in enumerate(media):
        if conc > 0.01:  # Only show significant concentrations
            print(f"  {ingredients[ing_idx]}: {conc:.4f} g/L")
```

### Organism-Adaptive Generation

Generate media that works across multiple organism types:

```python
# Average embeddings of archea genomes
archea_embeddings = [
    load_genome_embedding(gid, "kmer_128")
    for gid in archea_genome_ids
]
archea_avg = np.mean(archea_embeddings, axis=0)

# Generate media for archeal growth
archeal_media = model.generate(
    n_samples=5,
    condition=archea_avg.reshape(1, -1)
)

# These should contain more salt, different pH, etc.
```

### Interpolation Between Organisms

Smoothly transition media between organism types:

```python
bact_emb = load_genome_embedding("GCF_000005845.2", "kmer_128")
arch_emb = load_genome_embedding("GCF_001715635.1", "kmer_128")

# Interpolate in genome embedding space
for alpha in np.linspace(0, 1, 5):
    blended_emb = (1 - alpha) * bact_emb + alpha * arch_emb
    media = model.generate(1, blended_emb.reshape(1, -1))
    print(f"α={alpha:.2f}: Media = {media[0][:5]}...")
```

---

## Inference & Validation

### Reconstruction Fidelity

Evaluate how well the CVAE reconstructs known media:

```python
from src.models.evaluate import reconstruction_metrics

# Reconstruct test set
X_test = np.load("data/processed/genome_media_cvae/X_test.npy")
C_test = np.load("data/processed/genome_media_cvae/C_test.npy")

recon = model.predict(X_test, C_test)
metrics = reconstruction_metrics(X_test, recon)

print(f"MSE: {metrics['mse']:.6f}")
print(f"Pearson correlation: {metrics['pearson_r']:.4f}")
print(f"Ingredient match: {metrics['ingredient_match_pct']:.1f}%")
```

### Latent Space Visualization

Explore learned latent representations:

```python
# Encode test samples
latent = model.encode(X_test, C_test)  # (N_test, 32)

# PCA to 2D for visualization
from sklearn.decomposition import PCA
pca = PCA(n_components=2)
latent_2d = pca.fit_transform(latent)

import matplotlib.pyplot as plt
plt.scatter(latent_2d[:, 0], latent_2d[:, 1], c=y_test, cmap='tab10')
plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%})")
plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%})")
plt.colorbar(label="Organism Type")
plt.savefig("latent_space.png")
```

---

## Database Schema

### New Tables

```sql
-- Genomic sequences
CREATE TABLE genomes (
    genome_id TEXT PRIMARY KEY,
    organism_name TEXT NOT NULL,
    organism_type TEXT NOT NULL,  -- bacteria|archea|fungi|protist|virus
    taxid INTEGER,
    gc_content REAL,
    sequence_length INTEGER,
    fasta_path TEXT,
    fasta_hash TEXT
);

-- Pre-computed genome embeddings
CREATE TABLE genome_embeddings (
    genome_id TEXT PRIMARY KEY,
    embedding_model TEXT NOT NULL,  -- kmer_128|kmer_256|stats
    embedding BLOB,  -- pickled numpy array
    embedding_dim INTEGER
);

-- Growth observations linked to genomes
CREATE TABLE genome_growth (
    genome_id TEXT NOT NULL,
    media_id TEXT NOT NULL,
    growth BOOLEAN,
    confidence REAL,
    source TEXT,
    PRIMARY KEY (genome_id, media_id)
);
```

---

## Command Reference

### Data Preparation

```bash
# Initialize database with genome tables
python -m src.db.init_db

# Compute genome embeddings
make build-genome-embeddings

# Build CVAE dataset
python -m scripts.train_cvae --organism bacteria --compute-embeddings
```

### Training

```bash
# Train on bacteria only
make train-cvae

# Train with curriculum learning (all organism types)
make train-cvae-all

# Custom training
python -m scripts.train_cvae \
    --organism archea \
    --embedding-method kmer_256 \
    --epochs 150 \
    --batch-size 32 \
    --latent-dim 64 \
    --beta 0.5
```

### Evaluation

```bash
# Run tests
make test

# Type checking
make typecheck

# Linting
make lint
```

---

## Future Extensions

### 1. **Pre-trained Embeddings**
Instead of k-mers, use:
- ESM (language models for proteins)
- ProtTrans (attention-based transformers)
- Nucleotide transformers

### 2. **Hierarchical CVAE**
- Learn strain-level hierarchy
- Condition on both genome + strain phenotype
- Multi-level latent factors

### 3. **Growth Prediction**
- Add growth classifier branch to CVAE
- Predict success probability of generated media
- Reward signal for valid compositions

### 4. **Interpretability**
- Attention mechanisms over ingredient types
- Saliency maps showing which genome regions matter
- Latent factor decomposition

### 5. **Experimental Validation**
- Wet-lab testing pipeline
- Active learning with experimental feedback
- Model uncertainty quantification (MC dropout)

---

## Performance Tips

1. **Embedding Dimension**: Use `kmer_128` (~4096-dim) for good balance; `kmer_256` for higher capacity
2. **Latent Dimension**: Start with 32; increase to 64 for more complex media
3. **Beta**: Start at 1.0; increase to 2-5 if KL is negligible
4. **Learning Rate**: 1e-3 works well; reduce to 5e-4 if unstable
5. **Batch Size**: 64 is good; use 32 for limited memory, 128 for fast training
6. **Curriculum**: Always train bacteria first (most data), then gradually introduce harder types

---

## Troubleshooting

### Problem: KL loss too high (>0.5 after epoch 100)

**Cause**: β-VAE coefficient too low, latent space not being used

**Solution**: Increase `beta` to 2.0 or higher

### Problem: Reconstruction loss plateauing

**Cause**: Model capacity too low or learning rate too high

**Solution**: 
- Increase `hidden_dims` to `[512, 256]`
- Decrease learning rate to 5e-4
- Increase `latent_dim` to 64

### Problem: Out of memory

**Cause**: Batch size too large or embeddings too high-dimensional

**Solution**:
- Reduce `batch_size` to 32
- Use `kmer_64` instead of `kmer_256`
- Run on GPU: `torch.cuda.set_device(0)`

### Problem: Generated media unrealistic

**Cause**: Model overfitting or insufficient training data

**Solution**:
- Increase training epochs
- Add more genomes to training set
- Increase β to encourage latent regularization
- Use curriculum learning for better generalization
