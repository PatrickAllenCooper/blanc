# BLANC: Defeasible Abduction Benchmark

Expert-curated knowledge bases for evaluating foundation models on grounded abductive reasoning.

---

## Quick Status

**Progress**: Week 5 of 14 complete (36%)  
**Tests**: 228 passing ✅  
**Coverage**: 79% ✅  
**Expert KBs**: 2,318 rules from 4 institutions  
**Instances**: 374 development instances

---

## Key Features

### Expert-Curated Foundation

**All KBs from peer-reviewed sources**:
- YAGO 4.5 (Télécom Paris)
- WordNet 3.0 (Princeton)
- LKIF Core (U Amsterdam)
- MatOnto (MatPortal/MGI)

**Policy**: Expert-only (see KNOWLEDGE_BASE_POLICY.md)

### Complete Codec

**Modalities**: M2, M3, M4 (M1 in Week 6)  
**Decoders**: D1, D2 (D3 in Week 6)  
**Coverage**: 70-92% on codec modules

### Development Dataset

**374 instances** from expert KBs:
- Biology: 114 instances
- Legal: 168 instances
- Materials: 92 instances

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Load expert KB
from examples.knowledge_bases.biology_kb_subset import create_biology_subset
kb = create_biology_subset()  # 16 rules, fast iteration

# Generate instance
from scripts.generate_dev_instances import generate_from_kb_dev
instances, results = generate_from_kb_dev("Biology", kb, [...], max_per_strategy=10)
```

See `QUICK_START.md` for detailed guide.

---

## Repository Structure

```
blanc/
├── src/blanc/              Production code (1,507 lines, 79% coverage)
├── tests/                  228 tests
├── examples/knowledge_bases/  Expert KBs + subsets
├── instances/              374 development instances
├── scripts/                Reproducibility scripts
├── experiments/            Statistical analysis
├── results/                Analysis results
├── figures/                Publication figures
└── docs/                   Documentation
```

---

## Documentation

**Essential**:
- README.md (this file)
- QUICK_START.md
- STATUS.md (current progress)
- KNOWLEDGE_BASE_POLICY.md (CRITICAL)

**Planning**:
- NEURIPS_FULL_ROADMAP.md (14-week plan)
- IMPLEMENTATION_PLAN.md (technical spec)

**Reference**:
- docs/completed_weeks/ (Weeks 3-5)
- docs/audits/ (technical reviews)

---

## Current Work

**Completed**: Weeks 1-5
- Expert KB foundation
- Instance generation
- Statistical analysis
- Codec (M2, M3, D2)
- Architecture refactoring

**Next**: Week 6 (M1 + D3 + 85% coverage)

**Remaining**: 9 weeks to NeurIPS submission

---

## Testing

```bash
python -m pytest tests/              # 228 passing
python -m pytest tests/ --cov        # 79% coverage
```

---

## Citations

1. Suchanek et al. (2024). YAGO 4.5. SIGIR 2024.
2. Miller, G. A. (1995). WordNet. CACM.
3. Hoekstra et al. LKIF Core. U Amsterdam.
4. Bryan Miller. MatOnto. MatPortal.

---

## License

MIT License

---

## Author

Patrick Cooper

**Repository**: Clean, modular, 79% coverage, ready for experiments
