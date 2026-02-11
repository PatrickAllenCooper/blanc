# BLANC Quick Start Guide

**Get started with BLANC and DeFAb in 5 minutes**

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/blanc.git
cd blanc

# Install with development dependencies
pip install -e ".[dev]"

# Install SWI-Prolog (for Prolog backend)
# Windows: winget install -e --id SWI-Prolog.SWI-Prolog
# macOS: brew install swi-prolog
# Linux: sudo apt install swi-prolog
```

See `INSTALL.md` for detailed platform-specific instructions.

## Verify Installation

```bash
# Run test suite
pytest tests/ -v

# Expected: 107+ tests passing
```

## Basic Usage

### 1. Defeasible Reasoning

```python
from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable

# Create theory
theory = Theory()
theory.add_fact("bird(tweety)")
theory.add_rule(Rule(
    head="flies(X)",
    body=("bird(X)",),
    rule_type=RuleType.DEFEASIBLE,
    label="r1"
))

# Query
result = defeasible_provable(theory, "flies(tweety)")
print(f"flies(tweety): {result}")  # True
```

### 2. Generate Instance

```python
from blanc.author.generation import generate_level2_instance
from blanc.author.conversion import convert_theory_to_defeasible

# Convert to defeasible
defeasible_theory = convert_theory_to_defeasible(theory, "rule")

# Find critical rule
r1 = next(r for r in defeasible_theory.rules if r.label == "r1")

# Generate instance
instance = generate_level2_instance(
    defeasible_theory,
    "flies(tweety)",
    r1,
    k_distractors=5
)

print(f"Valid: {instance.is_valid()}")  # True
```

### 3. Encode and Decode

```python
from blanc.codec.encoder import PureFormalEncoder
from blanc.codec.decoder import ExactMatchDecoder

# Encode
encoder = PureFormalEncoder()
prompt = encoder.encode_instance(instance)
print(prompt)

# Decode
decoder = ExactMatchDecoder()
response = "flies(X) :- bird(X)."  # Model response
decoded = decoder.decode(response, instance)
print(f"Decoded: {decoded}")  # Returns the rule
```

## Load Example Knowledge Base

```python
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
    create_avian_biology_full,
)

# Load KB
kb_base = create_avian_biology_base()
kb_full = create_avian_biology_full()

print(f"Base: {len(kb_base.facts)} facts, {len(kb_base.rules)} rules")
print(f"Full: {len(kb_full.facts)} facts, {len(kb_full.rules)} rules")
```

## Generate Dataset

```bash
# Generate MVP dataset (12 instances L1-L2)
python scripts/generate_mvp_dataset.py

# Generate Level 3 instances (3 instances)
python scripts/generate_level3_instances.py

# Create final merged dataset (15 instances)
python scripts/create_final_dataset.py
```

Output: `avian_abduction_mvp_final.json`

## Run Validation Study

```bash
# Execute Jupyter notebook
jupyter notebook notebooks/MVP_Validation_Study.ipynb

# Or use pre-executed version
jupyter notebook notebooks/MVP_Validation_Study_Results.ipynb
```

## Key Concepts

### Defeasible Theory

- **Facts** (F): Ground observations
- **Strict Rules** (Rs): Always true (→)
- **Defeasible Rules** (Rd): Typically true (⇒)
- **Defeaters** (Rdf): Block conclusions (↝)
- **Superiority** (≻): Conflict resolution

### Instance Levels

- **Level 1**: Fact completion (identify missing observation)
- **Level 2**: Rule abduction (reconstruct generalization)
- **Level 3**: Defeater abduction (creative exception)

### Codec Modalities

- **M4**: Pure formal (raw Prolog syntax)
- **M3**: Annotated formal (code + comments)
- **M2**: Semi-formal (logical symbols + NL)
- **M1**: Narrative (full natural language)

## Next Steps

1. **Explore examples**: `examples/knowledge_bases/`
2. **Read tutorial**: `notebooks/BLANC_Tutorial.ipynb`
3. **Check roadmap**: `NEURIPS_ROADMAP.md`
4. **View validation**: `notebooks/MVP_Validation_Study_Results.ipynb`

## Getting Help

- **Documentation**: See `Guidance_Documents/API_Design.md`
- **Examples**: See `examples/` directory
- **Issues**: Check test files for usage patterns
- **Paper**: See `paper/paper.tex` for mathematical definitions

## Current Status

✅ **Phase 3 Complete**: MVP validated, 15 instances, 107 tests  
🚀 **Next**: Scale to 1000+ instances for NeurIPS submission

See `NEURIPS_ROADMAP.md` for complete plan.

---

**Version**: 0.1 (MVP)  
**License**: MIT  
**Author**: Patrick Cooper  
**Paper**: NeurIPS 2026 Submission
