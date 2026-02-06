# Troubleshooting Guide

**Solutions to common problems, errors, and questions.**

---

## Quick Reference

| Issue | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | Network/server down | Retry later, check internet |
| "NCBI rate limit" | Too many API requests | Add NCBI_API_KEY to .env |
| "Database locked" | Another process using DB | Close other processes, restart |
| "No results found" | Broad search terms | Try narrower searches |
| "Memory error" | Dataset too large | Reduce batch size, limit species |
| "Module not found" | Dependencies missing | `pip install -e ".[ml,viz,dev]"` |
| "Permission denied" | File permissions | `chmod 755 file` or use sudo |

---

## Installation Issues

### "ModuleNotFoundError: No module named 'torch'"

**Problem**: PyTorch not installed

**Solutions**:
```bash
# Full installation
pip install -e ".[ml,viz,dev]"

# Or install specific packages
pip install torch torchvision torchaudio
pip install pytorch-lightning
pip install transformers scikit-learn pandas numpy
```

### "Command not found: make"

**Problem**: GNU Make not installed (common on Windows)

**Solutions**:
- **macOS**: `brew install make`
- **Linux**: `sudo apt-get install make`
- **Windows**: Use `python -m scripts.xxx` instead of `make` targets

### "Permission denied" errors

**Problem**: File/folder permission issues

**Solutions**:
```bash
# Make scripts executable
chmod +x scripts/*.py

# Make data directories writable
chmod -R 755 data/

# If using sudo (not recommended)
sudo pip install -e ".[ml,viz,dev]"
```

---

## Setup Issues

### ".env not found"

**Problem**: Environment configuration file missing

**Solution**:
```bash
# Create from template
cp .env.example .env

# Edit and add NCBI email
# NCBI_EMAIL=your.email@example.com
```

### "NCBI_EMAIL not set"

**Problem**: Required environment variable missing

**Solution**:
```bash
# Edit .env
nano .env

# Add this line
NCBI_EMAIL=your.email@example.com

# Or set in current shell
export NCBI_EMAIL=your.email@example.com
```

### "Cannot create database"

**Problem**: Database initialization fails

**Solutions**:
```bash
# Check if database exists
ls -la data/processed/mediadive.db

# Initialize (creates if missing)
make init-db

# Or check schema
sqlite3 data/processed/mediadive.db ".tables"
```

---

## Data Ingestion Issues

### "Connection refused" (NCBI/BacDive)

**Problem**: Cannot connect to external APIs

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| Internet down | Check: `ping google.com` |
| Server down | Retry later; check https://status.ncbi.nlm.nih.gov/ |
| Firewall blocking | Configure firewall/proxy |
| DNS issues | Try: `nslookup eutils.ncbi.nlm.nih.gov` |

**Retry command**:
```bash
# Retry integration (continues from last checkpoint)
make integrate-mediadive-ncbi
```

### "NCBI rate limit exceeded"

**Problem**: API returns 429 (too many requests)

**Solutions**:
1. **Add API Key** (recommended):
   ```bash
   # Get key from: https://www.ncbi.nlm.nih.gov/account/
   # Add to .env
   NCBI_API_KEY=your_key_here
   
   # Increases limit from 3 to 10 requests/sec
   ```

2. **Increase delay**:
   ```bash
   # In .env
   BACDIVE_REQUEST_DELAY=1.0
   ```

3. **Retry later**:
   ```bash
   # Built-in backoff, retries automatically
   # Or run during off-peak hours (e.g., 2-5 AM)
   ```

### "No results found"

**Problem**: Search returns empty results

**Solutions**:

| Organism | Try | Example |
|----------|-----|---------|
| Bacteria | Broader genus name | "Escherichia" not "E. coli K-12" |
| Fungi | Common names | "Aspergillus" not "A. fumigatus strain123" |
| Protists | Phylum level | "Apicomplexa" not "specific_strain" |

**Debug**:
```bash
# Test specific search
python -c "
from src.ingest.fetch_ncbi_organisms import search_fungal_genomes
genomes = search_fungal_genomes('Saccharomyces', limit=5)
print(f'Found {len(genomes)} genomes')
for g in genomes:
    print(f'  {g[\"name\"]}')
"
```

### "Database locked" error

**Problem**: Another process using database

