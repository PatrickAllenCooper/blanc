# BLANC: Defeasible Abduction Benchmark

**Building Logical Abductive Non-monotonic Corpora**

Expert-curated knowledge bases for evaluating foundation models on grounded abductive reasoning and belief revision.

---

## Overview

Foundation models struggle with:
1. **Grounding**: Tracing conclusions to supporting evidence
2. **Novelty**: Generating hypotheses beyond training distribution
3. **Belief Revision**: Updating knowledge while preserving unrelated commitments

**DeFAb** provides a benchmark using expert-curated knowledge bases from government/academic institutions to test these capabilities.

---

## Quick Start

```python
from examples.knowledge_bases.biology_kb_subset import create_biology_subset
from blanc.author.conversion import phi_kappa
from blanc.generation.partition import partition_rule

# Load expert-curated KB subset (for development)
kb = create_biology_subset()  # 16 rules, fast iteration

# Convert to defeasible theory
theory = phi_kappa(kb, partition_rule)

# Query
from blanc.reasoning.defeasible import defeasible_provable
result = defeasible_provable(theory, "flies(robin)")  # True
```

See `QUICK_START.md` for detailed guide.

---

## Project Status

**Current**: Week 3 Day 1 of 14-week roadmap  
**Progress**: Expert KB foundation complete, instance generation started  
**Tests**: 208/208 passing (100%)

### Expert Knowledge Bases ✅ COMPLETE

All from peer-reviewed institutions:

| Domain | Rules | Source | Institution |
|--------|-------|--------|-------------|
| Biology | 927 | YAGO 4.5 + WordNet | Télécom Paris + Princeton |
| Legal | 201 | LKIF Core | University of Amsterdam |
| Materials | 1,190 | MatOnto | MatPortal/MGI |

**Total**: 2,318 expert-curated rules

**Policy**: Expert-only (see `KNOWLEDGE_BASE_POLICY.md`)

### Development Progress

- ✅ **Week 2**: Expert KB foundation complete
- ⏳ **Week 3**: Instance generation (72/300-600)
- 📋 **Weeks 4-14**: Codec, evaluation, analysis, HPC production

---

## Installation

```bash
git clone https://github.com/PatrickAllenCooper/blanc.git
cd blanc
pip install -r requirements.txt

# Download expert KBs (optional - extracted KBs work without this)
python scripts/download_yago.py
python scripts/download_wordnet.py

# Run tests
python -m pytest tests/
```

---

## Repository Structure

```
blanc/
├── src/blanc/              Production code (1,762 lines, 64% coverage)
├── tests/                  208 tests (100% passing)
├── examples/knowledge_bases/  3 expert KBs + subsets
├── scripts/                Generation and testing scripts
├── hpc/                    HPC/SLURM infrastructure (Weeks 13-14)
├── docs/                   Historical documentation
└── Guidance_Documents/     Phase implementation guides
```

---

## Key Documents

**Essential**:
- `README.md` - This overview
- `QUICK_START.md` - Getting started guide
- `KNOWLEDGE_BASE_POLICY.md` - Expert-only requirement ⚠️ CRITICAL
- `CONTINUE_WEEK3.md` - Current development status

**Planning**:
- `NEURIPS_FULL_ROADMAP.md` - 14-week development plan
- `IMPLEMENTATION_PLAN.md` - Complete technical specification
- `DEVELOPMENT_STRATEGY_REVISED.md` - Local dev + HPC production strategy

**Technical**:
- `COVERAGE_ANALYSIS.md` - Test coverage (64% overall, 91-99% critical)
- `WEEK2_COMPLETE.md` - Latest completed work
- `DATA_DOWNLOAD_INSTRUCTIONS.md` - How to get expert KBs

**Reference**:
- `docs/week3_docs/` - Session documentation
- `Guidance_Documents/` - Phase guides

---

## Expert Sources

### Biology (Π_bio)
- **YAGO 4.5**: 584 rules (Télécom Paris, SIGIR 2024)
- **WordNet 3.0**: 334 rules (Princeton, Miller 1995)

### Legal (Π_law)
- **LKIF Core**: 201 rules (U Amsterdam, ESTRELLA)

### Materials (Π_mat)
- **MatOnto**: 1,190 rules (MatPortal, MGI ecosystem)

**All sources**: Peer-reviewed, government/academic institutions

---

## Development Strategy

**Weeks 3-12**: Local development with KB subsets (fast iteration)  
**Weeks 13-14**: HPC production at massive scale (millions of instances)

Current: 72 instances generated locally in 4 minutes ✅

---

## Testing

```bash
python -m pytest tests/ --tb=no -q
# 208 passed, 3 skipped

python scripts/test_all_expert_kbs.py
# All 3 KBs pass validation
```

---

## Citations

1. Suchanek et al. (2024). YAGO 4.5. SIGIR 2024.
2. Miller, G. A. (1995). WordNet. CACM 38(11).
3. Hoekstra et al. LKIF Core. University of Amsterdam.
4. Bryan Miller. MatOnto. matportal.org/ontologies/MATONTO

---

## License

MIT License

---

## Author

Patrick Cooper

---

**For development**: See `CONTINUE_WEEK3.md`  
**For roadmap**: See `NEURIPS_FULL_ROADMAP.md`  
**For policy**: See `KNOWLEDGE_BASE_POLICY.md` ⚠️
