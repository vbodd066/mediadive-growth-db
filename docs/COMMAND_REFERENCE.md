# 📋 Command Reference

**Complete command reference for all MediaDive Growth DB operations.**

---

## ⚡ One-Line Quick Start

```bash
make integrate-mediadive-ncbi && make integrate-stats && make features && make train-cvae-all
```

---

## Phase-by-Phase Commands

### Phase 1: Link MediaDive Species to NCBI Genomes

```bash
# Full link phase
make integrate-link-species

# With custom parameters
python -m scripts.integrate_mediadive_ncbi --link-species --max-per-species 5

# Dry run preview (no execution)
python -m scripts.integrate_mediadive_ncbi --link-species --dry-run
```

**Result**: 4,000-12,000 NCBI genomes linked to MediaDive strains

---

### Phase 2: Propagate Growth Data

```bash
# Full propagation
make integrate-propagate

# With detailed output
python -m scripts.integrate_mediadive_ncbi --propagate --verbose

# With statistics
python -m scripts.integrate_mediadive_ncbi --propagate --stats
```

**Result**: 10,000-50,000 training pairs with growth labels

---

### Phase 3: View Statistics

```bash
# Quick summary
make integrate-stats

# Detailed output
make integrate-stats --verbose

# Save to file
python -m scripts.integrate_mediadive_ncbi --stats --save-report report.txt

# View report
cat integration_report.txt
```

**Output**: Coverage, distribution, confidence metrics

---

## 🚀 Complete Workflows

### Full Integration Pipeline

```bash
# All-in-one
make integrate-mediadive-ncbi

# Equivalent to
python -m scripts.integrate_mediadive_ncbi --full
```

**Time**: 8-30 minutes

### End-to-End: Ingest → Train

```bash
# Complete workflow
make integrate-mediadive-ncbi     # Link + propagate (20-30 min)
make integrate-stats              # View results (1 min)
make features                     # Extract embeddings (5-10 min)
make train-cvae-all               # Train model (2-4 hours on GPU)
```

**Total time**: 3-5 hours

### Quick Test (Small Dataset)

```bash
# Test with first 10 species
python -m scripts.integrate_mediadive_ncbi --link-species --limit-species 10
python -m scripts.integrate_mediadive_ncbi --propagate
make integrate-stats

# Fast result: validate setup works
```

---

## 🐍 Python API Usage

### Get Species from MediaDive

```python
from src.ingest.link_mediadive_to_genomes import extract_mediadive_species

species_list = extract_mediadive_species()
# Returns: [{"species": "E. coli", "domain": "bacteria", "count": 150}, ...]

for sp in species_list[:5]:
    print(f"{sp['species']}: {sp['count']} strains")
```

### Link Species to NCBI

```python
from src.ingest.link_mediadive_to_genomes import link_mediadive_species_to_ncbi

found, linked = link_mediadive_species_to_ncbi(
    species="Escherichia coli",
    domain="bacteria",
    max_results=3  # Up to 3 genomes per species
)
print(f"Found: {found}, Linked: {linked}")
```

### Propagate Growth Data

```python
from src.ingest.link_mediadive_to_genomes import propagate_growth_data_to_genomes

count = propagate_growth_data_to_genomes()
print(f"Propagated {count} observations")
```

### Get Statistics

```python
from src.ingest.link_mediadive_to_genomes import get_linked_dataset_stats
import json

stats = get_linked_dataset_stats()
print(json.dumps(stats, indent=2))
```

### Create Training Dataset

```python
from src.ingest.link_mediadive_to_genomes import create_composite_training_dataset

dataset_file = create_composite_training_dataset()
print(f"Dataset created: {dataset_file}")

# Load and inspect
import json
with open(dataset_file) as f:
    data = json.load(f)
    
for pair in data['pairs'][:3]:
    print(f"{pair['species']} → {pair['media_name']} | growth={pair['growth']}")
```

---

## 🔧 Custom Parameters

### Link with Specific Limits

```bash
# First 20 species, up to 5 genomes each
python -m scripts.integrate_mediadive_ncbi \
    --link-species \
    --limit-species 20 \
    --max-per-species 5
```

### Verbose Output for Debugging

```bash
# Detailed logging
python -m scripts.integrate_mediadive_ncbi \
    --full \
    --verbose

# Follow in real-time
tail -f mediadive_ingest.log
```

