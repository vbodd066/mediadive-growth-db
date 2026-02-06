# MediaDive-NCBI Integration Guide

## Overview

This guide explains how to leverage existing MediaDive strain data with NCBI genomes to build a rich, multi-modal training dataset for the Conditional VAE.

### What You Get

By integrating MediaDive with NCBI, you create training data that combines:

| Source | Data | Value |
|--------|------|-------|
| **MediaDive** | Strain species, media formulations, ingredients, growth conditions (temp, pH) | Growth ground truth, media composition |
| **NCBI** | Reference genomes, k-mer embeddings, GC content, sequence statistics | Genomic representation, organism signatures |
| **Combined** | (genome_embedding, media_composition, growth_label) triples | End-to-end CVAE training pairs |

### Example Dataset Entry

```json
{
  "genome_id": "GCF_000005845.2",
  "species": "Escherichia coli K-12",
  "strain_ccno": "K-12 substr. MG1655",
  "media_id": "48",
  "media_name": "Luria Broth (LB)",
  "pH_min": 6.5,
  "pH_max": 8.0,
  "growth": true,
  "confidence": 0.95,
  "organism_type": "bacteria",
  "genome_gc_content": 50.8,
  "genome_length": 4641652,
  "ingredients": "peptone(10g/L); beef_extract(5g/L); NaCl(10g/L)",
  "ingredient_count": 3
}
```

---

## Quick Start

### 1. Prerequisites

Ensure you have:
- ✅ Existing MediaDive data ingested (from earlier iterations)
- ✅ Database with strains, strain_growth, media, ingredients tables populated
- ✅ NCBI credentials configured in `.env`:

```bash
NCBI_EMAIL=your.email@example.com        # Required
NCBI_API_KEY=your_api_key               # Optional (recommended)
```

### 2. Full Integration Pipeline

```bash
# One command to do everything
make integrate-mediadive-ncbi

# Or step-by-step:
make integrate-link-species      # Link to NCBI genomes
make integrate-propagate         # Propagate growth data
make integrate-stats --verbose   # View results
```

### 3. View Results

```bash
# Statistics dashboard
make integrate-stats

# Or detailed analysis
python -c """
from src.ingest.link_mediadive_to_genomes import get_linked_dataset_stats
import json
stats = get_linked_dataset_stats()
print(json.dumps(stats, indent=2))
"""
```

---

## Detailed Pipeline

### Phase 1: Link MediaDive Species to NCBI

```python
from src.ingest.link_mediadive_to_genomes import (
    extract_mediadive_species,
    link_mediadive_species_to_ncbi,
)

# Get unique species from MediaDive
species_list = extract_mediadive_species()

for species in species_list:
    print(f"{species['species']}: {species['count']} strains")
    
    # Search NCBI for matching genomes
    found, linked = link_mediadive_species_to_ncbi(
        species['species'],
        domain=species['domain'],
        max_results=3,  # Link up to 3 reference genomes per species
    )
    print(f"  → Found {found}, linked {linked} genomes")
```

**What happens:**
1. Extracts unique species names from `strains` table
2. For each species, searches NCBI Assembly database
3. Filters for reference genomes (high quality)
4. Stores in `genomes` table with `strain_id` foreign key

**Result:** `genomes` table now contains NCBI genomes linked to MediaDive strains

### Phase 2: Propagate Growth Data to Genomes

```python
from src.ingest.link_mediadive_to_genomes import propagate_growth_data_to_genomes

count = propagate_growth_data_to_genomes()
print(f"Propagated {count} growth observations")
```

**What happens:**
1. For each strain with linked genomes
2. Copies all `strain_growth` records to `genome_growth`
3. Sets `source='mediadive'`
4. Assigns confidence based on `growth_quality`

**Data Mapping:**
- `growth_quality='excellent'` → confidence=0.95
- `growth_quality='good'` → confidence=0.85
- `growth_quality='fair'` → confidence=0.70
- `growth_quality='poor'` → confidence=0.50
- (default) → confidence=0.75

**Result:** `genome_growth` table populated with 10,000-50,000+ training pairs

### Phase 3: Build Composite Dataset

```python
from src.ingest.link_mediadive_to_genomes import create_composite_training_dataset

dataset_file = create_composite_training_dataset()
print(f"Dataset created: {dataset_file}")

# Load and inspect
import json
with open(dataset_file) as f:
    data = json.load(f)
    
print(f"Total pairs: {len(data['pairs'])}")
for pair in data['pairs'][:3]:
    print(f"  {pair['species']:30} → {pair['media_name']:20} | growth={pair['growth']}")
```

**Output file:** `data/processed/mediadive_ncbi_integrated_dataset.json`

