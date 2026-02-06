# MediaDive-NCBI Integration Guide

**Complete guide to linking your existing MediaDive data with NCBI genomes to build training datasets for the Conditional VAE.**

---

## Overview

This guide explains the three-phase integration process:

1. **Link**: Match MediaDive species to NCBI reference genomes
2. **Propagate**: Copy growth observations to genome level with confidence scoring
3. **Build**: Create composite JSON dataset for CVAE training

### What You Get

Combining MediaDive with NCBI creates rich training data:

| Source | Data | Contribution |
|--------|------|--------------|
| **MediaDive** | 5K-10K strains, media formulations, growth observations | Ground truth labels, media composition |
| **NCBI** | 4K-12K reference genomes, k-mer embeddings, metadata | Genomic representation, organism diversity |
| **Combined** | 10K-50K+ training pairs | Complete (genome_embedding, media, label) tuples |

### Example Training Pair

```json
{
  "genome_id": "GCF_000005845.2",
  "species": "Escherichia coli K-12",
  "media_name": "Luria Broth",
  "growth": true,
  "confidence": 0.95,
  "organism_type": "bacteria",
  "ingredients": "peptone(10g/L); beef_extract(5g/L); NaCl(10g/L)"
}
```

---

## Quick Start (3 Commands)

```bash
# Step 1: Link species to NCBI genomes
make integrate-link-species

# Step 2: Propagate growth data
make integrate-propagate

# Step 3: Build dataset
make integrate-stats

# Or all at once:
make integrate-mediadive-ncbi
```

**Time**: 10-30 minutes  
**Result**: 10K-50K training pairs ready for CVAE

---

## Detailed Process

### Phase 1: Link MediaDive Species to NCBI Genomes

**What happens:**
1. Extracts unique species from MediaDive `strains` table
2. Searches NCBI Assembly database for reference genomes
3. Filters for high-quality genomes (RefSeq category)
4. Stores in `genomes` table with foreign key to strains

**Python API:**

```python
from src.ingest.link_mediadive_to_genomes import (
    extract_mediadive_species,
    link_mediadive_species_to_ncbi,
)

# Get species
species_list = extract_mediadive_species()
# → Returns: [{"species": "E. coli", "domain": "bacteria", "count": 150}, ...]

# Link each species
for sp in species_list[:100]:  # First 100 species
    found, linked = link_mediadive_species_to_ncbi(
        sp['species'],
        domain=sp['domain'],
        max_results=3  # Up to 3 genomes per species
    )
    print(f"{sp['species']}: linked {linked}/{found}")
```

**SQL Result:**
```sql
SELECT organism_type, COUNT(*) FROM genomes GROUP BY organism_type;
-- bacteria:    3000
-- archaea:     500
-- fungi:       800
-- protists:    200
-- TOTAL:       4500
```

**Performance:**
- Bacteria: 5-10 min (largest group)
- Fungi/Archaea: 5 min
- Protists: 2 min
- **Total**: 10-15 min

---

### Phase 2: Propagate Growth Data to Genomes

**What happens:**
1. For each strain with linked genomes
2. Copies all `strain_growth` observations to `genome_growth`
3. Applies confidence scores based on data quality
4. Tracks source as 'mediadive'

**Confidence Mapping:**
```
growth_quality='excellent' → confidence=0.95
growth_quality='good'      → confidence=0.85
growth_quality='fair'      → confidence=0.70
growth_quality='poor'      → confidence=0.50
(default)                  → confidence=0.75
```

**Python API:**

```python
from src.ingest.link_mediadive_to_genomes import propagate_growth_data_to_genomes

count = propagate_growth_data_to_genomes()
print(f"Propagated {count} observations")
# → Propagated 25000 observations
```

**SQL Result:**
```sql
SELECT COUNT(*) FROM genome_growth WHERE growth=1;
-- 20000 (positive growth)

SELECT COUNT(*) FROM genome_growth WHERE growth=0;
-- 5000 (negative/no growth)

SELECT AVG(confidence) FROM genome_growth;
-- 0.82 (average confidence)
```

**Performance:**
- Small database (<1K genomes): <5 sec
- Medium database (5K-10K): 1-5 min
- Large database (50K+): 10-30 min

---

### Phase 3: Build Composite Dataset

**What happens:**
1. Loads genome embeddings (k-mer profiles)
2. Loads media compositions (ingredient vectors)
3. Combines with growth labels + metadata
4. Exports to JSON for training

**Python API:**

```python
from src.ingest.link_mediadive_to_genomes import (
    extract_rich_dataset_features,
    create_composite_training_dataset,
)

# Extract features
features = extract_rich_dataset_features()
print(f"Samples: {features['record_count']}")
print(f"Organisms: {set(features['organism_types'])}")

# Create dataset file
dataset_path = create_composite_training_dataset()
print(f"Saved to: {dataset_path}")
# → Saved to: data/processed/mediadive_ncbi_integrated_dataset.json

# Inspect
import json
with open(dataset_path) as f:
    data = json.load(f)

print(f"Total pairs: {len(data['pairs'])}")
for pair in data['pairs'][:3]:
    print(f"  {pair['species']:30} → {pair['media_name']:20}")
```

**Dataset JSON Structure:**
```json
{
  "metadata": {
    "created": "2024-...",
    "total_pairs": 25000,
    "organism_types": ["bacteria", "archaea", "fungi", "protists"],
    "media_count": 120,
    "confidence_stats": {...}
  },
  "pairs": [
    {
      "genome_id": "GCF_000005845.2",
      "species": "Escherichia coli K-12",
      "media_id": "48",
      "media_name": "Luria Broth",
      "growth": true,
      "confidence": 0.95,
      "organism_type": "bacteria",
      "genome_gc_content": 50.8,
      "ingredients": "peptone(10g/L);..."
    },
    ...
  ]
}
```

