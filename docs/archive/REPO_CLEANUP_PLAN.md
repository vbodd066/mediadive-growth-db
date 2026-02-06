# Repository Cleanup & Consolidation Plan

## Executive Summary

The repo has grown through 4 implementation phases with significant documentation overlap:
- **14 documentation files** (many with duplicate content)
- **7 scripts** (some duplicative, some specialized)
- **No clear docs/ folder structure**
- **No archive for deprecated versions**

**Goal**: Consolidate to 4-5 core docs + clear folder structure

---

## Part 1: Documentation Analysis

### Current Documentation (14 files)

#### Group A: System Overview (Overlapping)
| File | Purpose | Lines | Overlap | Status |
|------|---------|-------|---------|--------|
| **readme.md** | Main project overview | 256 | ✅ Current | **KEEP** |
| **SYSTEM_OVERVIEW.md** | Visual architecture | 350 | ~80% with readme | **ARCHIVE** |
| **IMPLEMENTATION_SUMMARY.md** | Technical summary | 703 | ~70% with others | **ARCHIVE** |
| **COMPLETION_SUMMARY.md** | Phase summary | 373 | ~90% dup | **ARCHIVE** |
| **PROJECT_COMPLETION_CHECKLIST.md** | Implementation checklist | 452 | ~85% dup | **ARCHIVE** |

**Recommendation**: Keep readme.md only, move others to docs/archive/

---

#### Group B: Getting Started (Overlapping)
| File | Purpose | Lines | Overlap | Status |
|------|---------|-------|---------|--------|
| **QUICK_START.md** | Fast reference | 150 | ~60% with COMMAND_REFERENCE | **ARCHIVE** |
| **COMMAND_REFERENCE.md** | Command examples | 400 | ✅ More complete | **KEEP** |
| **DOCUMENTATION_INDEX.md** | Navigation guide | 500 | ✅ Navigation | **KEEP** |

**Recommendation**: Keep COMMAND_REFERENCE + DOCUMENTATION_INDEX, archive QUICK_START

---

#### Group C: Integration-Specific (Specialized)
| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| **MEDIADIVE_NCBI_INTEGRATION.md** | MediaDive-NCBI linking guide | 450 | **KEEP** |
| **MEDIADIVE_INTEGRATION_WORKFLOW.md** | Architecture & data flow | 500 | **KEEP** |
| **MEDIADIVE_INTEGRATION_COMPLETE.md** | Executive summary | 700 | **MERGE into MEDIADIVE_NCBI_INTEGRATION.md** |
| **DATA_SOURCES.md** | API reference | 850+ | **KEEP** |
| **CVAE_GUIDE.md** | Model details | 550 | **KEEP** |
| **CVAE_IMPLEMENTATION.md** | Training guide | 350 | **KEEP** |
| **CVAE_QUICK_START.md** | Notebook reference | 250 | **MERGE into CVAE_IMPLEMENTATION.md** |

**Recommendation**: Merge related files, keep specialized guides

---

### Current Script Structure Analysis

#### Group A: Foundation/Legacy
| Script | Purpose | Uses | Status |
|--------|---------|------|--------|
| **run_ingest.py** | MediaDive ingestion (8 steps) | Legacy MediaDive API | **OK** (still valid for phase 1) |
| **train.py** | Simple training entry | sklearn/neural/vae | **DEPRECATED** (use train_cvae.py instead) |

#### Group B: Current/Active
| Script | Purpose | Uses | Status |
|--------|---------|------|--------|
| **train_cvae.py** | CVAE training + curriculum | Full multi-organism pipeline | **CURRENT** |
| **build_features.py** | Feature engineering | Genome embeddings | **CURRENT** |
| **ingest_all_organisms.py** | Multi-source ingestion | BacDive, NCBI, PubMed | **CURRENT** |

#### Group C: Newer/Latest
| Script | Purpose | Uses | Status |
|--------|---------|------|--------|
| **integrate_mediadive_ncbi.py** | MediaDive-NCBI linking | Linking + propagation + dataset building | **LATEST** |

**Recommendation**:
- Archive: `train.py` (use `train_cvae.py` instead)
- Keep all others but clarify when to use in docs

---

## Part 2: Proposed New Structure