**Fields per pair:**
- `genome_id`: NCBI assembly accession
- `species`: Organism name
- `strain_ccno`: Culture collection number (if available)
- `media_id`: MediaDive media ID
- `media_name`: Human-readable media name
- `pH_min`, `pH_max`: Media pH range
- `growth`: Boolean label
- `confidence`: Confidence score [0-1]
- `organism_type`: bacteria|archea|fungi|protist
- `genome_gc_content`: GC% of genome
- `genome_length`: Sequence length in bp
- `ingredients`: Concatenated list with concentrations
- `ingredient_count`: Number of ingredients

---

## Data Statistics

### Expected Volumes

After full integration:

```
MediaDive Strains:     5,000-10,000
├─ With NCBI genomes:  3,000-7,000 (60-70% coverage)
└─ Genomes linked:     4,000-12,000 (1-3 per species)

Training Pairs:        10,000-50,000+
├─ Positive growth:    7,000-35,000
└─ Negative growth:    3,000-15,000

Media Coverage:        100-300+ unique formulations
Organism Types:        4 (bacteria, archaea, fungi, protists)
```

### Quality Metrics

**Positive Growth Ratio:**
- Typical: 60-80% (biological reality: some media work, many don't)
- Per-organism variation: ±10-20%

**Confidence Distribution:**
- High confidence (0.85-0.95): 60-70% (direct MediaDive observations)
- Medium confidence (0.70-0.84): 20-30% (fair/good quality data)
- Lower confidence (0.50-0.69): 5-10% (poor quality, rare organisms)

**Coverage:**
- All strains: One genome linked on average (higher for common species)
- Media: 90%+ of MediaDive media represented in training data

---

## Advanced Usage

### Custom Linking Parameters

```bash
# Link only specific species
python -m scripts.integrate_mediadive_ncbi \
    --link-species \
    --max-per-species 5 \
    --limit-species 10

# Link first 10 species, up to 5 genomes each
```

### Selective Propagation

```python
from src.ingest.link_mediadive_to_genomes import propagate_growth_data_to_genomes

# Propagate with quality filter (only good/excellent quality)
# (Modify function to add confidence threshold)
count = propagate_growth_data_to_genomes()
```

### Extract Rich Features

```python
from src.ingest.link_mediadive_to_genomes import extract_rich_dataset_features

data = extract_rich_dataset_features()

print(f"Dataset shape:")
print(f"  Samples: {len(data['features'])}")
print(f"  Feature dims: {data['features'][0].shape if data['features'] else 'N/A'}")
print(f"  Labels: {set(data['labels'])}")
print(f"  Organism types: {set(data['organism_types'])}")

# Examine metadata
for i, meta in enumerate(data['metadata'][:3]):
    print(f"\nSample {i}:")
    print(f"  Organism: {meta['organism_name']}")
    print(f"  Media: {meta['media_name']}")
    print(f"  Growth: {data['labels'][i]}")
    print(f"  Confidence: {meta['confidence']}")
```

### Generate Statistics Report

```bash
# Console output
make integrate-stats --verbose

# Save to file
python -m scripts.integrate_mediadive_ncbi \
    --stats \
    --verbose \
    --save-report integration_report.txt
```

---

## Using the Dataset for Training

### 1. Load Composite Dataset

```python
import json
import numpy as np

# Load
with open('data/processed/mediadive_ncbi_integrated_dataset.json') as f:
    data = json.load(f)

pairs = data['pairs']
print(f"Loaded {len(pairs)} genome-media pairs")
```

### 2. Split by Organism Type (Curriculum Learning)

```python
from collections import defaultdict

pairs_by_organism = defaultdict(list)
for pair in pairs:
    pairs_by_organism[pair['organism_type']].append(pair)

# Curriculum order
curriculum = ['bacteria', 'archea', 'fungi', 'protists']

for org_type in curriculum:
    count = len(pairs_by_organism[org_type])
    print(f"{org_type:12} | {count:5} pairs")
```

### 3. Build Training Batches

```python
import pickle
from pathlib import Path

# Reconstruct genome embeddings + media vectors
genome_embeddings = {}  # Load from genome_embeddings table
media_compositions = {}  # Load from media_composition table

for pair in pairs:
    genome_id = pair['genome_id']
    media_id = pair['media_id']
    
    # Get features
    genome_emb = genome_embeddings[genome_id]  # 128-dim k-mer profile
    media_comp = media_compositions[media_id]  # Ingredient composition
    
    # Create training example
    x = np.concatenate([genome_emb, media_comp])
    y = pair['growth']
    
    # Use for CVAE training
```

### 4. Curriculum Learning Training Loop

```python
from src.models.media_generator import ConditionalMediaVAE

model = ConditionalMediaVAE(
    genome_embedding_dim=128,
    media_embedding_dim=100,
    latent_dim=32,
)

curriculum_order = ['bacteria', 'archea', 'fungi', 'protists']

for phase, org_type in enumerate(curriculum_order, 1):
    print(f"\n=== Phase {phase}: {org_type} ===")
    
    # Get pairs for this organism type
    phase_pairs = [p for p in pairs if p['organism_type'] == org_type]
    print(f"Training on {len(phase_pairs)} pairs")
    
    # Train
    for epoch in range(50):
        # ... training loop ...
        pass
    
    # Evaluate
    val_loss = model.evaluate(phase_pairs)
    print(f"Phase {phase} complete | Val loss: {val_loss:.4f}")
```

---

## Troubleshooting

### "No species found in MediaDive"

**Problem:** `extract_mediadive_species()` returns empty list

**Solution:**
1. Verify MediaDive data was ingested: `SELECT COUNT(*) FROM strains;`
2. Check species column is populated: `SELECT COUNT(DISTINCT species) FROM strains WHERE species IS NOT NULL;`
3. Run `make ingest` if strains data is missing

### "NCBI rate limit exceeded"

**Problem:** API returns 429 error

**Solutions:**
1. Add API key to `.env`: `NCBI_API_KEY=your_key`
2. Increases limit from 3 to 10 requests/sec
3. Or: Run during off-peak hours, requests auto-retry with backoff

### "Genomes linked but no growth data propagated"

**Problem:** `genome_growth` table is empty after propagation

**Solutions:**
1. Check genomes are properly linked: `SELECT COUNT(*) FROM genomes WHERE strain_id IS NOT NULL;`
2. Verify MediaDive growth data exists: `SELECT COUNT(*) FROM strain_growth;`
3. Check strain_id foreign key constraint: `PRAGMA foreign_key_check;`

### "Low confidence scores in propagated data"

**Normal if:**
- Many MediaDive observations are low quality
- Use `confidence` column to filter in training

**Solution:**
```sql
-- Filter for high-confidence only
SELECT * FROM genome_growth 
WHERE source='mediadive' AND confidence >= 0.85;
```

---

## Data Quality Considerations

### Biases to Be Aware Of

1. **Publication Bias**: Some organisms/media over-represented in literature
2. **Model Organism Bias**: E. coli, S. cerevisiae, B. subtilis heavily represented
3. **Media Bias**: LB medium dominates bacterial data
4. **Environmental Bias**: Lab organisms ≠ environmental organisms

### Mitigation Strategies

1. **Confidence Weighting**: Use confidence scores in loss function
2. **Stratified Sampling**: Ensure balanced organism type representation
3. **Data Augmentation**: Generate synthetic conditions for rare organisms
4. **Curriculum Learning**: Start with well-sampled domain, progress to rare organisms

### Quality Checkpoints

```sql
-- Check positive/negative balance
SELECT growth, COUNT(*) FROM genome_growth 
WHERE source='mediadive' 
GROUP BY growth;

-- Check per-organism balance
SELECT organism_type, COUNT(*) FROM genomes g
JOIN genome_growth gg ON g.genome_id = gg.genome_id
WHERE gg.source='mediadive'
GROUP BY organism_type;

-- Check confidence distribution
SELECT 
    ROUND(confidence, 1) as conf_bin,
    COUNT(*) as count
FROM genome_growth
WHERE source='mediadive'
GROUP BY ROUND(confidence, 1)
ORDER BY conf_bin DESC;
```

---

## Next Steps

1. **Verify Integration**:
   ```bash
   make integrate-stats
   ```

2. **Extract Embeddings** (if not already done):
   ```bash
   python -m scripts.build_features --compute-genome-embeddings --all-organisms
   ```

3. **Build Final Dataset**:
   ```bash
   make features
   ```

4. **Train CVAE**:
   ```bash
   make train-cvae-all
   ```

5. **Evaluate**:
   - Cross-organism generalization
   - Curriculum learning effectiveness
   - Generated media quality

---

## API Reference

### Main Functions

```python
# Extract MediaDive data
extract_mediadive_species() → List[Dict]

# Link to NCBI
link_mediadive_species_to_ncbi(species, domain, max_results) → (found, linked)

# Propagate growth data
propagate_growth_data_to_genomes() → count

# Extract features
extract_rich_dataset_features() → Dict

# Statistics
get_linked_dataset_stats() → Dict

# Build dataset
create_composite_training_dataset() → filepath
```

### Command Line Interface

```bash
# Full pipeline
python -m scripts.integrate_mediadive_ncbi --full

# Individual steps
python -m scripts.integrate_mediadive_ncbi --link-species --max-per-species 5
python -m scripts.integrate_mediadive_ncbi --propagate
python -m scripts.integrate_mediadive_ncbi --build-dataset

# Statistics
python -m scripts.integrate_mediadive_ncbi --stats --verbose

# Dry run
python -m scripts.integrate_mediadive_ncbi --full --dry-run

# Save report
python -m scripts.integrate_mediadive_ncbi --full --save-report report.txt
```

---

## See Also

- [DATA_SOURCES.md](DATA_SOURCES.md) - API integration details
- [CVAE_IMPLEMENTATION.md](CVAE_IMPLEMENTATION.md) - Model architecture
- [QUICK_START.md](QUICK_START.md) - Quick reference

---

**Status**: ✅ Production Ready

**Last Updated**: 2024

**Maintained By**: MediaDive Growth DB Team
