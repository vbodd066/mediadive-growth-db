# Data Sources & Integration Guide

## Overview

MediaDive Growth DB now integrates data from multiple public databases to build a comprehensive, multi-organism training dataset for the CVAE model. This document describes each data source, how to access them, and integration details.

---

## 1. BacDive - Bacterial Diversity Culturomics

### What is BacDive?

**BacDive** (Bacterial Diversity) is a curated database of bacterial strain characterization data maintained by the DSMZ (Deutsche Sammlung von Mikroorganismen und Zellkulturen).

- **Organisms**: Bacteria and Archaea
- **Coverage**: 30,000+ characterized strains
- **Data**: Growth conditions, metabolism, phenotypes, 16S rRNA genes
- **URL**: https://bacdive.dsmz.de/

### Available Data

| Data Type | Example | Notes |
|-----------|---------|-------|
| Culture temperature | 37°C, 4-40°C range | Mesophile, thermophile, psychrophile |
| pH range | 6.5-8.0, acidophile | Optimal and tolerated ranges |
| Oxygen requirement | Aerobic, facultative, anaerobic | Obligate requirements |
| Salinity | 0.5-5% NaCl | Halophile tolerance |
| Carbon sources | Glucose, acetate, lactose | Metabolic substrates |
| Media types | LB, M9, TSB | Laboratory media |
| Nitrogen sources | Ammonia, nitrate, N2 fixation | Nitrogen metabolism |

### API Integration

**Module**: [src/ingest/fetch_bacdive.py](src/ingest/fetch_bacdive.py)

**Key Functions**:
```python
from src.ingest.fetch_bacdive import (
    search_bacdive,
    fetch_strain_details,
    ingest_bacdive_strain,
    search_and_ingest_bacdive,
)

# Search for strains
results = search_bacdive("Escherichia", limit=10)

# Fetch detailed info
strain_data = fetch_strain_details(strain_id=1)

# Ingest into database
ingest_bacdive_strain(strain_id=1, organism_type="bacteria")

# Batch ingest
count = search_and_ingest_bacdive("thermophil", limit=50)
```

### API Limitations

- **Rate limit**: 3 requests/second
- **Caching**: Results cached in `data/raw/bacdive/cache/`
- **Authentication**: None required (public API)
- **No API key needed**: Rate limit enforced server-side

### Usage

```bash
# Ingest bacterial strains
make ingest-bacteria-bacdive

# Or via script
python -m scripts.ingest_all_organisms --bacteria --bacdive-limit 500
```

---

## 2. NCBI Entrez - Genome & Taxonomy Data

### What is NCBI Entrez?

**NCBI Entrez** provides unified access to multiple biomedical databases including:
- **GenBank**: Sequence records
- **Assembly**: Genome assemblies
- **Taxonomy**: Organism classification
- **PubMed**: Scientific literature abstracts

- **URL**: https://www.ncbi.nlm.nih.gov/
- **E-utilities**: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/

### Databases Used

#### Assembly Database (Genomes)

| Organism Type | Search Query | Coverage | Example |
|---------------|--------------|----------|---------|
| Fungi | `fungi[Organism] AND complete genome` | 1000s | Saccharomyces, Aspergillus |
| Protists | `protist[Organism] AND complete genome` | 100s | Tetrahymena, Paramecium |
| Archaea | `archaea[Organism] AND complete genome` | 100s | Methanococcus, Thermoplasma |

#### Taxonomy Database

Provides:
- Organism names and synonyms
- Taxonomic hierarchy
- Host organism information
- Metabolic characteristics

#### Nucleotide Database

Stores actual genome sequences:
- FASTA format download
- Sequence statistics
- GC content
- Feature annotations

### API Integration

**Module**: [src/ingest/fetch_ncbi_organisms.py](src/ingest/fetch_ncbi_organisms.py)

**Key Functions**:
```python
from src.ingest.fetch_ncbi_organisms import (
    search_fungal_genomes,
    search_protist_genomes,
    fetch_ncbi_taxonomy,
    ingest_fungal_species,
    ingest_protist_species,
)

# Search
fungal_genomes = search_fungal_genomes(genus="Saccharomyces", limit=50)

# Ingest
fungi_count = ingest_fungal_species(limit=100)
protist_count = ingest_protist_species(limit=50)

# Get taxonomy
tax_data = fetch_ncbi_taxonomy(taxid=4932)  # S. cerevisiae
```

### E-utilities Configuration

```python
# In environment or config
NCBI_TOOL = "mediadive_cvae"           # Identify your software
NCBI_EMAIL = "your.email@example.com"   # Contact if issues
NCBI_API_KEY = "your_api_key"          # Optional, for higher limits
```

**Rate Limits**:
- **Without API key**: 3 requests/second
- **With API key**: 10 requests/second
- **Batch operations**: Use EPost + EFetch to minimize requests

**Get an API Key**:
1. Create NCBI account: https://www.ncbi.nlm.nih.gov/account/
2. Login and go to Account Settings
3. Create new API Key
4. Add to `.env`: `NCBI_API_KEY=your_key`