### Save Comprehensive Report

```bash
python -m scripts.integrate_mediadive_ncbi \
    --full \
    --verbose \
    --save-report my_report.txt

cat my_report.txt
```

---

## 📊 Data Inspection (SQL)

### Count Linked Genomes

```bash
sqlite3 data/processed/mediadive.db \
  "SELECT organism_type, COUNT(*) FROM genomes WHERE strain_id IS NOT NULL GROUP BY organism_type;"
```

### View Training Pairs

```bash
sqlite3 data/processed/mediadive.db \
  "SELECT COUNT(*) total, SUM(growth) positive FROM genome_growth WHERE source='mediadive';"
```

### Growth Statistics

```bash
sqlite3 data/processed/mediadive.db \
  "SELECT growth, COUNT(*) FROM genome_growth WHERE source='mediadive' GROUP BY growth;"
```

### Confidence Distribution

```bash
sqlite3 data/processed/mediadive.db \
  "SELECT ROUND(confidence, 1), COUNT(*) FROM genome_growth WHERE source='mediadive' GROUP BY ROUND(confidence, 1) ORDER BY ROUND(confidence, 1) DESC;"
```

### Top Media by Coverage

```bash
sqlite3 data/processed/mediadive.db \
  "SELECT media_id, COUNT(*) FROM genome_growth WHERE source='mediadive' GROUP BY media_id ORDER BY COUNT(*) DESC LIMIT 10;"
```

---

## 📈 Feature Engineering

### Build All Features

```bash
make features
```

### Build Specific Features

```bash
# Genome embeddings (k-mer profiles)
python -m scripts.build_features --compute-genome-embeddings

# Media composition vectors
python -m scripts.build_features --build-media-vectors

# Combined dataset
python -m scripts.build_features --build-genome-media-dataset
```

### Check Feature Status

```bash
sqlite3 data/processed/mediadive.db \
  "SELECT COUNT(*) FROM genome_embeddings;"

sqlite3 data/processed/mediadive.db \
  "SELECT COUNT(*) FROM media_composition;"
```

---

## 🤖 Model Training

### CVAE Training

```bash
# Full curriculum learning (all organisms)
make train-cvae-all

# Single organism
make train-cvae

# Custom configuration
python -m scripts.train_cvae \
    --organism bacteria \
    --epochs 100 \
    --batch-size 32 \
    --latent-dim 32 \
    --curriculum-learning
```

### Training Parameters

```bash
# Lower learning rate (more stable but slower)
python -m scripts.train_cvae --lr 1e-4

# Smaller batch size (better for small GPU)
python -m scripts.train_cvae --batch-size 16

# Fewer epochs (quick test)
python -m scripts.train_cvae --epochs 20
```

### Check Training Progress

```bash
# Monitor in real-time
tail -f mediadive_training.log

# Check checkpoint
ls -lh data/models/
```

---

## 🔍 Troubleshooting Commands

### Verify Connections

```bash
# Test NCBI
python << 'EOF'
from src.ingest.fetch_ncbi_organisms import ncbi_search
results = ncbi_search('assembly', 'Escherichia coli', max_results=1)
print("✅ NCBI OK" if results else "❌ NCBI Failed")
EOF

# Test database
python << 'EOF'
from src.db.queries import table_counts
counts = table_counts()
print(f"✅ Database OK: {counts}")
EOF
```

### Check Data Integrity

```bash
# Foreign key constraint check
sqlite3 data/processed/mediadive.db "PRAGMA foreign_key_check;"

# Orphaned records
sqlite3 data/processed/mediadive.db \
  "SELECT COUNT(*) FROM genomes g WHERE NOT EXISTS (SELECT 1 FROM strains s WHERE g.strain_id = s.strain_id);"
```

### View System Status

```bash
# What tables exist
sqlite3 data/processed/mediadive.db ".tables"

# All record counts
sqlite3 data/processed/mediadive.db ".dump" | grep -c "INSERT INTO"

# Database size
du -h data/processed/mediadive.db

# Check Python environment
python << 'EOF'
import torch
print(f"PyTorch: {torch.__version__}")
print(f"GPU: {torch.cuda.is_available()}")
print(f"CUDA: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
EOF
```

---

## 📁 File Management

### View Dataset

