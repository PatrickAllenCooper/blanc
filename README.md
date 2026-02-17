# BLANC: Defeasible Abduction Benchmark

Expert-curated knowledge bases for evaluating foundation models on grounded abductive reasoning.

[![Tests](https://img.shields.io/badge/tests-343%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-80%25-green)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()

---

## Status

**Progress**: Week 8 of 14.5 complete (55%) ✅  
**Phase**: Evaluation infrastructure complete  
**Tests**: 343 passing ✅  
**Coverage**: 80% ✅

**Current**: Starting Week 8.5 - Level 3 instance generation (critical)  
**Why Critical**: Tests novelty & belief revision (currently 0% coverage)  
**See**: [OBJECTIVE_ACCOUNTING.md](OBJECTIVE_ACCOUNTING.md) for gap analysis

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

### Essential Reading (Start Here)
1. **[NEXT_STEPS_SUMMARY.md](NEXT_STEPS_SUMMARY.md)** - What to do next (Week 8.5)
2. **[INTUITIVE_GUIDE.md](INTUITIVE_GUIDE.md)** - Explains the benchmark to non-experts
3. **[OBJECTIVE_ACCOUNTING.md](OBJECTIVE_ACCOUNTING.md)** - Gap analysis (why Level 3 is critical)
4. **[PI_REPORT_2026-02-13.md](PI_REPORT_2026-02-13.md)** - Current status report

### Implementation & Planning
- **[REVISED_IMPLEMENTATION_PLAN.md](Guidance_Documents/REVISED_IMPLEMENTATION_PLAN.md)** - ⭐ Current plan (Weeks 8.5-14)
- **[STATUS.md](Guidance_Documents/STATUS.md)** - Progress tracker
- **[CONTINUE_DEVELOPMENT.md](Guidance_Documents/CONTINUE_DEVELOPMENT.md)** - Development handoff

### Policies & Standards
- **[KNOWLEDGE_BASE_POLICY.md](Guidance_Documents/KNOWLEDGE_BASE_POLICY.md)** - Expert-only policy (CRITICAL)

### Complete Index
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Navigation to all docs

### Historical (Archived)
- `docs/` - Completed weeks, audits, session reports

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
- ✅ Expert KBs (2,318 rules from 4 peer-reviewed institutions)
- ✅ Development dataset (374 Level 2 instances - grounding)
- ✅ Complete codec (M1-M4 encoders, D1-D3 decoders, 75% validation)
- ✅ Statistical analysis (Section 4.3 complete)
- ✅ LLM evaluation infrastructure (5 models, 2 strategies, 4 modalities, caching)
- ✅ All metrics implemented (novelty, conservativity, revision distance)
- ✅ 343 tests passing, 80% coverage

**Current** (Week 8.5 - CRITICAL):
- ⏳ Level 3 instance generation (3-5 days)
- Why: Tests novelty & belief revision (currently 0% dataset coverage)
- Goal: 35-50 defeater abduction instances
- See: [OBJECTIVE_ACCOUNTING.md](OBJECTIVE_ACCOUNTING.md)

**Remaining** (Weeks 9-14.5):
- Week 9: Pilot evaluation (all 3 levels)
- Week 10: Full evaluation (grounding + novelty + belief revision)
- Week 11-12: Advanced analyses
- Week 13-14: HPC production + NeurIPS submission

**Timeline**: ON TRACK (added 3-5 days for Level 3)

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

## Current Focus: Level 3 Instance Generation

### Week 8: Evaluation Infrastructure ✅ COMPLETE
- 5 model interfaces (GPT-4o, Claude 3.5, Gemini 1.5, Llama 3)
- Complete prompting (Direct + CoT for all 4 modalities)
- Response caching and evaluation pipeline
- 50 new tests, all passing

### Week 8.5: Level 3 Instances ⏳ IN PROGRESS (Critical)
**What**: Generate defeater abduction instances  
**Why**: Test novelty and belief revision (paper's core claims)  
**Goal**: 35-50 instances across 3 domains  
**Timeline**: 3-5 days

**Current gap**: 
- Paper claims: "Grounding, Novelty, and Belief Revision"
- Dataset coverage: Grounding (100%), Novelty (0%), Belief Revision (0%)
- Solution: Add Level 3 instances

**See detailed plan**: [REVISED_IMPLEMENTATION_PLAN.md](Guidance_Documents/REVISED_IMPLEMENTATION_PLAN.md)

---

**For continuing development**: See `Guidance_Documents/Continue_Development.md`  
**For Week 8 details**: See `Guidance_Documents/Week8_Complete.md`