```
mediadive-growth-db/
│
├── README.md                          # Main entry point (REWRITTEN)
│
├── docs/
│   ├── INDEX.md                       # Navigation hub (updated)
│   ├── GETTING_STARTED.md             # New consolidated guide
│   │
│   ├── guides/
│   │   ├── mediadive_ncbi_linking.md  # (merged from 3 files)
│   │   ├── cvae_training.md           # (merged from 2 files)
│   │   └── api_reference.md           # (from DATA_SOURCES.md)
│   │
│   ├── command_reference.md           # (from COMMAND_REFERENCE.md)
│   ├── workflows.md                   # Common workflows
│   ├── troubleshooting.md             # Debugging & FAQs
│   │
│   └── archive/
│       ├── IMPLEMENTATION_SUMMARY.md
│       ├── COMPLETION_SUMMARY.md
│       ├── PROJECT_COMPLETION_CHECKLIST.md
│       ├── SYSTEM_OVERVIEW.md
│       ├── QUICK_START.md
│       ├── MEDIADIVE_INTEGRATION_COMPLETE.md
│       ├── CVAE_QUICK_START.md
│       └── README.md (explaining what went here)
│
├── scripts/
│   ├── run_ingest.py               # Phase 1: MediaDive only (legacy but valid)
│   ├── train_cvae.py               # Phase 2+: CVAE with multi-organism
│   ├── build_features.py           # Feature extraction
│   ├── ingest_all_organisms.py     # Phase 3a: Multi-source ingest
│   ├── integrate_mediadive_ncbi.py # Phase 3b: MediaDive-NCBI linking (LATEST)
│   └── train.py                    # DEPRECATED → see train_cvae.py
│
├── src/
│   └── ... (no changes)
```

---

## Part 3: Consolidation Actions

### 1. Create docs/ Folder Structure

```bash
mkdir -p docs/{guides,archive}
```

### 2. Create New Consolidated Documents

#### docs/INDEX.md
- Updated navigation hub
- Replace DOCUMENTATION_INDEX.md

#### docs/GETTING_STARTED.md
- Combined from QUICK_START.md + COMMAND_REFERENCE intro
- 3 clear paths: "Just run it", "Understand first", "Customize"

#### docs/guides/mediadive_ncbi_linking.md
- Merge: MEDIADIVE_NCBI_INTEGRATION.md + MEDIADIVE_INTEGRATION_COMPLETE.md
- Keep: MEDIADIVE_INTEGRATION_WORKFLOW.md (rename → data_flow.md if needed)

#### docs/guides/cvae_training.md
- Merge: CVAE_IMPLEMENTATION.md + CVAE_QUICK_START.md
- Keep: CVAE_GUIDE.md as supplementary

#### docs/guides/api_reference.md
- Rename from DATA_SOURCES.md (less jargony title)

#### docs/COMMAND_REFERENCE.md
- Move from root (already comprehensive)

#### docs/TROUBLESHOOTING.md
- Extract troubleshooting sections from various docs
- Add common error patterns

### 3. Archive Old Documentation

```
docs/archive/
├── IMPLEMENTATION_SUMMARY.md       (703 lines - Phase 2 summary)
├── COMPLETION_SUMMARY.md           (373 lines - Phase 3a summary)
├── PROJECT_COMPLETION_CHECKLIST.md (452 lines - Implementation checklist)
├── SYSTEM_OVERVIEW.md              (350 lines - Architecture diagram)
├── QUICK_START.md                  (150 lines - Fast reference, subsumed by GETTING_STARTED)
├── MEDIADIVE_INTEGRATION_COMPLETE.md (700 lines - Merging into linking guide)
├── CVAE_QUICK_START.md             (250 lines - Merging into training guide)
└── README.md                       (Explaining this archive)
```

### 4. Update Root README.md

```markdown
# MediaDive Growth DB

[Keep intro + architecture]

## Quick Navigation

- **New to the project?** → [Getting Started](docs/GETTING_STARTED.md)
- **Want commands?** → [Command Reference](docs/COMMAND_REFERENCE.md)
- **Need help?** → [Troubleshooting](docs/TROUBLESHOOTING.md)
- **Full docs?** → [Documentation Index](docs/INDEX.md)

## Installation

[Keep this section]

## Roadmap

[Keep this section]
```

