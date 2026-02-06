# Getting Started with MediaDive Growth DB

**Welcome!** This guide will get you up and running in 5 minutes.

---

## Choose Your Path

### Path 1️⃣: "Just Run It" (5 minutes)
Perfect if you want to ingest data and start training immediately.

```bash
# 1. Setup environment
cp .env.example .env
# Add your email: NCBI_EMAIL=your@email.com (required for fungi/protists)

# 2. Initialize database
make init-db

# 3. Run the complete pipeline
make integrate-mediadive-ncbi

# 4. Check results
make integrate-stats

# 5. Start training
make train-cvae-all
```

**What you get**: 
- 30,000+ bacterial strains from BacDive
- 1,000+ fungal genomes from NCBI
- 100+ protist genomes from NCBI
- 10,000-50,000 training pairs
- Ready for CVAE training

**Time**: 3-5 hours total (mostly waiting for training)

---

### Path 2️⃣: "Understand First" (30 minutes)
Perfect if you want to learn how everything works before running.

```bash
# 1. Read the overview
# See: README.md (top of repo)

# 2. Understand the architecture
# See: docs/INDEX.md → Architecture section

# 3. Review the data flow
# See: MEDIADIVE_INTEGRATION_WORKFLOW.md

# 4. Then run
make integrate-mediadive-ncbi
```

**What you learn**:
- How MediaDive data links to NCBI genomes
- How growth observations propagate
- How training dataset is constructed
- What each command does

---

### Path 3️⃣: "Customize It" (1-2 hours)
Perfect if you want to modify pipelines or try different parameters.

```bash
# 1. Read the complete guide
# See: docs/guides/mediadive_ncbi_linking.md

# 2. Understand the Python API
# See: docs/COMMAND_REFERENCE.md → Python API Usage

# 3. Customize and run
python -m scripts.integrate_mediadive_ncbi \
    --link-species \
    --max-per-species 10 \
    --limit-species 100

# 4. Check parameters
python -m scripts.integrate_mediadive_ncbi --help
```

**What you can customize**:
- Number of genomes per species
- Which organisms to include
- Confidence score thresholds
- Report generation

---

## Quick Reference

### Core Commands

```bash
# ═══════════════════════════════════════════════════════════════
# Data Pipeline
# ═══════════════════════════════════════════════════════════════

make init-db                    # Setup database schema
make integrate-mediadive-ncbi   # Link + propagate + build dataset (FULL)
make integrate-link-species     # Link phase only
make integrate-propagate        # Propagate phase only
make integrate-stats            # View statistics

# ═══════════════════════════════════════════════════════════════
# Feature Engineering
# ═══════════════════════════════════════════════════════════════

make features                   # Build all features

# ═══════════════════════════════════════════════════════════════
# Training
# ═══════════════════════════════════════════════════════════════

make train-cvae-all             # Full curriculum learning
make train-cvae                 # Single organism (default bacteria)

# ═══════════════════════════════════════════════════════════════
# Legacy (Phase 1 only)
# ═══════════════════════════════════════════════════════════════

make ingest                     # MediaDive original data only
make ingest-bacteria-bacdive    # BacDive bacteria
make ingest-fungi-ncbi          # NCBI fungi
```

---

## Environment Setup

### Required

```bash
# Copy template
cp .env.example .env

# Edit .env and add your NCBI email
NCBI_EMAIL=your@email.com

# Optional but RECOMMENDED: Get higher API rate limits
# Visit: https://www.ncbi.nlm.nih.gov/account/
# Create API key, add to .env:
NCBI_API_KEY=your_api_key_here
```

### Optional

```bash
# Adjust request delays if hitting rate limits
BACDIVE_REQUEST_DELAY=1.0    # Longer delays between BacDive requests
```

---

## Typical Workflow

### Scenario 1: First Time Setup

```bash
# 1. Clone and install
git clone <repo> && cd mediadive-growth-db
pip install -e ".[ml,viz,dev]"

# 2. Setup env
cp .env.example .env
# Edit .env and add NCBI_EMAIL

# 3. Initialize
make init-db

# 4. Ingest data
make integrate-mediadive-ncbi
# Wait 10-30 minutes...

# 5. Build features
make features
# Wait 5-10 minutes...

# 6. Train
make train-cvae-all
# Wait 2-4 hours on GPU...

# 7. Done!
```

### Scenario 2: Adding New Organisms (Later)

```bash
# Add specific organism type
python -m scripts.ingest_all_organisms --fungi

# Or with enrichment
python -m scripts.ingest_all_organisms --bacteria --enrich-conditions

# Rebuild features
make features

# Retrain
make train-cvae-all
```

