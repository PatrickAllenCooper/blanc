# BLANC Repository Structure

**Last Updated**: 2026-02-11  
**Status**: Cleaned and organized for NeurIPS submission

## Root Directory

```
blanc/
├── README.md                         # Project overview (START HERE)
├── QUICK_START.md                    # 5-minute getting started guide
├── NEURIPS_ROADMAP.md                # MVP → Full benchmark plan (8 weeks)
├── PROJECT_SUMMARY.md                # Comprehensive project summary
├── VALIDATION_STUDY_RESULTS.md       # Empirical validation findings
├── IMPLEMENTATION_PLAN.md            # 80-page technical specification
├── INSTALL.md                        # Installation instructions
├── KNOWLEDGE_BASE_INVENTORY.md       # Catalog of 18 knowledge bases
├── COMPREHENSIVE_STATUS_REPORT.md    # Overall project status
├── VALIDATION_REPORT.md              # KB download validation
├── SLIDES_README.md                  # Presentation materials guide
├── pyproject.toml                    # Python package configuration
├── author.py                         # Mathematical reference implementation
└── .gitignore
```

## Source Code (`src/blanc/`)

```
src/blanc/
├── __init__.py
│
├── core/                   # Phase 1: Core abstractions
│   ├── theory.py              # Theory, Rule, RuleType
│   ├── query.py               # Query builder
│   ├── result.py              # ResultSet
│   └── knowledge_base.py      # KnowledgeBase wrapper
│
├── backends/               # Phase 2: Backend adapters
│   ├── base.py                # Abstract interface
│   ├── prolog.py              # PySwip/SWI-Prolog
│   ├── asp.py                 # Clingo/Clorm
│   ├── defeasible.py          # Defeasible backend (stub)
│   └── rulelog.py             # Rulelog (stub)
│
├── reasoning/              # Phase 3, Week 1: Defeasible logic
│   ├── defeasible.py          # D ⊢∂ q engine (Definition 7)
│   └── derivation_tree.py     # AND-OR proof trees (Definition 13)
│
├── author/                 # Phase 3, Weeks 2-3: Generation pipeline
│   ├── conversion.py          # φ_κ(Π) (Definition 9)
│   ├── support.py             # Crit*(D,q) (Definition 18)
│   ├── metrics.py             # Y(κ,Q) (Definition 22)
│   └── generation.py          # L1-L3 instances (Defs 20-21)
│
├── generation/             # Phase 3, Weeks 2-3: Generation helpers
│   ├── partition.py           # 4 partition functions (Definition 10)
│   └── distractor.py          # 3 sampling strategies (Section 4.2)
│
├── codec/                  # Phase 3, Week 4: Rendering codec
│   ├── encoder.py             # M4 encoder (Definition 26)
│   └── decoder.py             # D1 decoder (Definition 29)
│
├── experiments/            # Phase 4 (Future): Evaluation
│   └── __init__.py
│
├── knowledge_bases/        # Phase 2: KB infrastructure
│   ├── registry.py
│   └── loaders.py
│
└── utils/
    └── __init__.py
```

## Tests (`tests/`)

```
tests/
├── reasoning/              # Week 1 tests (33 tests)
│   ├── test_defeasible.py
│   └── test_derivation_tree.py
│
├── author/                 # Week 2-3 tests (48 tests)
│   ├── test_conversion.py
│   ├── test_partition.py
│   ├── test_support.py
│   ├── test_yield.py
│   └── test_generation.py
│
├── codec/                  # Week 4 tests (26 tests)
│   └── test_roundtrip.py
│
├── backends/               # Phase 2 tests
│   ├── test_asp_backend.py
│   └── test_prolog_backend.py
│
├── test_theory.py          # Phase 1 tests
├── test_query.py
├── test_result.py
└── conftest.py
```

**Total**: 107 tests for Phase 3 author algorithm  
**Status**: 107/107 passing (100%)

## Examples (`examples/`)

```
examples/
├── basic_usage.py
│
└── knowledge_bases/
    ├── avian_biology/          # Phase 3: Test KB
    │   ├── __init__.py
    │   └── avian_biology_base.py  # 6 birds, 20+ rules
    │
    ├── tweety.pl               # Phase 2: Classic examples
    ├── medical.pl
    ├── family.pl
    ├── idp_discovery.pl
    ├── nephrology_simple.pl
    └── citizenship_simple.pl
```

## Scripts (`scripts/`)