### 5. Deprecate train.py

Add warning to scripts/train.py:

```python
"""
⚠️ DEPRECATED: This script is for basic sklearn/VAE only.

For Conditional VAE with multi-organism support, use:
  python -m scripts.train_cvae --help

See: docs/guides/cvae_training.md
"""
```

---

## Part 4: Implementation Order

### Phase 1: Create New Structure (30 min)
1. Create docs/ folders
2. Create docs/INDEX.md (navigation)
3. Create docs/GETTING_STARTED.md (consolidated guide)
4. Create docs/TROUBLESHOOTING.md

### Phase 2: Consolidate Guides (1 hour)
5. Merge → docs/guides/mediadive_ncbi_linking.md
6. Merge → docs/guides/cvae_training.md
7. Rename → docs/guides/api_reference.md (from DATA_SOURCES.md)
8. Move → docs/COMMAND_REFERENCE.md

### Phase 3: Archive & Update (30 min)
9. Create docs/archive/README.md
10. Move old files to docs/archive/
11. Update README.md with new navigation
12. Add deprecation warning to train.py
13. Update Makefile comments

### Phase 4: Verification (15 min)
14. Verify all links work
15. Test old links still accessible (docs/archive/)
16. Update DOCUMENTATION_INDEX.md → docs/INDEX.md

---

## Part 5: Results

### Before
- 14 top-level .md files
- Confusing what to read first
- Significant duplication
- No archive of history
- No clear docs/ folder

### After
- 5-6 core .md files in root/docs/
- Clear navigation via docs/INDEX.md
- No duplication (merged into guides/)
- Complete history in docs/archive/
- Professional folder structure
- ~40% reduction in doc files to sort through

### File Reduction
- **Before**: 14 documentation files + 7 scripts = 21 files
- **After**: 
  - Root: 5 files (README.md + pyproject.toml + Makefile + .env + .gitignore)
  - docs/: 8-10 files (guides + consolidated docs)
  - docs/archive/: 7 files (old versions)
  - scripts/: 7 files (4 current + 1 deprecated + 2 supporting)
  
**Result**: Cleaner root, organized docs/, preserved history

---

## Part 6: Files to Keep vs Archive

### KEEP (Active/Current)
- ✅ readme.md (updated with navigation)
- ✅ COMMAND_REFERENCE.md → docs/COMMAND_REFERENCE.md
- ✅ DOCUMENTATION_INDEX.md → docs/INDEX.md
- ✅ MEDIADIVE_NCBI_INTEGRATION.md → docs/guides/mediadive_ncbi_linking.md
- ✅ MEDIADIVE_INTEGRATION_WORKFLOW.md (still useful for architecture)
- ✅ DATA_SOURCES.md → docs/guides/api_reference.md
- ✅ CVAE_GUIDE.md (supplementary)
- ✅ CVAE_IMPLEMENTATION.md → docs/guides/cvae_training.md

### ARCHIVE (Historical/Superseded)
- 📦 IMPLEMENTATION_SUMMARY.md
- 📦 COMPLETION_SUMMARY.md
- 📦 PROJECT_COMPLETION_CHECKLIST.md
- 📦 SYSTEM_OVERVIEW.md
- 📦 QUICK_START.md
- 📦 MEDIADIVE_INTEGRATION_COMPLETE.md
- 📦 CVAE_QUICK_START.md

### DEPRECATE (Superseded by newer version)
- ⚠️ scripts/train.py (use train_cvae.py)

---

## Benefits of Reorganization

1. **Clarity**: Clear which doc to read first (README → docs/INDEX → specific guide)
2. **Maintainability**: No duplicate content to update
3. **Discoverability**: New users see 5 docs, not 14
4. **History**: Archive preserves all work/decisions
5. **Professionalism**: Standard docs/ folder structure
6. **Navigation**: All links in docs/INDEX.md
7. **Scalability**: Easy to add new docs to guides/

---

## Action Required

Run cleanup script (to be created) that:
1. Creates folder structure
2. Merges and renames files
3. Updates all cross-references
4. Creates archive README
5. Deprecates train.py
6. Updates root README
7. Verifies all links

**Estimated time**: 2-3 hours
**Risk level**: Low (all files preserved in archive)
**Impact**: High (much cleaner, more professional repo)
