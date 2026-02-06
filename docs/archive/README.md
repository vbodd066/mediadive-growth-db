# Documentation Archive

This folder contains historical documentation from previous implementation phases.

## What's Here

These files are **superseded by newer versions** in the main `docs/` folder. They are preserved for historical reference and to understand project evolution.

### Historical Documentation

| File | Original Purpose | Replaced By | Why Archived |
|------|-----------------|-------------|--------------|
| **IMPLEMENTATION_SUMMARY.md** | Phase 2 CVAE implementation summary | [docs/guides/cvae_training.md](../guides/cvae_training.md) | Merged into consolidated guide |
| **COMPLETION_SUMMARY.md** | Phase 3a completion summary | [docs/INDEX.md](../INDEX.md) | Summary info now in navigation |
| **PROJECT_COMPLETION_CHECKLIST.md** | Implementation checklist | [REPO_CLEANUP_PLAN.md](../../REPO_CLEANUP_PLAN.md) | Superseded by cleanup plan |
| **SYSTEM_OVERVIEW.md** | Architecture diagram (ASCII) | [README.md](../../README.md) | Content incorporated into main README |
| **QUICK_START.md** | Quick command reference | [docs/GETTING_STARTED.md](../GETTING_STARTED.md) | Consolidated into getting started guide |
| **MEDIADIVE_INTEGRATION_COMPLETE.md** | MediaDive-NCBI exec summary | [docs/guides/mediadive_ncbi_linking.md](../guides/mediadive_ncbi_linking.md) | Merged into main integration guide |
| **CVAE_QUICK_START.md** | CVAE notebook reference | [docs/guides/cvae_training.md](../guides/cvae_training.md) | Merged into training guide |

---

## How to Use This Archive

### If You're New
👉 **Start with** [docs/GETTING_STARTED.md](../GETTING_STARTED.md), not here.

### If You Want Historical Context
- **What was built in Phase 2?** → Read IMPLEMENTATION_SUMMARY.md
- **What was built in Phase 3a?** → Read COMPLETION_SUMMARY.md
- **What's the implementation checklist?** → Read PROJECT_COMPLETION_CHECKLIST.md

### If You Want to Understand Evolution
1. SYSTEM_OVERVIEW.md (original architecture)
2. IMPLEMENTATION_SUMMARY.md (Phase 2: CVAE)
3. COMPLETION_SUMMARY.md (Phase 3a: Multi-organism)
4. Then → [docs/INDEX.md](../INDEX.md) for current state

---

## Why These Files Were Archived

### Problem We Solved
- **14 documentation files** at root level (confusing)
- **Significant duplication** between files
- **No clear navigation** for new users
- **No version history** for different phases

### Our Solution
- Consolidated overlapping docs into specialized guides
- Organized into `docs/` folder with clear structure
- Preserved all content (moved to archive)
- Created navigation hub ([docs/INDEX.md](../INDEX.md))

### Benefit
- **New users**: See 5-6 docs instead of 14
- **Maintainers**: No duplicate content to update
- **Historians**: All work preserved here
- **Professional**: Standard docs/ folder structure

---

## Reading Guide

### For Project Historians
**Timeline of implementation:**
1. Phase 1 (Existing): Basic MediaDive ingestion
2. Phase 2: CVAE with genome embeddings (see IMPLEMENTATION_SUMMARY.md)
3. Phase 3a: Multi-source ingest (see COMPLETION_SUMMARY.md)
4. Phase 3b: MediaDive-NCBI linking (see ../guides/mediadive_ncbi_linking.md)

### For Feature Understanding
- **How was CVAE designed?** → IMPLEMENTATION_SUMMARY.md, then CVAE_QUICK_START.md
- **How are organisms ingested?** → COMPLETION_SUMMARY.md, then ../guides/api_reference.md
- **What's the overall system?** → SYSTEM_OVERVIEW.md, then README.md