**Solutions**:
```bash
# Check what's using it
lsof | grep mediadive.db

# Kill process (get PID from above)
kill -9 <PID>

# Or restart terminal
# Or use temporary DB
DB_PATH=/tmp/test.db make integrate-mediadive-ncbi
```

---

## Data Processing Issues

### "Memory error" during feature building

**Problem**: Dataset too large for RAM

**Solutions**:

| Solution | Command |
|----------|---------|
| Reduce batch size | `--batch-size 8` (default 32) |
| Limit species | `--limit-species 100` |
| Process in chunks | Process organism type separately |

```bash
# Memory-efficient approach
# Link only bacteria first
python -m scripts.integrate_mediadive_ncbi \
    --link-species \
    --limit-species 50

# Propagate
python -m scripts.integrate_mediadive_ncbi --propagate

# Build features in smaller batches
python -m scripts.build_features --batch-size 8
```

### "Empty dataset" after propagation

**Problem**: No training pairs created

**Solutions**:

| Check | Command |
|-------|---------|
| Genomes linked? | `SELECT COUNT(*) FROM genomes;` |
| Growth data exists? | `SELECT COUNT(*) FROM strain_growth;` |
| Propagation ran? | `SELECT COUNT(*) FROM genome_growth;` |

```sql
-- Diagnose
SELECT COUNT(*) FROM genomes;                          -- Should be >0
SELECT COUNT(*) FROM strains WHERE strain_id IS NOT NULL;  -- Should be >0
SELECT COUNT(*) FROM genome_growth;                    -- Should be >0
SELECT COUNT(*) FROM genome_growth WHERE growth=1;     -- Positive samples
```

### "Low confidence scores"

**Problem**: Average confidence < 0.7

**Normal if**:
- Many observations are low quality
- Rare organisms with uncertain conditions

**Solution - Filter in training**:
```python
from src.ingest.link_mediadive_to_genomes import create_composite_training_dataset

# Use confidence column to weight samples
pairs = load_pairs()
high_conf = [p for p in pairs if p['confidence'] >= 0.8]
# Train on high_conf for better results
```

---

## Training Issues

### "No GPU available" (but GPU expected)

**Problem**: PyTorch not using GPU

**Solutions**:

```python
import torch
print(f"GPU available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")
print(f"GPU name: {torch.cuda.get_device_name(0)}")

# Verify in PyTorch Lightning
from pytorch_lightning import Trainer
trainer = Trainer(accelerator='gpu', devices=1)
# If error, GPU not accessible
```

**Fixes**:
- **CUDA not installed**: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
- **Wrong CUDA version**: Check `nvcc --version`, install matching PyTorch
- **GPU not detected**: Restart, check `nvidia-smi`, update drivers

### "Out of memory" during training

**Problem**: GPU/CPU memory exhausted

**Solutions**:

| Parameter | Default | Try |
|-----------|---------|-----|
| batch_size | 32 | 16 or 8 |
| num_workers | 4 | 0 |
| latent_dim | 32 | 16 |
| hidden_dim | 128 | 64 |

```bash
# Train with smaller parameters
python -m scripts.train_cvae \
    --epochs 100 \
    --batch-size 8 \
    --latent-dim 16 \
    --hidden-dims 64 32
```

### "NaN loss" (training diverges)

**Problem**: Loss becomes NaN, training collapses

**Solutions**:
1. **Lower learning rate**:
   ```bash
   python -m scripts.train_cvae --lr 1e-4  # Default 1e-3
   ```

2. **Add gradient clipping** (already in code, but verify)

3. **Normalize input data**: Ensure embeddings are scaled

4. **Check for invalid data**:
   ```python
   import numpy as np
   # Check for NaN in dataset
   assert not np.isnan(embeddings).any()
   assert not np.isinf(embeddings).any()
   ```

### "Model training too slow"

**Problem**: Training takes too long

**Solutions**:

| Solution | Time Saving |
|----------|-------------|
| Fewer epochs | 50→20 = 60% faster |
| Smaller batch size | Uses GPU more efficiently |
| Single organism | Skip curriculum learning |
| CPU mode (last resort) | Parallelize across cores |

```bash
# Faster training (trade-off: quality)
python -m scripts.train_cvae \
    --epochs 50 \
    --organism bacteria \
    --batch-size 64
```

---

## Debugging Commands

### Check System Status