### Usage

```bash
# Ingest fungi
make ingest-fungi-ncbi

# Ingest protists
make ingest-protists-ncbi

# Both
make ingest-all-organisms

# Custom
python -m scripts.ingest_all_organisms \
    --fungi --fungal-genus Aspergillus \
    --protists --ncbi-limit 200
```

---

## 3. PubMed Literature Mining

### Purpose

Extract growth condition information from published research abstracts:
- Culture temperature ranges
- pH optima
- Media formulations
- Carbon/nitrogen source preferences
- Oxygen requirements

### Integration

**Module**: [src/ingest/enrich_growth_conditions.py](src/ingest/enrich_growth_conditions.py)

**Key Functions**:
```python
from src.ingest.enrich_growth_conditions import (
    search_pubmed_growth_conditions,
    extract_growth_params_from_abstract,
    enrich_organism_conditions,
)

# Search PubMed for organism
articles = search_pubmed_growth_conditions("Bacillus subtilis", limit=10)

# Parse abstracts
for article in articles:
    params = extract_growth_params_from_abstract(article['abstract'])
    print(params)  # pH, temps, media found

# Comprehensive enrichment
conditions = enrich_organism_conditions("Bacillus subtilis")
```

### Features

- **Text parsing**: Regex-based extraction of pH, temperature, media names
- **Organism name search**: Looks for organism-specific growth data
- **Confidence scoring**: Assigns confidence to inferred conditions
- **Bias correction**: Accounts for publication bias toward well-known media

---

## 4. Curated Organism-Media Mappings

### Purpose

Provide high-confidence mappings from common organisms to their preferred growth media, derived from:
- Laboratory standards
- Literature consensus
- Organism databases

### Source Data

**File**: [src/ingest/enrich_growth_conditions.py](src/ingest/enrich_growth_conditions.py) → `create_curated_growth_map()`

**Example Mappings**:
```python
{
    "Escherichia coli": [
        ("48", 0.95),   # LB medium (95% confidence)
        ("1", 0.90),    # Nutrient medium
        ("2", 0.85),    # Glucose medium
    ],
    "Saccharomyces cerevisiae": [
        ("50", 0.95),   # YPD medium
        ("51", 0.85),   # Rich medium
    ],
    "Thermus aquaticus": [
        ("10", 0.90),   # High-temperature medium
    ],
}
```

**Confidence Scores**:
- 0.95+: Unanimous literature consensus
- 0.80-0.95: Strong preference based on multiple sources
- 0.60-0.80: Viable but not optimal
- <0.60: Rare or marginal growth

### Application

```bash
# Apply curated mappings
python -m scripts.ingest_all_organisms --apply-curated

# Or within larger pipeline
make ingest-all-organisms
```

---

## 5. Growth Condition Enrichment

### Taxonomic Inference

Automatically infer likely growth conditions from organism names:

```
Examples:
- "Thermoplasma acidophilum" → thermophile + acidophile
- "Halobacterium salinarum" → halophile (salt-lover)
- "Clostridium botulinum" → anaerobic
- "Psychromonas" → psychrophile (cold-loving)
```

**Extracted Parameters**:
- Temperature preference (psychrophile, mesophile, thermophile)
- pH preference (acidophile, neutrophile, alkaliphile)
- Oxygen requirement (aerobic, facultative, anaerobic)
- Salinity tolerance

### Literature Integration

For each organism:
1. Search PubMed for growth condition publications
2. Parse abstracts for pH, temperature, media names
3. Extract carbon/nitrogen sources
4. Aggregate confidence scores

---

## Data Flow Architecture

```
BacDive API          NCBI E-utils         PubMed API
     ↓                    ↓                    ↓
[Strain Data]      [Genome Metadata]    [Literature]
     ↓                    ↓                    ↓
  Taxonomy          Organism Type       Growth Params
  Growth Cond.      Sequences            Media Names
  Media Pref.       Tax ID               Carbon Sources
     ↓                    ↓                    ↓
┌────────────────────────────────────────────────────┐
│        Enrichment & Integration Layer              │
│  - Taxonomy inference                             │
│  - Confidence scoring                             │
│  - Duplicate handling                             │
│  - Cross-database linking                         │
└────────────────────────────────────────────────────┘
     ↓                    ↓                    ↓
   Strains          Genomes              Growth Links
   (bacteria)     (all types)         (genome→media)
     ↓                    ↓                    ↓
┌────────────────────────────────────────────────────┐
│              SQLite Database                      │
│  - strains           - genomes                    │
│  - genome_embeddings - genome_growth             │
│  - strain_growth     - ingest_log                │
└────────────────────────────────────────────────────┘
     ↓
   CVAE Dataset Builder
     ↓
 (genome, media, growth) triples
```

---

## Database Tables

### New/Updated Tables

