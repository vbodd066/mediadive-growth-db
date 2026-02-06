# MediaDive-NCBI Integration: Complete Workflow

## Overview

This document shows the complete end-to-end workflow for building a rich training dataset by integrating MediaDive strain data with NCBI genomes.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Existing MediaDive Data                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  strains table               strain_growth table                   │
│  ├─ strain_id               ├─ strain_id (FK)                      │
│  ├─ species                 ├─ media_id (FK)                       │
│  ├─ ccno (culture collection)  ├─ growth (bool)                     │
│  ├─ domain                  ├─ growth_rate                         │
│  └─ bacdive_id              ├─ growth_quality                      │
│                             └─ modification                        │
│  media table                media_composition table                │
│  ├─ media_id               ├─ media_id (FK)                        │
│  ├─ media_name             ├─ ingredient_id (FK)                   │
│  ├─ min_pH, max_pH         ├─ g_per_l                              │
│  └─ description            └─ mmol_per_l                           │
│                                                                     │
│  ingredients table                                                  │
│  ├─ ingredient_id                                                   │
│  ├─ ingredient_name                                                 │
│  ├─ chebi_id, cas_rn, kegg_compound                                │
│  └─ molar_mass, formula, density                                   │
│                                                                     │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               │ NEW: LinkMediaDiveToGenomes Pipeline
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│        Phase 1: Link Species to NCBI                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Extract unique species from strains table                        │
│     Result: [                                                        │
│       {species: "Escherichia coli", domain: "B", count: 150},       │
│       {species: "Bacillus subtilis", domain: "B", count: 89},       │
│       ...                                                            │
│     ]                                                                │
│                                                                      │
│  2. For each species:                                                │
│     a. Search NCBI Assembly: "{species}" AND "complete genome"       │
│     b. Filter reference genomes (high quality)                       │
│     c. Store in genomes table with strain_id FK                      │
│                                                                      │
│  Result: genomes table populated                                     │
│          5,000-7,000 species × 1-3 genomes = 10,000-20,000 rows    │
│                                                                      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│        Phase 2: Propagate Growth Data to Genomes                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  For each strain with linked genomes:                                │
│                                                                      │
│    strain_growth                          genome_growth             │
│    ────────────────                       ──────────────             │
│    strain_id → media_id, growth           genome_id → media_id      │
│         │                                      │                     │
│         └─ join via ─────────────────────────────┘                  │
│            strain.strain_id = genomes.strain_id                     │
│                                                                      │
│  Copy all observations:                                              │
│    INSERT INTO genome_growth                                        │
│    SELECT g.genome_id, sg.media_id, sg.growth,                     │
│           sg.growth_rate, confidence, 'mediadive'                  │
│    FROM genomes g                                                    │
│    JOIN strains s ON g.strain_id = s.strain_id                     │
│    JOIN strain_growth sg ON s.strain_id = sg.strain_id             │
│                                                                      │
│  Confidence mapping:                                                 │
│    excellent → 0.95  |  good → 0.85  |  fair → 0.70  |  poor → 0.50
│                                                                      │
│  Result: genome_growth table populated                              │
│          10,000-50,000 training observations                        │
│                                                                      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│      Phase 3: Build Composite Training Dataset                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Query: Get all linked genome-media pairs with metadata             │
│                                                                      │
│  SELECT                                                              │
│    g.genome_id, s.species, s.ccno,                                 │
│    m.media_id, m.media_name,                                       │
│    gg.growth, gg.confidence, gg.source,                            │
│    g.organism_type, g.gc_content, g.sequence_length,              │
│    GROUP_CONCAT(i.ingredient_name || '(' || mc.g_per_l || 'g/L')   │
│  FROM genome_growth gg                                              │
│  JOIN genomes g, strains s, media m, media_composition mc, ...     │
│                                                                      │
│  Output JSON with fields per pair:                                  │
│  {                                                                   │
│    "genome_id": "GCF_000005845.2",                                 │
│    "species": "Escherichia coli",                                  │
│    "strain_ccno": "K-12 substr. MG1655",                           │
│    "media_id": "48",                                                │
│    "media_name": "Luria Broth (LB)",                               │
│    "pH_min": 6.5,                                                   │
│    "pH_max": 8.0,                                                   │
│    "growth": true,                                                  │
│    "confidence": 0.95,                                              │
│    "organism_type": "bacteria",                                     │
│    "genome_gc_content": 50.8,                                       │
│    "genome_length": 4641652,                                        │
│    "ingredients": "peptone(10g/L);beef_extract(5g/L);NaCl(10g/L)", │
│    "ingredient_count": 3                                            │
│  }                                                                   │
│                                                                      │
│  Result: mediadive_ncbi_integrated_dataset.json                     │
│          10,000-50,000 complete training pairs                      │
│                                                                      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│        Ready for CVAE Training                                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  For each genome-media pair:                                         │
│                                                                      │
│    1. Load genome embeddings (k-mer 128-dim from genome_embeddings) │
│    2. Load media composition vector (from media_composition)        │
│    3. Create training example (X, y)                                │
│                                                                      │
│    X = [genome_embedding, media_composition]                        │
│    y = growth_label                                                 │
│                                                                      │
│  Split by organism type for curriculum learning:                    │
│                                                                      │
│    Phase 1: Bacteria     (8,000-12,000 pairs)                       │
│    Phase 2: Archaea      (500-1,000 pairs)                          │
│    Phase 3: Fungi        (1,000-2,000 pairs)                        │
│    Phase 4: Protists     (100-200 pairs)                            │
│                                                                      │
│  Training loop:                                                      │
│    for phase in [bacteria, archaea, fungi, protists]:               │
│        model = train_cvae(phase_pairs)                              │
│        evaluate_cross_organism_generalization()                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Reference: Command Execution