### Scenario 3: Debugging/Inspection

```bash
# Check what's in database
make integrate-stats

# View statistics dashboard
sqlite3 data/processed/mediadive.db \
  "SELECT organism_type, COUNT(*) FROM genomes GROUP BY organism_type;"

# See recent errors
tail -50 mediadive_ingest.log

# See help for any script
python -m scripts.integrate_mediadive_ncbi --help
```

---

## Expected Results

### After `make integrate-mediadive-ncbi`

```
Database Statistics:
├─ Organisms
│  ├─ Bacteria:     ~30,000 strains (BacDive)
│  ├─ Archaea:      ~500 genomes (NCBI)
│  ├─ Fungi:        ~1,000 genomes (NCBI)
│  └─ Protists:     ~100 genomes (NCBI)
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│  TOTAL:           ~31,600 organisms
│
├─ Growth Links
│  ├─ Positive:     ~30,000 (growth observed)
│  ├─ Negative:     ~20,000 (no growth)
│  └─ Confidence:   0.5-0.95 (scored by quality)
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│  TOTAL:           ~50,000 training pairs
│
└─ Media Types
   └─ Unique:       ~100 formulations
```

### After `make features`

```
Features Generated:
├─ Genome embeddings:    ~31,600 k-mer vectors
├─ Media compositions:   ~100 ingredient vectors
└─ Growth labels:        Binary (0/1)

Dataset Ready:
└─ Location: data/processed/mediadive_ncbi_integrated_dataset.json
   Contains: (genome_embedding, media_composition, growth_label, metadata)
```

### After `make train-cvae-all`

```
CVAE Model Trained:
├─ Checkpoint 1: Bacteria (20 epochs)
├─ Checkpoint 2: Archaea (10 epochs)
├─ Checkpoint 3: Fungi (5 epochs)
└─ Checkpoint 4: Protists (2 epochs)

Can now:
✅ Predict growth for new organism-media pairs
✅ Generate novel media for unseen species
✅ Visualize organism relationships
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Check internet, NCBI/BacDive may be down, retry later |
| "NCBI rate limit" | Add `NCBI_API_KEY` to .env for 10x higher limits |
| "Database locked" | Close other processes using DB, or restart |
| "No results found" | Try broader search terms, some organisms have limited data |
| "Memory error" | Reduce batch size: `--batch-size 16` or use `--limit-species 100` |

### Getting Help

```bash
# See available commands
make help

# Get script documentation
python -m scripts.integrate_mediadive_ncbi --help
python -m scripts.train_cvae --help

# Check logs
tail -f mediadive_ingest.log

# Read detailed guides
# See: docs/TROUBLESHOOTING.md
# See: docs/guides/
```

---

## Next Steps

1. **Run one of the three paths above**

2. **After data ingestion**, explore results:
   ```bash
   make integrate-stats
   ```

3. **Read specialized guides** for deeper learning:
   - [Media-NCBI Linking Guide](docs/guides/mediadive_ncbi_linking.md)
   - [CVAE Training Guide](docs/guides/cvae_training.md)
   - [API Reference](docs/guides/api_reference.md)

4. **Customize** for your research:
   - Adjust organism selections
   - Tune hyperparameters
   - Add new data sources
   - Modify the model architecture

5. **Validate** your model:
   - Check growth prediction accuracy
   - Generate novel media predictions
   - Compare with lab results

---

## Documentation Map

| Document | When to Read | Read Time |
|----------|--------------|-----------|
| This file (GETTING_STARTED) | **First** | 5 min |
| [README.md](../README.md) | Overview/Architecture | 10 min |
| [docs/INDEX.md](INDEX.md) | Full navigation | 2 min |
| [docs/COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) | Commands/API | 10 min |
| [docs/guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md) | Integration details | 20 min |
| [docs/guides/cvae_training.md](guides/cvae_training.md) | Model training | 20 min |
| [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) | When stuck | 10 min |

---

## Quick Checklist

- [ ] Cloned repo
- [ ] Installed dependencies: `pip install -e ".[ml,viz,dev]"`
- [ ] Set up .env with `NCBI_EMAIL`
- [ ] Ran `make init-db`
- [ ] Started ingestion: `make integrate-mediadive-ncbi`
- [ ] Checked stats: `make integrate-stats`
- [ ] Built features: `make features`
- [ ] Started training: `make train-cvae-all`
- [ ] Read getting started guide (this file)
- [ ] Bookmarked [docs/INDEX.md](INDEX.md) for later reference

---

**All set!** 🚀 See Path 1/2/3 above to get started.

Questions? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or check [docs/](.) for detailed guides.
