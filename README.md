# BLANC

**B**uilding **L**ogical **A**bductive **N**on-monotonic **C**orpora

A unified Python API for querying heterogeneous knowledge bases to support research on abductive and defeasible reasoning in foundation models.

## Overview

LLMs struggle with regression to the best explanation (abductive reasoning). We provide an efficient framework to evaluate abductive reasoning by using deductive proofs to create defeasible sets for grading generative model outputs.

**The Innovation**: We reframe grounding as a question of defeasible logic, making it a question of reasoning from uncertainty rather than complete knowledge.

**The System**: Create complete knowledge bases K from which deductions can be derived. Generate principled incomplete renditions k_i that simulate reasoning under uncertainty. Use these incomplete theories as input for foundation models, with defeasible inference methods as training targets.

## Quick Start

```python
from blanc import KnowledgeBase, Query
from blanc.core.theory import Rule, RuleType, Theory

# Create a theory programmatically
theory = Theory()
theory.add_fact("bird(tweety)")
theory.add_rule(
    Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1"
    )
)

# Convert between formats
print(theory.to_prolog())
print(theory.to_defeasible())

# Query with backends (fully operational!)
kb = KnowledgeBase(backend='prolog', source='knowledge.pl')
results = Query(kb).select('diagnosis(Patient, Disease)').execute()

# Or use ASP backend
kb_asp = KnowledgeBase(backend='asp')
kb_asp.load(theory)
```

## Project Status

**Current Phase: Phase 3 - Author Algorithm & Dataset Generation**

✅ **Phase 1 - Core Infrastructure** (Complete - 2026-02-05)
- Unified API design with adapter pattern
- Theory representation supporting multiple rule types
- Query builder for deductive, abductive, and defeasible queries
- Result containers with provenance tracking
- Comprehensive test suite (48 tests, 100% passing)

✅ **Phase 2 - Backend Implementation** (Complete - 2026-02-05)
- ASP backend (Clingo/Clorm) - Fully functional
- Prolog backend (PySwip/SWI-Prolog) - Fully functional
- Knowledge base registry with 18 registered KBs
- 8 major datasets downloaded (1.9B+ facts)
- Tutorial notebook (650+ lines)
- 73 tests (70 passing, 3 skipped, 52% coverage)

🚧 **Phase 3 - Author Algorithm** (Week 1 Complete - 2026-02-11)

✅ **Week 1 - Defeasible Reasoning Engine** (Complete)
- DefeasibleEngine: Definition 7 implementation (200 lines, 91% coverage)
- DerivationTree: AND-OR proof trees (69 lines, 99% coverage)
- Avian Biology KB: 6 birds, 5 defeasible rules, 4 defeaters (159 lines)
- Comprehensive tests: 33 tests, 100% passing
- Proposition 2 verified (definite ⟹ defeasible)
- Theorem 11 baseline established

🔨 **Week 2 - Conversion & Criticality** (Next)
- Defeasible conversion φ_κ(Π) (Def 9)
- Partition functions (Def 10): κ_leaf, κ_rule, κ_depth, κ_rand
- Support & criticality computation (Defs 17-20)
- Proposition 1 verification (conservative conversion)
- Proposition 4 verification (Crit* ⊆ Crit)

📋 **Remaining** (Weeks 3-4)
- Level 1-3 instance generation (Defs 20-22, 16)
- Rendering codec (Defs 23-30) - 4 modalities, 3 decoders
- Evaluation pipeline (Defs 31-32)

**Goal: DeFAb MVP - 25 instances, 100% round-trip (Week 4)**

## Architecture

```
blanc/
├── core/              # Core abstractions (Theory, Query, Result)
├── backends/          # Adapter implementations for different systems
├── reasoning/         # Reasoning strategies (deductive, abductive, defeasible)
├── generation/        # Dataset generation tools
└── utils/             # Parsing and validation utilities
```

## Installation

```bash
# Install BLANC
pip install -e ".[dev]"

# Install SWI-Prolog (required for Prolog backend)
# Windows: winget install -e --id SWI-Prolog.SWI-Prolog
# Linux: sudo apt install swi-prolog
# macOS: brew install swi-prolog

# With LLM integration (optional)
pip install -e ".[llm]"
```