```sql
-- Genomes (stores all organisms)
genomes
├── genome_id (PK)
├── organism_name
├── organism_type (bacteria|fungi|protist|archea)
├── taxid (NCBI taxonomy ID)
├── gc_content
├── sequence_length
└── fasta_path

-- Growth observations
genome_growth
├── genome_id (FK)
├── media_id (FK)
├── growth (boolean)
├── confidence [0-1]
└── source (bacdive|ncbi|literature|curated)

-- Strains (existing, enhanced)
strains
├── bacdive_id (new FK)
├── domain (enhanced)
└── ...
```

---

## Complete Ingestion Pipeline

### Quick Start

```bash
# Initialize database
make init-db

# Ingest all data
make ingest-all-organisms

# This runs:
# 1. BacDive bacteria
# 2. NCBI fungi
# 3. NCBI protists
# 4. Curated mappings
```

### Step-by-Step

```bash
# 1. Bacteria only
python -m scripts.ingest_all_organisms --bacteria

# 2. Add fungi
python -m scripts.ingest_all_organisms --fungi

# 3. Add protists
python -m scripts.ingest_all_organisms --protists

# 4. Enrich with conditions (requires API keys)
python -m scripts.ingest_all_organisms \
    --all \
    --enrich-conditions \
    --apply-curated
```

### Custom Queries

```bash
# Specific BacDive search
python -m scripts.ingest_all_organisms \
    --bacteria \
    --bacdive-query "Thermophile" \
    --bacdive-limit 200

# Specific fungal genus
python -m scripts.ingest_all_organisms \
    --fungi \
    --fungal-genus "Aspergillus" \
    --ncbi-limit 500
```

---

## Configuration

### Environment Variables

```bash
# .env file
NCBI_API_KEY=your_ncbi_api_key         # Optional, for higher rate limits
NCBI_TOOL=mediadive_cvae               # Software identifier
NCBI_EMAIL=your.email@example.com      # Contact email

BACDIVE_BASE_URL=https://bacdive.dsmz.de/api
BACDIVE_REQUEST_DELAY=0.5              # 3 requests/second limit
```

### Rate Limit Handling

**BacDive**: 0.5s delay between requests (3/sec limit)

**NCBI**: 
- Without API key: 0.33s delay (3/sec)
- With API key: 0.1s delay (10/sec)

**PubMed**: Same as NCBI (part of Entrez)

---

## Data Quality & Validation

### Quality Checks

1. **Taxonomy validation**: All organisms checked against NCBI taxonomy
2. **Duplicate detection**: Cross-database organism deduplication
3. **Confidence scoring**: All assertions include confidence [0-1]
4. **Source tracking**: Original data source recorded (bacdive, ncbi, literature, curated)

### Statistics

Check ingestion progress:

```python
from src.ingest.fetch_bacdive import get_bacdive_statistics
from src.ingest.fetch_ncbi_organisms import get_ncbi_statistics
from src.ingest.enrich_growth_conditions import get_enrichment_statistics

print(get_bacdive_statistics())
print(get_ncbi_statistics())
print(get_enrichment_statistics())
```

Or via SQL:

```sql
-- Count organisms by type
SELECT organism_type, COUNT(*) as count
FROM genomes
GROUP BY organism_type;

-- Count growth observations
SELECT source, COUNT(*) as count
FROM genome_growth
WHERE growth = 1
GROUP BY source;
```

---

## Future Data Sources

Potential additions:

1. **IMG/M** (Integrated Microbial Genomes)
   - Metagenomics data
   - Environmental samples

2. **JGI (Joint Genome Institute)**
   - Reference genomes
   - Fungal genomes

3. **UniProt**
   - Protein sequences
   - Functional annotations
   - Organism metadata

4. **RAST (Rapid Annotation using Subsystems Technology)**
   - Gene annotations
   - Metabolic pathways

5. **BioCyc**
   - Metabolic networks
   - Growth media formulations

6. **MGnify**
   - Metagenomic samples
   - Environmental context

---

## Troubleshooting

### "Connection refused" errors
- Check internet connectivity
- BacDive/NCBI servers may be down
- Use cache: previously downloaded data in `data/raw/` directories

### Rate limit exceeded
- **BacDive**: Automatically backs off with delay
- **NCBI**: Get API key for higher rate limit
- Distribute large jobs across time (weekends/nights)

### "Organism not found"
- Check spelling
- Try parent genus/family
- May not be in chosen database

### Empty results
- Database may not have data
- Queries too restrictive
- Try broader search terms

---

## Citation & Attribution

When using data from these sources in publications, cite:

**BacDive**:
> Sohngen, C., et al. (2016). BacDive - The Bacterial Diversity Metadatabase. 
> Nucleic Acids Research, 44(D1), D581-D585.

**NCBI**:
> Sayers, E. W., et al. (2021). Database resources of the National Center for 
> Biotechnology Information. Nucleic Acids Research, 49(D1), D10-D17.

**PubMed**:
> National Center for Biotechnology Information. PubMed Help. 
> https://pubmed.ncbi.nlm.nih.gov/help/

---

## Support

For issues with:
- **BacDive**: https://bacdive.dsmz.de/
- **NCBI**: https://www.ncbi.nlm.nih.gov/books/NBK3833/
- **This integration**: See module docstrings and inline comments