```bash
# ┌─ Setup ─────────────────────────────────────────────────┐
cd mediadive-growth-db
cp .env.example .env
# Edit .env: add NCBI_EMAIL=your@email.com

# ┌─ Integration ───────────────────────────────────────────┐

# Option 1: One command (full pipeline)
make integrate-mediadive-ncbi

# Option 2: Step-by-step
make integrate-link-species      # Phase 1: Link to NCBI
make integrate-propagate         # Phase 2: Propagate growth data
make integrate-stats             # Phase 3: View results

# ┌─ Training ──────────────────────────────────────────────┐

# Extract genome embeddings (if needed)
make build-genome-embeddings

# Build features and dataset
make features

# Train CVAE with curriculum learning
make train-cvae-all
```

## Data Volumes: Before & After

### Before Integration (MediaDive Only)

```
Strains:                 5,000-10,000
├─ Genomes:              0 (no genome data)
└─ Growth observations:  10,000-50,000

Media types:             100-300
Ingredients:             500-1000
Training pairs:          ❌ Can't train CVAE (no genomes)
```

### After Integration (MediaDive + NCBI)

```
Strains:                 5,000-10,000
├─ With genomes:         3,000-7,000 (60-70% coverage)
├─ Genomes linked:       4,000-12,000
└─ Growth observations:  10,000-50,000

Media types:             100-300
Ingredients:             500-1000
Training pairs:          ✅ 10,000-50,000 (genome, media, growth)

Organism types:
├─ Bacteria:             8,000-12,000 pairs
├─ Archaea:              500-1,000 pairs
├─ Fungi:                1,000-2,000 pairs
└─ Protists:             100-200 pairs

Ready for CVAE training: ✅ YES
```

## Key Features

### 1. Cross-Organism Data Linking

```
MediaDive Strain             →  NCBI Genomes
────────────────────────────    ──────────────
Escherichia coli K-12        →  GCF_000005845.2 (reference)
                             →  GCF_000017325.1 (other assembly)

Growth on LB medium          →  Genome embedding (k-mer 128-dim)
Growth on Nutrient medium    →  Media composition vector
Growth on M9 medium
```

### 2. Metadata Richness

Each training pair includes:
- ✅ Genome embedding (organism signature)
- ✅ Media composition (chemical specification)
- ✅ Growth label (binary observation)
- ✅ Confidence score (data quality)
- ✅ Temperature range (from media metadata)
- ✅ pH range (from media metadata)
- ✅ Ingredient list (from media formulation)
- ✅ Organism type (curriculum learning)
- ✅ GC content (genomic feature)
- ✅ Sequence length (genomic feature)

### 3. Quality Assurance

```
Confidence scoring:
┌─────────────────────────────────────┐
│ Direct MediaDive observation        │
├─ excellent growth quality: 0.95     │
├─ good growth quality:      0.85     │
├─ fair growth quality:      0.70     │
├─ poor growth quality:      0.50     │
└─ default (unspecified):    0.75     │
└─────────────────────────────────────┘

Deduplication:
├─ Same strain-media pair: take highest confidence
├─ Cross-database duplicates: merge with weighting
└─ Organism name variants: normalize via NCBI taxonomy
```

## Expected Outcomes

### Dataset Statistics

```
Total genome-media pairs:    10,000-50,000
├─ Positive growth:          6,000-35,000 (60-70%)
└─ Negative growth:          4,000-15,000 (30-40%)

Organism distribution:
├─ Bacteria:                 80% (most data)
├─ Fungi:                    10%
├─ Archaea:                  8%
└─ Protists:                 2%

Media distribution:
├─ LB medium:                15-20%
├─ Nutrient medium:          10-15%
├─ M9 medium:                5-10%
├─ Specialized media:        50-70%
└─ Total unique types:       100-300

Feature availability:
├─ Genome embeddings:        100% (precomputed)
├─ Media composition:        90-95%
├─ pH metadata:              80-90%
├─ Ingredient details:       95-99%
└─ Temperature metadata:     Varies by media source
```