### For Debug Reference
Each original file may contain troubleshooting sections not in current docs. Check here if you hit issues.

---

## When to Reference This Archive

✅ **Use these files when:**
- Understanding historical implementation decisions
- Learning about different phases of development
- Debugging issues specific to certain components
- Tracing back how features were built

❌ **Don't use these for:**
- Getting started (use [docs/GETTING_STARTED.md](../GETTING_STARTED.md))
- Commands (use [docs/COMMAND_REFERENCE.md](../COMMAND_REFERENCE.md))
- Current architecture (use [README.md](../../README.md))
- Troubleshooting (use [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md))

---

## Archive Index

```
archive/
├── README.md (this file)
│
├── IMPLEMENTATION_SUMMARY.md        # Phase 2: CVAE architecture (703 lines)
├── COMPLETION_SUMMARY.md            # Phase 3a: Multi-source ingest (373 lines)
├── PROJECT_COMPLETION_CHECKLIST.md  # Phase 1-3 checklist (452 lines)
├── SYSTEM_OVERVIEW.md               # Original architecture (350 lines)
├── QUICK_START.md                   # Old quick reference (203 lines)
├── MEDIADIVE_INTEGRATION_COMPLETE.md # Phase 3b summary (700 lines)
└── CVAE_QUICK_START.md              # CVAE notebook guide (250 lines)

Total: ~3,500 lines of historical documentation
```

---

## Content Summary

### IMPLEMENTATION_SUMMARY.md
What: Complete CVAE implementation in Phase 2
When: After Phase 2 completion
Why: Documents architectural decisions, integration points, data flows
Key sections: Overview, BacDive module, NCBI module, Enrichment, Results

### COMPLETION_SUMMARY.md
What: Phase 3a multi-organism integration status
When: After Phase 3a completion
Why: Summary of what was delivered
Key sections: Deliverables, Code modules, Documentation, Database state

### PROJECT_COMPLETION_CHECKLIST.md
What: Full project checklist across all phases
When: End of Phase 3a
Why: Track all deliverables
Key sections: Phase breakdown, Code modules, Documentation, Tests

### SYSTEM_OVERVIEW.md
What: Visual architecture using ASCII diagrams
When: Phase 2/3a
Why: Architecture documentation
Key sections: Data flow, Model architecture, Integration flows

### QUICK_START.md
What: Fast command reference
When: Phase 3a
Why: Quick lookup for common commands
Key sections: Setup, Common commands, Check progress, Troubleshooting

### MEDIADIVE_INTEGRATION_COMPLETE.md
What: Phase 3b executive summary
When: End of Phase 3b (MediaDive-NCBI linking)
Why: Overview of integration completion
Key sections: Features, Quick start, Architecture, Status

### CVAE_QUICK_START.md
What: CVAE notebook reference and quick training guide
When: Phase 2 completion
Why: Quick start for CVAE training
Key sections: Notebook walkthrough, Training pipeline, Results

---

## Related Documents

**Current main documentation:**
- [docs/INDEX.md](../INDEX.md) - Navigation hub (use this!)
- [docs/GETTING_STARTED.md](../GETTING_STARTED.md) - Start here
- [docs/guides/](../guides/) - Consolidated guides
- [README.md](../../README.md) - Main project overview

**Cleanup documentation:**
- [REPO_CLEANUP_PLAN.md](../../REPO_CLEANUP_PLAN.md) - This archive's creation plan

---

## Questions?

- **Want to use the project?** → See [docs/GETTING_STARTED.md](../GETTING_STARTED.md)
- **Need help?** → See [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **Looking for commands?** → See [docs/COMMAND_REFERENCE.md](../COMMAND_REFERENCE.md)
- **Want history?** → Read this folder's files
- **Lost?** → See [docs/INDEX.md](../INDEX.md)

---

**Archive Created**: 2024 (Part of repository cleanup)  
**Status**: All files preserved, not deleted, for reference
**Next Steps**: Use [docs/](../) for current documentation