```bash
# Database status
echo "=== Database ===" && \
sqlite3 data/processed/mediadive.db "SELECT name FROM sqlite_master WHERE type='table';" && \
sqlite3 data/processed/mediadive.db "SELECT name, COUNT(*) as cnt FROM (SELECT 'strains' as name, COUNT(*) as cnt FROM strains UNION SELECT 'genomes', COUNT(*) FROM genomes UNION SELECT 'strain_growth', COUNT(*) FROM strain_growth UNION SELECT 'genome_growth', COUNT(*) FROM genome_growth);"

# Environment
echo "=== Environment ===" && \
env | grep -E "(NCBI|BACDIVE|PYTHON)"

# Python packages
echo "=== Packages ===" && \
pip list | grep -E "(torch|pytorch|numpy|pandas|scikit)"

# System
echo "=== System ===" && \
python --version && \
which python && \
whoami
```

### Check Logs

```bash
# Recent errors
tail -100 mediadive_ingest.log | grep -i error

# Full log
cat mediadive_ingest.log

# By component
grep "fetch_ncbi" mediadive_ingest.log | tail -20
grep "fetch_bacdive" mediadive_ingest.log | tail -20
```

### Test Individual Components

```python
# Test NCBI connection
from src.ingest.fetch_ncbi_organisms import ncbi_search
try:
    results = ncbi_search('assembly', 'Escherichia coli', max_results=5)
    print(f"✓ NCBI connection OK ({len(results)} results)")
except Exception as e:
    print(f"✗ NCBI error: {e}")

# Test BacDive connection
from src.ingest.fetch_bacdive import search_bacdive
try:
    results = search_bacdive('E. coli', limit=5)
    print(f"✓ BacDive connection OK ({len(results)} results)")
except Exception as e:
    print(f"✗ BacDive error: {e}")

# Test database
from src.db.queries import table_counts
try:
    counts = table_counts()
    print(f"✓ Database OK: {counts}")
except Exception as e:
    print(f"✗ Database error: {e}")
```

---

## FAQ

### Q: How long does ingestion take?

**A**: 20-50 minutes depending on data volume:
- Link species: 10-15 min
- Propagate: 5-30 min (depends on linked genomes)
- Build dataset: 2-5 min

### Q: Can I run integration multiple times?

**A**: Yes, it's safe. Uses `ingest_log` to skip completed work.

### Q: How much disk space do I need?

**A**: Typical:
- Database: 50-500 MB
- Genome embeddings: 100-200 MB
- Total: <1 GB

### Q: What if my internet drops during ingest?

**A**: It's resumable. Just run `make integrate-mediadive-ncbi` again.

### Q: Can I use data from only specific organisms?

**A**: Yes, use `--limit-species` or modify Python API:
```python
species = extract_mediadive_species()
bacteria = [s for s in species if s['domain'] == 'bacteria']
```

### Q: How do I validate the dataset?

**A**: Check statistics and inspect samples:
```bash
make integrate-stats --verbose
```

### Q: Can I train without all organisms?

**A**: Yes, train on subset:
```bash
python -m scripts.train_cvae --organism bacteria --epochs 100
```

### Q: How do I add more data?

**A**: Re-run ingest pipeline (appends to database):
```bash
make integrate-mediadive-ncbi
```

---

## Getting Help

### Check Documentation

1. [GETTING_STARTED.md](GETTING_STARTED.md) - Start here
2. [COMMAND_REFERENCE.md](../COMMAND_REFERENCE.md) - All commands
3. [guides/](../guides/) - Detailed guides
4. [INDEX.md](../INDEX.md) - Documentation map

### Get More Information

```bash
# Script help
python -m scripts.integrate_mediadive_ncbi --help
python -m scripts.train_cvae --help

# Check logs
tail -f mediadive_ingest.log

# Read code comments
grep -r "TODO\|FIXME\|NOTE" src/
```

### Debug with Verbose Output

```bash
# Verbose logging
python -m scripts.integrate_mediadive_ncbi --verbose --link-species

# Python debug
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Contact & Resources

- **NCBI Status**: https://status.ncbi.nlm.nih.gov/
- **BacDive API**: https://bacdive.dsmz.de/api/v1/
- **PyTorch Issues**: https://github.com/pytorch/pytorch/issues
- **Local Help**: See [guides/](../guides/) folder

---

**Status**: ✅ Comprehensive troubleshooting guide  
**Last Updated**: 2024  
**Found an issue not listed?** Open an issue or check inline code comments
