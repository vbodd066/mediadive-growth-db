# Documentation Index

Your complete guide to MediaDive Growth DB documentation.

---

## 🚀 Start Here

| Document | Time | Purpose |
|----------|------|---------|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5-10 min | **READ THIS FIRST** - Choose your path |
| [README.md](../README.md) | 10 min | Project overview & architecture |

---

## 📚 Core Documentation

### For Different Use Cases

#### "I just want to run it"
1. [GETTING_STARTED.md](GETTING_STARTED.md) → Path 1: "Just Run It"
2. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) → Copy commands
3. `make integrate-mediadive-ncbi`

#### "I want to understand before running"
1. [GETTING_STARTED.md](GETTING_STARTED.md) → Path 2: "Understand First"
2. [README.md](../README.md) → Architecture section
3. [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md)
4. Then run: `make integrate-mediadive-ncbi`

#### "I want to customize the pipeline"
1. [GETTING_STARTED.md](GETTING_STARTED.md) → Path 3: "Customize It"
2. [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md)
3. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) → Python API section
4. Edit scripts and run

---

## 📖 Complete Guide

### Getting Started
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Three paths to getting started (5 min read)
- **[README.md](../README.md)** - Project overview, architecture, roadmap

### Using the System

| Document | For | Details |
|----------|-----|---------|
| **[COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)** | Commands & API | All CLI commands, Python examples |
| **[guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md)** | Data Integration | Linking MediaDive to NCBI (link+propagate+build) |
| **[guides/cvae_training.md](guides/cvae_training.md)** | CVAE Training | Model architecture, training pipeline, curriculum learning |
| **[guides/api_reference.md](guides/api_reference.md)** | Data Sources | BacDive, NCBI, PubMed API integration |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Help | Common issues, error messages, solutions |

---

## 🗂️ Documentation by Purpose

### Installation & Setup
- [README.md](../README.md) → Quick Start section
- [GETTING_STARTED.md](GETTING_STARTED.md) → "Just Run It" path

### Understanding the Architecture
- [README.md](../README.md) → Architecture section
- [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md) → Data integration architecture

### Running Commands
- [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) → All commands organized by task

### Using Data APIs
- [guides/api_reference.md](guides/api_reference.md) → BacDive, NCBI, PubMed integration

### Training Models
- [guides/cvae_training.md](guides/cvae_training.md) → CVAE model and training

### Troubleshooting
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → Common issues & solutions

---

## 📋 Document Details

### Core Documents

#### GETTING_STARTED.md (NEW - Consolidated)
**What**: Three entry paths for different user types  
**When to read**: First thing  
**Time**: 5-10 minutes  
**Contains**:
- Path 1: Just run it (5 min total)
- Path 2: Understand first (30 min setup + reading)
- Path 3: Customize it (1-2 hours)
- Quick reference commands
- Typical workflows
- Troubleshooting checklist

#### COMMAND_REFERENCE.md
**What**: Complete command reference and Python API  
**When to read**: When executing tasks  
**Time**: 10-20 min (just skim for relevant section)  
**Contains**:
- All CLI commands organized by phase
- Python API usage examples
- Custom parameters
- Data inspection queries
- Workflow combinations

#### README.md (Project Root)
**What**: Project overview, architecture, roadmap  
**When to read**: For background  
**Time**: 10 minutes  
**Contains**:
- Project goals and use cases
- Architecture diagram
- Quick start
- Project structure
- Models overview
- Roadmap

---

### Specialized Guides (in guides/ folder)

#### mediadive_ncbi_linking.md
**What**: Complete integration guide (linking + propagation)  
**When to read**: Understanding data pipeline  
**Time**: 20-30 minutes  
**Contains**:
- Overview of integration
- Quick start (3 steps)
- Detailed pipeline explanation
- Data statistics & volumes
- Advanced usage options
- Troubleshooting

#### cvae_training.md
**What**: CVAE model training guide  
**When to read**: Before training models  
**Time**: 20-30 minutes  
**Contains**:
- Model architecture overview
- Training pipeline steps
- Curriculum learning strategy
- Evaluation metrics
- Usage examples
- Advanced configurations

#### api_reference.md
**What**: API documentation for data sources  
**When to read**: Customizing data ingestion  
**Time**: 20-30 minutes (reference)  
**Contains**:
- BacDive API integration
- NCBI E-utilities integration
- PubMed literature mining
- Rate limits & authentication
- Error handling

---

### Support Documents

#### TROUBLESHOOTING.md
**What**: Common issues and solutions  
**When to read**: When stuck  
**Contains**:
- Common error messages
- Installation issues
- API connection problems
- Database issues
- Memory/performance problems
- FAQ section

---

## 📂 File Organization

