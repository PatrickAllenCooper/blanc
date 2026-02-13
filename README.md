# BLANC: Defeasible Abduction Benchmark

Expert-curated knowledge bases for evaluating foundation models on grounded abductive reasoning.

[![Tests](https://img.shields.io/badge/tests-343%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-80%25-green)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()

---

## Status

**Progress**: Week 8 of 14 complete (57%) ✅  
**Phase**: Evaluation infrastructure complete, ready for pilot  
**Tests**: 343 passing ✅  
**Coverage**: 80% ✅

**Next**: Pilot evaluation (needs API keys) → Week 9 full evaluation

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Validate everything works
python -m pytest tests/ --cov=src/blanc

# When you have API keys:
cp .env.template .env  # Add your keys
python experiments/validate_api_keys.py
python experiments/run_pilot_evaluation.py
```

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
- `Guidance_Documents/` - All planning and status docs
  - `Continue_Development.md` - Handoff for next session
  - `STATUS.md` - Current progress
  - `Knowledge_Base_Policy.md` - Expert-only policy (CRITICAL)
  - `Week8_Complete.md` - Latest work (evaluation infrastructure)
  - Phase summaries and implementation plans

**Reference**:
- `docs/` - Historical documentation (archived)

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

**Complete** (Weeks 1-8):
- Expert KBs (2,318 rules from 4 institutions)
- Complete codec (M1-M4 encoders, D1-D3 decoders)
- Statistical analysis framework (Section 4.3)
- Validation (75% round-trip, 3 of 4 modalities perfect)
- **LLM evaluation infrastructure** (5 models, prompting, caching, pipeline)
- 343 tests, 80% coverage

**Current** (Week 8):
- Pilot evaluation ready (awaiting API keys)

**Remaining** (Weeks 9-14):
- Full LLM evaluation (2 weeks)
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

## Week 8: Evaluation Infrastructure (Current)

Built complete infrastructure for evaluating foundation models:
- Model interfaces: GPT-4o, Claude 3.5, Gemini 1.5, Llama 3
- Prompting: Direct + Chain-of-Thought for all modalities
- Caching: Persistent response storage
- Pipeline: End-to-end evaluation with progress tracking
- Testing: 50 new tests, all passing

**Ready for pilot**: Just need API keys

---

**For continuing development**: See `Guidance_Documents/Continue_Development.md`  
**For Week 8 details**: See `Guidance_Documents/Week8_Complete.md`
