# Quick Start: Multi-Organism Ingestion & CVAE Training

**TL;DR**: Run one command to ingest all organism data and prepare for CVAE training.

---

## 30-Second Setup

```bash
cd mediadive-growth-db

# 1. Set up environment
cp .env.example .env
# Edit .env: add NCBI_EMAIL=your@email.com

# 2. Initialize database
make init-db

# 3. Ingest all data (bacteria + fungi + protists)
make ingest-all-organisms

# 4. Done! Database now has 30K+ organisms
```

---

## Common Commands

### Ingest

```bash
# All organisms with curated mappings
make ingest-all-organisms

# Just bacteria
make ingest-bacteria-bacdive

# Just fungi
make ingest-fungi-ncbi

# Just protists
make ingest-protists-ncbi

# With literature enrichment
make ingest-with-conditions
```

### Build Features

```bash
# Extract k-mer embeddings from all organisms
python -m scripts.build_features --compute-genome-embeddings --all-organisms

# Build training dataset (genome embedding, media composition, growth)
python -m scripts.build_features --build-genome-media-dataset
```

### Train CVAE

```bash
# Full curriculum learning
make train-cvae-all

# Or custom
python -m scripts.train_cvae \
    --epochs 200 \
    --batch-size 32 \
    --curriculum-learning
```

---

## Check Progress

```bash
# Count organisms by type
sqlite3 data/processed/mediadive.db \
  "SELECT organism_type, COUNT(*) FROM genomes GROUP BY organism_type;"

# Count growth links
sqlite3 data/processed/mediadive.db \
  "SELECT source, COUNT(*) FROM genome_growth WHERE growth=1 GROUP BY source;"

# Check embeddings
sqlite3 data/processed/mediadive.db \
  "SELECT COUNT(*) FROM genome_embeddings;"
```

---

## Data Sources

| Source | Organisms | Example Query |
|--------|-----------|---------------|
| **BacDive** | Bacteria, Archaea | `--bacteria` |
| **NCBI** | Fungi, Protists, more Archaea | `--fungi --protists` |
| **PubMed** | All (literature) | `--enrich-conditions` |
| **Curated** | All (expert maps) | `--apply-curated` |

---

## Expected Results

```
After: make ingest-all-organisms

✅ Bacteria:     ~30,000 strains (BacDive)
✅ Archaea:      ~500 genomes (NCBI)
✅ Fungi:        ~1,000 genomes (NCBI)
✅ Protists:     ~100 genomes (NCBI)
─────────────────────────────
   TOTAL:        ~31,600 organisms
   
✅ Growth links: ~50,000 genome→media associations
✅ Literature:   ~10,000 condition inferences
✅ Coverage:     100+ media types

Database size: ~500MB
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| **[DATA_SOURCES.md](DATA_SOURCES.md)** | Complete API guide |
| **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** | Full architecture & details |
| **[CVAE_QUICK_START.md](CVAE_QUICK_START.md)** | CVAE training guide |
| **[readme.md](readme.md)** | Overview & architecture |

---

## Environment Variables

```bash
# Required for NCBI (fungi, protists)
NCBI_EMAIL=your.email@example.com

# Optional (recommended) - higher rate limits
NCBI_API_KEY=your_api_key

# Optional - adjust if needed
BACDIVE_REQUEST_DELAY=0.5
```

**Get NCBI API Key**: https://www.ncbi.nlm.nih.gov/account/ → Account Settings → API Key

---

## Troubleshooting

### "Connection refused"
→ Check internet, servers may be down, retry later

### "NCBI rate limit"
→ Add NCBI_API_KEY to .env for 10x higher limit

### "Empty results"
→ Try broader search terms, some databases have limited coverage

### "Database locked"
→ Check no other processes using database, or restart

---

## Performance

| Task | Time |
|------|------|
| Ingest bacteria | 2-5 min |
| Ingest fungi/protists | 5-10 min |
| Build embeddings (30K genomes) | 5-10 min |
| Build dataset | 2-5 min |
| Train CVAE (GPU) | 2-4 hrs |

---

## Next Steps

1. Run ingestion: `make ingest-all-organisms`
2. Check results: See "Check Progress" above
3. Build features: `python -m scripts.build_features --compute-genome-embeddings --all-organisms`
4. Train: `make train-cvae-all`
5. Evaluate: See CVAE_QUICK_START.md

---

## Modules Used

- **BacDive**: [src/ingest/fetch_bacdive.py](src/ingest/fetch_bacdive.py)
- **NCBI**: [src/ingest/fetch_ncbi_organisms.py](src/ingest/fetch_ncbi_organisms.py)
- **Enrichment**: [src/ingest/enrich_growth_conditions.py](src/ingest/enrich_growth_conditions.py)
- **Orchestration**: [scripts/ingest_all_organisms.py](scripts/ingest_all_organisms.py)

All with comprehensive docstrings and inline comments.

---

**Status**: ✅ Ready to use

Run `make ingest-all-organisms` to get started!
