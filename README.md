# BLANC: Defeasible Abduction Benchmark

**B**uilding **L**ogical **A**bductive **N**on-monotonic **C**orpora

A framework for evaluating foundation models on grounded abductive reasoning and belief revision using expert-curated knowledge bases.

---

## Overview

Foundation models struggle with abductive reasoning and belief revision. We provide a benchmark that tests:
1. **Grounding**: Tracing conclusions to supporting evidence
2. **Novelty**: Generating hypotheses beyond training distribution
3. **Belief Revision**: Updating knowledge while preserving unrelated commitments

**The Innovation**: Convert expert-curated ontologies into defeasible theories, enabling systematic evaluation of rational reasoning.

---

## Quick Start

```python
from examples.knowledge_bases.biology_kb import create_biology_kb
from blanc.author.conversion import phi_kappa
from blanc.generation.partition import partition_rule

# Load expert-curated biology KB
kb = create_biology_kb()  # 927 rules, 255 facts, depth 7

# Convert to defeasible theory
theory = phi_kappa(kb, partition_rule)

# Query
from blanc.reasoning.defeasible import defeasible_provable
result = defeasible_provable(theory, "flies(robin)")  # True
```

See `QUICK_START.md` for detailed guide.

---

## Project Status

**Current**: Week 2 Complete - Expert KB Foundation Established  
**Tests**: 208/208 passing (100%)  
**Coverage**: 64% overall, 91-99% critical paths

### Expert Knowledge Bases ✅ COMPLETE

All 3 required domains with expert-curated sources:

| Domain | Rules | Source | Expert Institution |
|--------|-------|--------|-------------------|
| Biology | 927 | YAGO 4.5 + WordNet | Télécom Paris + Princeton |
| Legal | 201 | LKIF Core | University of Amsterdam |
| Materials | 1,190 | MatOnto | MatPortal Community |

**Total**: 2,318 expert-curated rules from 4 peer-reviewed institutions

### Development Timeline

- ✅ MVP Complete (Feb 2026)
- ✅ Expert KB Foundation (Week 2, Feb 2026)
- ⏳ Full Benchmark (Weeks 3-14, Feb-May 2026)
- 📅 NeurIPS Submission (May 2026)

---

## Key Features

### Expert-Curated Foundation

**All knowledge bases from expert sources** (see `KNOWLEDGE_BASE_POLICY.md`):
- YAGO 4.5 (Télécom Paris, SIGIR 2024)
- WordNet 3.0 (Princeton University, Miller 1995)
- LKIF Core (University of Amsterdam, ESTRELLA project)
- MatOnto (MatPortal materials science community)

**Policy**: NO hand-crafted knowledge bases allowed

### Three Evaluation Levels

1. **Level 1**: Fact completion (basic grounding)
2. **Level 2**: Rule abduction (hypothesis generation)
3. **Level 3**: Defeater abduction (rational belief revision)

### Proven Correctness

- Defeasible reasoning engine (91% coverage)
- Criticality computation (94% coverage)
- Instance generation (87% coverage)
- Round-trip codec (92% coverage)

---

## Installation

```bash
git clone https://github.com/username/blanc.git
cd blanc
pip install -r requirements.txt
python -m pytest tests/  # Verify installation
```

---

## Repository Structure

```
blanc/
├── src/blanc/                  Production code
│   ├── reasoning/              Defeasible engine
│   ├── author/                 Instance generation
│   ├── codec/                  Encoding/decoding
│   └── generation/             Partition strategies
│
├── tests/                      Test suite (208 tests)
├── examples/knowledge_bases/   Expert KBs (3 domains)
├── scripts/                    Utilities (17 scripts)
├── paper/                      LaTeX paper + slides
│
├── docs/                       Historical documentation
├── Guidance_Documents/         Phase summaries
└── archive/                    Deprecated files
```

---

## Key Documents

**Start Here**:
- `README.md` - This overview
- `QUICK_START.md` - 5-minute getting started guide
- `PROJECT_STATUS.md` - Current development status

**Critical Policy**:
- `KNOWLEDGE_BASE_POLICY.md` - Expert-only requirement (MANDATORY)

**Planning**:
- `NEURIPS_FULL_ROADMAP.md` - 14-week development plan
- `IMPLEMENTATION_PLAN.md` - Complete technical specification

**Current Work**:
- `WEEK2_COMPLETE.md` - Latest achievements
- `EXPERT_KB_COMPLETE.md` - KB foundation details

---

## Expert Knowledge Base Sources

### Biology (Π_bio)
- **YAGO 4.5**: Taxonomic hierarchy (584 rules, depth 7)
- **WordNet 3.0**: Linguistic taxonomy (334 rules)
- **Citation**: Suchanek et al. (2024) SIGIR; Miller (1995) CACM

### Legal (Π_law)
- **LKIF Core**: Legal norms and actions (201 rules, depth 7)
- **Citation**: Hoekstra et al., U Amsterdam, ESTRELLA project

### Materials (Π_mat)
- **MatOnto**: Materials science ontology (1,190 rules, depth 10)
- **Citation**: Bryan Miller, MatPortal community

**All sources peer-reviewed and citeable**

---

## Testing

```bash
# Run all tests
python -m pytest tests/ --tb=no -q

# Test expert KBs
python scripts/test_all_expert_kbs.py

# Test instance generation
python scripts/generate_minimal_test.py
```

**Status**: 208/208 passing, 0 bugs

---

## Citations

1. Suchanek et al. (2024). YAGO 4.5: A Large and Clean Knowledge Base with a Rich Taxonomy. SIGIR 2024.
2. Miller, G. A. (1995). WordNet: A lexical database for English. CACM 38(11): 39-41.
3. Hoekstra, R., Boer, A., van den Berg, K. LKIF Core: Legal Knowledge Interchange Format.
4. Bryan Miller. MatOnto: Materials Science Ontology. matportal.org/ontologies/MATONTO

---

## License

MIT License - See LICENSE file

---

## Author

Patrick Cooper

---

**For detailed technical information**: See `IMPLEMENTATION_PLAN.md`  
**For development roadmap**: See `NEURIPS_FULL_ROADMAP.md`  
**For current status**: See `PROJECT_STATUS.md`
