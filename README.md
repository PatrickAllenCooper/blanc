# BLANC: Defeasible Abduction Benchmark

Expert-curated knowledge bases for evaluating foundation models on grounded abductive reasoning.

[![Tests](https://img.shields.io/badge/tests-310%2B%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-77--80%25-yellow)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()

---

## Status

**Progress**: Week 7 of 14 complete (50%) ✅  
**Phase**: Infrastructure complete, ready for evaluation  
**Tests**: 310+ passing ✅  
**Coverage**: 77-80% ✅

**Next**: Week 8 - LLM evaluation infrastructure

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Load expert KB
from examples.knowledge_bases.biology_kb_subset import create_biology_subset
kb = create_biology_subset()  # 16 rules for fast iteration

# Generate instances
python scripts/generate_dev_instances.py
```

See `QUICK_START.md` for detailed guide.

---

## Key Features

### Expert-Curated Knowledge

**2,318 rules from 4 institutions**:
- YAGO 4.5 (Télécom Paris, SIGIR 2024)
- WordNet 3.0 (Princeton, Miller 1995)
- LKIF Core (U Amsterdam, ESTRELLA)
- MatOnto (MatPortal, MGI ecosystem)

**Policy**: Expert-only (see `KNOWLEDGE_BASE_POLICY.md`)

### Complete Codec Framework

**All 4 Modalities**: M1-M4 (narrative to formal)  
**All 3 Decoders**: D1-D3 (exact, template, semantic)  
**Validation**: 75% (3 of 4 perfect)

### Development Dataset

**374 instances** for local iteration  
**Production**: Millions via HPC (Weeks 13-14)

---

## Documentation

**Essential**:
- `README.md` - This file
- `CONTINUE_DEVELOPMENT.md` - Handoff for next session
- `STATUS.md` - Current progress
- `KNOWLEDGE_BASE_POLICY.md` - Expert-only (CRITICAL)

**Planning**:
- `NEURIPS_FULL_ROADMAP.md` - 14-week plan
- `IMPLEMENTATION_PLAN.md` - Technical spec

**Reference**:
- `docs/completed_weeks/` - Weeks 1-7 reports
- `docs/audits/` - Technical audits

---

## Testing

```bash
python -m pytest tests/              # 310+ tests
python -m pytest tests/ --cov        # 77-80% coverage
```

---

## Structure

```
src/blanc/          # Production code (1,712 lines)
tests/              # 310+ tests
examples/           # Expert KBs
instances/          # 374 development instances
experiments/        # Analysis and validation
scripts/            # Reproducibility
hpc/                # HPC infrastructure (Weeks 13-14)
```

---

## Progress

**Complete** (Weeks 1-7):
- Expert KBs (2,318 rules)
- Complete codec (M1-M4, D1-D3)
- Statistical analysis (Section 4.3)
- Validation framework
- 310+ tests, 77-80% coverage

**Remaining** (Weeks 8-14):
- LLM evaluation (3 weeks)
- Advanced analyses (2 weeks)
- HPC production + submission (2 weeks)

**Timeline**: ON TRACK for NeurIPS submission

---

## Citations

1. Suchanek et al. (2024). YAGO 4.5. SIGIR 2024.
2. Miller, G. A. (1995). WordNet. CACM.
3. Hoekstra et al. LKIF Core. U Amsterdam.
4. Bryan Miller. MatOnto. matportal.org/ontologies/MATONTO

---

## License

MIT

---

**For continuing development**: See `CONTINUE_DEVELOPMENT.md`