```
scripts/
├── generate_mvp_dataset.py         # Generate L1-L2 instances
├── generate_level3_instances.py    # Generate L3 instances
├── create_final_dataset.py         # Merge datasets
├── demo_downloaded_kbs.py          # Phase 2: Demo KBs
├── register_all_kbs.py
├── test_all_kbs.py
└── test_downloaded_kbs.py
```

## Notebooks (`notebooks/`)

```
notebooks/
├── BLANC_Tutorial.ipynb                    # Phase 2: Complete tutorial
├── MVP_Validation_Study.ipynb              # Phase 3: Validation study
├── MVP_Validation_Study_Results.ipynb      # Executed results
├── yield_monotonicity.png                  # Proposition 3 plot
├── reasoning_complexity.png                # Theorem 11 plot
├── criticality_complexity.png              # Definition 18 plot
└── difficulty_stratification.png           # Dataset analysis
```

## Paper Materials (`paper/`)

```
paper/
├── paper.tex                       # NeurIPS 2026 submission
├── references.bib                  # Bibliography
└── mvp_validation_slides.tex       # Validation study presentation (25 slides)
```

## Guidance Documents (`Guidance_Documents/`)

```
Guidance_Documents/
├── API_Design.md                   # Complete API design + changelog
├── Phase1_Summary.md               # Phase 1 completion
├── Phase2_Summary.md               # Phase 2 completion
├── Phase2_Implementation_Plan.md   # Phase 2 plan
├── Phase3_Implementation_Plan.md   # Phase 3 plan (original)
└── Phase3_Complete.md              # Phase 3 completion summary
```

## Archive (`archive/`)

```
archive/
├── week_reports/               # Weekly development reports
│   ├── WEEK1_COMPLETION_REPORT.md
│   ├── WEEK2_COMPLETION_REPORT.md
│   ├── WEEK3_COMPLETION_REPORT.md
│   ├── PHASE3_WEEK1_SUMMARY.md
│   ├── WEEKS_1-2_SUMMARY.md
│   └── PHASE3_WEEKS1-3_COMPLETE.md
│
└── mvp_docs/                   # MVP development documents
    ├── MVP_IMPLEMENTATION.md
    ├── MVP_COMPLETE.md
    ├── MVP_FINAL_SUMMARY.md
    └── PHASE3_DESIGN_SUMMARY.md
```

## Datasets (Generated)

```
blanc/
├── avian_abduction_v0.1.json           # L1-L2 instances (12)
├── avian_level3_v0.1.json              # L3 instances (3)
└── avian_abduction_mvp_final.json      # Merged dataset (15 instances)
```

## Documentation Priority

### Must Read (In Order)

1. **README.md** - Project overview and current status
2. **QUICK_START.md** - Get running in 5 minutes
3. **NEURIPS_ROADMAP.md** - Plan to full implementation
4. **notebooks/MVP_Validation_Study_Results.ipynb** - See it work

### For Development

1. **Guidance_Documents/API_Design.md** - API patterns and changelog
2. **IMPLEMENTATION_PLAN.md** - Detailed technical spec
3. **author.py** - Mathematical reference (all definitions)

### For Understanding

1. **PROJECT_SUMMARY.md** - Comprehensive overview
2. **VALIDATION_STUDY_RESULTS.md** - Validation findings
3. **Guidance_Documents/Phase3_Complete.md** - Phase 3 summary

### Optional

- **archive/** - Historical development documents
- **SLIDES_README.md** - Presentation materials
- Individual phase summaries

## Key Files by Purpose

### Want to understand the math?
→ `author.py` (all definitions mapped to code)  
→ `IMPLEMENTATION_PLAN.md` (detailed explanations)

### Want to use the system?
→ `QUICK_START.md` (examples)  
→ `notebooks/BLANC_Tutorial.ipynb` (interactive)

### Want to see validation?
→ `notebooks/MVP_Validation_Study_Results.ipynb`  
→ `VALIDATION_STUDY_RESULTS.md`

### Want to contribute?
→ `NEURIPS_ROADMAP.md` (what's needed)  
→ `Guidance_Documents/API_Design.md` (patterns)

### Want to present?
→ `paper/mvp_validation_slides.tex` (LaTeX beamer)  
→ Visualizations in `notebooks/`

---

**Repository Status**: Clean, organized, production-ready  
**Documentation**: Comprehensive and accessible  
**Next Step**: Begin Phase 1 of NeurIPS roadmap
