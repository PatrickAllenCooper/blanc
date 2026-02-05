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

# Query (when backends are implemented in Phase 2)
kb = KnowledgeBase(backend='prolog', source='knowledge.pl')
results = Query(kb).select('diagnosis(Patient, Disease)').execute()
```

## Project Status

**Current Phase: Phase 1 - Core Infrastructure (Complete)**

- Unified API design with adapter pattern
- Theory representation supporting multiple rule types
- Query builder for deductive, abductive, and defeasible queries
- Result containers with provenance tracking
- Comprehensive test suite (48 tests, 63% coverage)

**Next Phase: Phase 2 - Backend Implementations**

Backend adapters for:
- SWI-Prolog (via PySwip)
- Clingo ASP solver (via Clorm ORM)
- Defeasible logic systems
- Rulelog integration (strategy TBD)

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
# Install from source
pip install -e .

# With development dependencies
pip install -e ".[dev]"

# With LLM integration
pip install -e ".[llm]"
```

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
# Run test suite
pytest tests -v

# Run with coverage
pytest tests --cov=src/blanc --cov-report=html

# Run examples
python examples/basic_usage.py
```

## Documentation

Comprehensive documentation available in:
- `Guidance_Documents/API_Design.md` - Detailed API specification
- `examples/basic_usage.py` - Working examples
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