```
docs/
├── README.md (this file - Navigation Hub)
├── GETTING_STARTED.md          ← Start here!
├── COMMAND_REFERENCE.md         
├── TROUBLESHOOTING.md
│
├── guides/
│   ├── mediadive_ncbi_linking.md    (Data integration)
│   ├── cvae_training.md              (Model training)
│   └── api_reference.md              (APIs: BacDive, NCBI, PubMed)
│
└── archive/
    ├── README.md (explains what's archived)
    ├── IMPLEMENTATION_SUMMARY.md     (Phase 2 CVAE)
    ├── COMPLETION_SUMMARY.md         (Phase 3a summary)
    ├── SYSTEM_OVERVIEW.md            (Original architecture)
    ├── PROJECT_COMPLETION_CHECKLIST.md
    ├── QUICK_START.md
    ├── MEDIADIVE_INTEGRATION_COMPLETE.md
    └── CVAE_QUICK_START.md

Root level:
├── README.md (Project overview)
├── REPO_CLEANUP_PLAN.md (This reorganization)
└── ... (code, data, notebooks, etc.)
```

---

## 🎯 Quick Navigation

### By Task

**"How do I ingest data?"**
→ [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) Phase 1-3 sections

**"How do I train a model?"**
→ [guides/cvae_training.md](guides/cvae_training.md)

**"What commands do I run?"**
→ [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)

**"How do I link MediaDive to NCBI?"**
→ [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md)

**"What are the data sources?"**
→ [guides/api_reference.md](guides/api_reference.md)

**"I'm getting an error"**
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**"I want to understand the system"**
→ [README.md](../README.md) then [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md)

### By Document Type

**Getting Started**: [GETTING_STARTED.md](GETTING_STARTED.md)  
**Overviews**: [README.md](../README.md)  
**Commands**: [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)  
**Guides**: [guides/](guides/)  
**Help**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)  
**History**: [archive/](archive/)

---

## 📈 Reading Paths

### Path A: First-Time User (30 min)
1. This file (2 min) - you're reading it!
2. [GETTING_STARTED.md](GETTING_STARTED.md) (5 min) - Choose your path
3. [GETTING_STARTED.md](GETTING_STARTED.md) Path 1 (20 min) - Run the system
4. Done! You have data and can start training

### Path B: Understanding First (1-2 hours)
1. [README.md](../README.md) (10 min)
2. [GETTING_STARTED.md](GETTING_STARTED.md) (10 min)
3. [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md) (30 min)
4. [guides/cvae_training.md](guides/cvae_training.md) (30 min)
5. Then run the pipeline

### Path C: Deep Dive (3+ hours)
1. Read all of Path B
2. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) - Review all commands
3. [guides/api_reference.md](guides/api_reference.md) - Understand APIs
4. [archive/](archive/) - Historical context
5. Code repository - Read source files

### Path D: Troubleshooting (As needed)
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Check FAQ & common issues
2. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) - Verify commands
3. Specific guide from [guides/](guides/) - Domain-specific help

---

## 🔍 Search Tips

**Looking for...**

| Need | Search In | Look For |
|------|-----------|----------|
| A command | [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) | `make` or `python -m` |
| Data source | [guides/api_reference.md](guides/api_reference.md) | BacDive, NCBI, PubMed |
| Error message | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Error text |
| Architecture | [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md) | Data Flow section |
| Model details | [guides/cvae_training.md](guides/cvae_training.md) | Model Architecture |
| Historical info | [archive/](archive/) | Specific phase |

---

## 📞 Still Lost?

1. **First time?** → [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Need a command?** → [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)
3. **Got an error?** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Want to understand?** → [README.md](../README.md)
5. **Need deep dive?** → [guides/](guides/) folder
6. **Want history?** → [archive/](archive/) folder

---

## 🎓 Learning Outcomes

After reading the relevant docs, you'll understand:

| Topic | Read | Time |
|-------|------|------|
| Project goals | [README.md](../README.md) | 5 min |
| How to get started | [GETTING_STARTED.md](GETTING_STARTED.md) | 5 min |
| How to run commands | [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) | 10 min |
| How data flows | [guides/mediadive_ncbi_linking.md](guides/mediadive_ncbi_linking.md) | 20 min |
| How to train models | [guides/cvae_training.md](guides/cvae_training.md) | 20 min |
| How to solve problems | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 10 min |

---

## 📊 Documentation Statistics

| Category | Count | Lines | Updated |
|----------|-------|-------|---------|
| Quick starts | 1 | 200 | 2024 |
| Guides | 3 | 1,200 | 2024 |
| References | 1 | 400 | 2024 |
| Support | 1 | 300 | 2024 |
| Archive | 7 | 3,500 | Original |
| **Total** | **13** | **5,600** | — |

---

**Last Updated**: 2024  
**Status**: ✅ Current & Complete  
**Next**: Choose a path above or start with [GETTING_STARTED.md](GETTING_STARTED.md)