---

## Expected Results

### Data Volumes

| Metric | Typical Range |
|--------|---------------|
| Strains linked | 3,000-7,000 (60-70% coverage) |
| Genomes linked | 4,000-12,000 (1-3 per species) |
| Training pairs | 10,000-50,000+ |
| Positive growth | 60-80% |
| Media types | 100-300 unique formulations |
| Database size | 50-500 MB |

### Quality Metrics

**Coverage by organism type:**
```
Bacteria:     25,000 pairs (80%)
Archaea:      3,000 pairs  (10%)
Fungi:        2,000 pairs  (8%)
Protists:     500 pairs    (2%)
```

**Confidence distribution:**
```
High (0.85-1.0):    70%  → Direct MediaDive observations
Medium (0.70-0.84): 20%  → Fair/good quality
Lower (0.50-0.69):  10%  → Poor quality or rare organisms
```

---

## Customization

### Link with Custom Parameters

```bash
# Limit to first 10 species, 5 genomes each
python -m scripts.integrate_mediadive_ncbi \
    --link-species \
    --limit-species 10 \
    --max-per-species 5

# Dry run (preview without executing)
python -m scripts.integrate_mediadive_ncbi \
    --link-species \
    --dry-run
```

### Generate Statistics Report

```bash
# View in console
make integrate-stats --verbose

# Save to file
python -m scripts.integrate_mediadive_ncbi \
    --stats \
    --save-report report.txt

# View file
cat report.txt
```

### Inspect Data with SQL

```sql
-- Count genomes by organism
SELECT organism_type, COUNT(*) FROM genomes GROUP BY organism_type;

-- Growth distribution
SELECT growth, COUNT(*) FROM genome_growth GROUP BY growth;

-- Average confidence by source
SELECT source, AVG(confidence) FROM genome_growth GROUP BY source;

-- Media coverage
SELECT COUNT(DISTINCT media_id) FROM genome_growth;
```

---

## Using the Dataset for Training

### Load and Explore

```python
import json
import pandas as pd

# Load dataset
with open('data/processed/mediadive_ncbi_integrated_dataset.json') as f:
    data = json.load(f)

pairs = data['pairs']
df = pd.DataFrame(pairs)

# Statistics
print(f"Organisms: {df['organism_type'].nunique()}")
print(f"Growth: {df['growth'].mean():.1%} positive")
print(f"Confidence: {df['confidence'].mean():.2f} avg")
```

### Build Training/Test Split

```python
from sklearn.model_selection import train_test_split

# Split by organism type (for curriculum learning)
train_pairs = [p for p in pairs if p['organism_type'] in ['bacteria', 'archaea']]
test_pairs = [p for p in pairs if p['organism_type'] in ['fungi', 'protists']]

print(f"Train: {len(train_pairs)}, Test: {len(test_pairs)}")
```

### Create Training Batches

```python
import numpy as np

# Load genome embeddings and media compositions (from database)
# Then create batches for CVAE

for pair in pairs:
    genome_id = pair['genome_id']
    media_id = pair['media_id']
    
    # Get embeddings from database
    genome_emb = get_genome_embedding(genome_id)     # 128-dim
    media_comp = get_media_composition(media_id)     # 100-dim
    
    # Combine
    x = np.concatenate([genome_emb, media_comp])  # 228-dim
    y = pair['growth']  # Binary label
    
    # Use for training
```

---

## Troubleshooting

### No species found

**Problem**: `extract_mediadive_species()` returns empty list

**Solution:**
1. Check MediaDive data exists: `SELECT COUNT(*) FROM strains;`
2. Check species column is populated: `SELECT COUNT(DISTINCT species) FROM strains WHERE species IS NOT NULL;`
3. Run `make ingest` if strains missing

### NCBI rate limit exceeded

**Problem**: API returns 429 error

**Solutions:**
1. Add API key to .env: `NCBI_API_KEY=your_key` (10x higher limit)
2. Retry later (built-in auto-retry with backoff)
3. Run during off-peak hours

### Genomes linked but no growth data

**Problem**: `genome_growth` table is empty after propagation

**Solutions:**
1. Check genomes are linked: `SELECT COUNT(*) FROM genomes WHERE strain_id IS NOT NULL;`
2. Verify growth data: `SELECT COUNT(*) FROM strain_growth;`
3. Check foreign key constraints: `PRAGMA foreign_key_check;`

### Low confidence scores

**Normal if** many observations are lower quality. **Solution**: Filter in training with confidence threshold

```sql
SELECT * FROM genome_growth WHERE confidence >= 0.85;
```

---

## Performance Tips

| Task | Time | Optimization |
|------|------|--------------|
| Link species | 10-15 min | Already optimized |
| Propagate | 5-30 min | Reduce if many species |
| Build dataset | 2-5 min | Already fast |
| Total | 20-50 min | Use `--limit-species` for testing |

**For faster development:**
```bash
# Test with first 10 species only
python -m scripts.integrate_mediadive_ncbi --link-species --limit-species 10
```

---

## Next Steps

1. **Run integration**: `make integrate-mediadive-ncbi`
2. **Check results**: `make integrate-stats`
3. **Build features**: `make features`
4. **Train CVAE**: `make train-cvae-all`
5. **Evaluate**: See [guides/cvae_training.md](cvae_training.md)

---

## Related Documentation

- [COMMAND_REFERENCE.md](../COMMAND_REFERENCE.md) - All CLI commands
- [guides/cvae_training.md](cvae_training.md) - Train your model
- [guides/api_reference.md](api_reference.md) - Data source APIs
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Common issues

---

**Status**: Production-ready ✅  
**Last Updated**: 2024  
**Questions?** See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