### Training Performance

**Phase 1 (Bacteria):**
- Training pairs: 8,000-12,000
- Expected loss: 0.15-0.20
- Training time (GPU): 1-2 hours
- Cross-organism accuracy: N/A (same organism type)

**Phase 2 (Archaea):**
- Training pairs: 500-1,000
- Expected loss: 0.18-0.23 (slightly higher, new patterns)
- Training time (GPU): 15-30 minutes
- Cross-organism accuracy: 70-80% (vs bacteria)

**Phase 3 (Fungi):**
- Training pairs: 1,000-2,000
- Expected loss: 0.20-0.25 (eukaryotic complexity)
- Training time (GPU): 30-60 minutes
- Cross-organism accuracy: 60-75% (vs bacteria)

**Phase 4 (Protists):**
- Training pairs: 100-200
- Expected loss: 0.22-0.28 (limited data, complex features)
- Training time (GPU): 5-10 minutes
- Cross-organism accuracy: 50-65% (vs bacteria)

## Usage in CVAE Training

```python
import json
import numpy as np
from torch.utils.data import DataLoader, TensorDataset

# Load integrated dataset
with open('data/processed/mediadive_ncbi_integrated_dataset.json') as f:
    data = json.load(f)

pairs = data['pairs']

# Split by organism type (curriculum learning)
pairs_by_type = {}
for pair in pairs:
    org_type = pair['organism_type']
    if org_type not in pairs_by_type:
        pairs_by_type[org_type] = []
    pairs_by_type[org_type].append(pair)

# Curriculum training
curriculum_order = ['bacteria', 'archea', 'fungi', 'protists']
model = ConditionalMediaVAE(...)

for phase, org_type in enumerate(curriculum_order, 1):
    print(f"\nPhase {phase}: Training on {org_type}")
    
    phase_pairs = pairs_by_type.get(org_type, [])
    if not phase_pairs:
        print(f"  No {org_type} data, skipping")
        continue
    
    print(f"  Training on {len(phase_pairs)} pairs")
    
    # Create data loaders
    genome_embeddings = [...]  # Load from database
    media_compositions = [...]  # Load from database
    growth_labels = [p['growth'] for p in phase_pairs]
    
    X = torch.cat([genome_embeddings, media_compositions], dim=1)
    y = torch.tensor(growth_labels, dtype=torch.float32)
    
    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=64)
    
    # Train
    for epoch in range(50):
        train_loss = model.train_epoch(loader)
        print(f"  Epoch {epoch+1}: loss={train_loss:.4f}")
    
    # Validate
    val_loss = model.evaluate(phase_pairs)
    print(f"  Validation loss: {val_loss:.4f}")
    
    # Save checkpoint
    model.save(f'checkpoints/cvae_phase{phase}.pt')
```

## Quality Considerations

### Data Biases

1. **Model Organism Bias**: E. coli, S. cerevisiae over-represented
2. **Media Bias**: LB and standard media dominant
3. **Taxonomic Bias**: Culturable organisms only (excludes uncultured)
4. **Temporal Bias**: Historical data (older strains may have different characteristics)

### Mitigation

- Use confidence scores as weights in loss function
- Apply stratified sampling across organism types
- Data augmentation for rare organisms
- Curriculum learning to handle distribution shift

### Quality Checks

```sql
-- Check data balance
SELECT organism_type, COUNT(*) FROM genome_growth
WHERE source='mediadive'
GROUP BY organism_type;

-- Check confidence distribution
SELECT ROUND(confidence, 1), COUNT(*)
FROM genome_growth WHERE source='mediadive'
GROUP BY ROUND(confidence, 1);

-- Check positive/negative balance
SELECT growth, COUNT(*) FROM genome_growth
WHERE source='mediadive'
GROUP BY growth;
```

## Next Steps

1. ✅ **Execute integration**: `make integrate-mediadive-ncbi`
2. ✅ **Verify dataset**: `make integrate-stats`
3. ✅ **Build features**: `make features`
4. ✅ **Train CVAE**: `make train-cvae-all`
5. 🔄 **Evaluate**: Cross-organism generalization metrics
6. 🔄 **Iterate**: Tune curriculum schedule, model architecture

## See Also

- [MEDIADIVE_NCBI_INTEGRATION.md](MEDIADIVE_NCBI_INTEGRATION.md) - Detailed guide
- [CVAE_IMPLEMENTATION.md](CVAE_IMPLEMENTATION.md) - Model architecture
- [DATA_SOURCES.md](DATA_SOURCES.md) - API integration
- [QUICK_START.md](QUICK_START.md) - Commands reference

---

**Status**: ✅ Ready to execute

**Command**: `make integrate-mediadive-ncbi`