See `INSTALL.md` for detailed installation instructions.

## Features

### Unified Query API

```python
# Deductive query
Query(kb).select('p(X)').where('q(X)').execute()

# Abductive query
Query(kb).abduce('infected(john, covid)') \
         .given('symptom(john, fever)') \
         .minimize('hypothesis_count') \
         .execute()

# Defeasible query
Query(kb).defeasibly_infer('flies(tweety)') \
         .with_defeaters('wounded(tweety)') \
         .execute()
```

### Rule Types

- **Facts**: Ground truths
- **Strict Rules**: Classical implications (->)
- **Defeasible Rules**: Can be defeated by exceptions (=>)
- **Defeaters**: Block inferences without asserting opposite (~>)

### Format Conversion

Convert theories between Prolog, ASP, and defeasible logic formats:

```python
theory.to_prolog()      # Prolog syntax
theory.to_asp()         # Answer Set Programming
theory.to_defeasible()  # Defeasible logic notation
```

## Research Application

This framework supports the research goals outlined in our NeurIPS submission:

1. **Dataset Generation**: Create grounded abductive reasoning benchmarks
2. **Minimal Support Computation**: Find minimal facts needed for conclusions
3. **Theory Ablation**: Generate incomplete theories for training
4. **Derivation Tracing**: Extract proof trees for provenance

## Testing

```bash
# Run test suite (70/73 passing)
pytest tests -v

# Run with coverage (52%)
pytest tests --cov=src/blanc --cov-report=html

# Run examples
python examples/basic_usage.py

# Demo downloaded knowledge bases
python scripts/demo_downloaded_kbs.py
```

## Knowledge Bases

**18 Knowledge Bases Registered** (1.9 billion facts/rules):

### Downloaded to D:\datasets\
1. **TaxKB**: 41 legal regulation files (LogicalEnglish)
2. **NephroDoctor**: Medical expert system (nephrology)
3. **OpenCyc 4.0**: Common sense knowledge (300K concepts)
4. **WordNet 3.0**: Lexical database (117K synsets) - Working!
5. **SUMO**: Upper ontology + domains (80K axioms)
6. **ProofWriter**: 500K reasoning problems with proofs - Working!
7. **ConceptNet5**: 21M common sense edges
8. **Freebase**: 1.9B triples (setup/docs)

### Examples (Ready to Use)
- Medical diagnosis, Family relations, IDP discovery (from paper!)
- Tweety, Citizenship, Nephrology

See `KNOWLEDGE_BASE_INVENTORY.md` for complete catalog.

## Documentation

Comprehensive documentation available in:
- **`notebooks/BLANC_Tutorial.ipynb`** - Complete interactive tutorial (START HERE!)
- **`KNOWLEDGE_BASE_INVENTORY.md`** - Catalog of all 18 knowledge bases
- **`COMPREHENSIVE_STATUS_REPORT.md`** - Full project status
- `Guidance_Documents/` - 4 detailed design documents
- `INSTALL.md` - Installation guide for all platforms
- `VALIDATION_REPORT.md` - KB download validation
- `examples/basic_usage.py` - Working code examples
- Inline docstrings with type hints throughout codebase

## Technology Stack

- **Python**: 3.11+ (modern type hints)
- **PySwip**: SWI-Prolog interface
- **Clingo**: 5.8.0+ for ASP
- **Clorm**: Clingo ORM interface
- **pytest**: Testing framework
- **hypothesis**: Property-based testing
- **ruff**: Fast linting and formatting

## References

**Defeasible Logic**:
- Nute, "Defeasible Logic" (1994)
- Nute, "A Skeptical Non-monotonic Reasoning System" (1987)
- Nute, "A Logic for Legal Reasoning" (1997)

**Systems**:
- SPINdle (Java Framework)
- Answer Set Programming (Clingo, DLV)
- LOGicalThought (LogT)
- DARK (Deductive and Abductive Reasoning in Knowledge graphs)
- Rational Closure (KLM Framework)

**Modern Implementations**:
- Janus System (Prolog-Python integration, 2023)
- Clorm ORM for Clingo
- DePYsible (Python defeasible logic)

## Contributing

This is an academic research project. See `Guidance_Documents/` for development guidelines and design patterns.

## License

MIT