```bash
# First 50 lines
head -50 data/processed/mediadive_ncbi_integrated_dataset.json

# Pretty print
cat data/processed/mediadive_ncbi_integrated_dataset.json | python -m json.tool | head -100

# Total pairs
python -c "import json; print(len(json.load(open('data/processed/mediadive_ncbi_integrated_dataset.json'))['pairs']))"
```

### Backup Data

```bash
# Backup database
cp data/processed/mediadive.db data/processed/mediadive.db.backup

# Backup models
tar -czf data/models.tar.gz data/models/
```

### Clean Up

```bash
# Remove temporary files
rm -f data/raw/api_cache_*/*

# Clear logs
rm mediadive_*.log

# Note: Don't delete data/processed/ without backup!
```

---

## 🔄 Integration + Training Workflow Script

```bash
#!/bin/bash
# Save as run_workflow.sh

set -e  # Exit on error

echo "==== MediaDive-NCBI Integration & Training Workflow ===="
echo ""

echo "[1/5] Integrating MediaDive with NCBI..."
make integrate-mediadive-ncbi
echo "✅ Integration complete"
echo ""

echo "[2/5] Viewing statistics..."
make integrate-stats
echo "✅ Statistics complete"
echo ""

echo "[3/5] Building features..."
make features
echo "✅ Features complete"
echo ""

echo "[4/5] Training CVAE..."
make train-cvae-all
echo "✅ Training complete"
echo ""

echo "[5/5] Done!"
echo "==== Workflow Complete ===="
echo ""
echo "Results:"
echo "  Database: data/processed/mediadive.db"
echo "  Dataset: data/processed/mediadive_ncbi_integrated_dataset.json"
echo "  Model: data/models/"
echo ""
```

Run it:
```bash
chmod +x run_workflow.sh
./run_workflow.sh
```

---

## 🆘 Getting Help

### View Documentation

```bash
# Navigation hub
open docs/INDEX.md

# Getting started
open docs/GETTING_STARTED.md

# Troubleshooting
open docs/TROUBLESHOOTING.md

# Specific guides
open docs/guides/mediadive_ncbi_linking.md
open docs/guides/cvae_training.md
open docs/guides/api_reference.md
```

### Get Script Help

```bash
# List all options
python -m scripts.integrate_mediadive_ncbi --help
python -m scripts.train_cvae --help
python -m scripts.build_features --help
```

### Check Logs

```bash
# Last 50 lines of logs
tail -50 mediadive_ingest.log

# Follow logs in real-time
tail -f mediadive_ingest.log

# Search for errors
grep -i error mediadive_ingest.log | tail -20
```

---

## 💾 Environment Variables

```bash
# Required
NCBI_EMAIL=your.email@example.com

# Optional but recommended (higher rate limits)
NCBI_API_KEY=your_api_key_here

# Optional (adjust if needed)
BACDIVE_REQUEST_DELAY=0.5
```

Set in `.env`:
```bash
cp .env.example .env
nano .env  # Edit and add variables
```

---

## ⏱️ Performance Reference

| Task | Time | GPU |
|------|------|-----|
| Link species (full) | 10-15 min | N/A |
| Propagate | 5-30 min | N/A |
| Build embeddings | 5-10 min | N/A |
| Build features | 2-5 min | N/A |
| Train (bacteria) | 1-2 hrs | Optional |
| Train (all curriculum) | 4-8 hrs | Recommended |

---

## 📝 Common Patterns

### Incremental Development

```bash
# Day 1: Just link
make integrate-link-species

# Day 2: Link more species
make integrate-link-species

# Day 3: Propagate
make integrate-propagate

# Day 4: Train
make train-cvae-all
```

### Debugging Workflow

```bash
# 1. Test connection
python -m scripts.integrate_mediadive_ncbi --link-species --limit-species 1 --dry-run

# 2. Actually run small subset
python -m scripts.integrate_mediadive_ncbi --link-species --limit-species 5

# 3. Check results
make integrate-stats

# 4. Scale up
python -m scripts.integrate_mediadive_ncbi --link-species
```

---

**Quick Access**:  
👉 **Most used**: `make integrate-mediadive-ncbi`, `make integrate-stats`, `make train-cvae-all`  
👉 **Help**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)  
👉 **More info**: See [docs/guides/](guides/)

---

**Status**: ✅ Current  
**Last Updated**: 2024
