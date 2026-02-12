# Architecture Audit: Modularity and Interface Review

**Date**: 2026-02-12  
**Purpose**: Ensure software is modular, maintainable, and ready for experiments  
**Scope**: Complete codebase review

---

## Current Module Structure

```
src/blanc/
├── __init__.py
├── reasoning/          # Defeasible logic engine
│   ├── defeasible.py
│   └── derivation_tree.py
│
├── author/             # Instance generation
│   ├── conversion.py   # Theory conversion (φ_κ)
│   ├── support.py      # Criticality computation
│   ├── generation.py   # Instance generation
│   └── metrics.py      # Yield computation
│
├── generation/         # Supporting generation utilities
│   ├── partition.py    # Partition strategies
│   └── distractor.py   # Distractor sampling
│
├── codec/              # Encoding/decoding modalities
│   ├── encoder.py      # M4 encoder
│   ├── decoder.py      # D1 decoder
│   ├── m2_encoder.py   # M2 (NEW)
│   ├── m3_encoder.py   # M3 (NEW)
│   ├── d2_decoder.py   # D2 (NEW)
│   └── nl_mapping.py   # NL mappings (NEW)
│
├── core/               # Core data structures
│   ├── theory.py       # Theory, Rule classes
│   ├── query.py        # Query interface
│   ├── result.py       # Result structures
│   └── knowledge_base.py  # KB interface
│
├── backends/           # Backend implementations (not used)
│   ├── asp.py
│   ├── prolog.py
│   ├── defeasible.py
│   └── rulelog.py
│
├── ontology/           # KB extraction (completed)
│   ├── conceptnet_extractor.py
│   └── opencyc_extractor.py
│
├── knowledge_bases/    # KB registry (not used)
│   ├── loaders.py
│   └── registry.py
│
└── utils/              # Utilities (empty)
```

---

## Modularity Assessment

### ✅ GOOD Modularity

**1. reasoning/** - Clean separation
- Purpose: Defeasible logic engine
- Interface: `defeasible_provable(theory, query)`
- Dependencies: Only core/
- Assessment: **Excellent** - well-defined, minimal dependencies

**2. core/** - Good foundation
- Purpose: Data structures
- Interface: Theory, Rule, Query classes
- Dependencies: None (pure data)
- Assessment: **Good** - foundational types, no business logic

**3. codec/** - Recently improved
- Purpose: Encoding/decoding
- Interface: `encode_*(element)`, `decode_*(text, candidates)`
- Dependencies: core/, nl_mapping
- Assessment: **Good** - modular encoders/decoders

---

### ⚠️ NEEDS IMPROVEMENT

**4. author/** - Mixed concerns
- Purpose: Instance generation BUT also conversion and metrics
- Issues:
  - `conversion.py` is really about partition, not authoring
  - `metrics.py` is about yield, not authoring
  - Module name doesn't match contents

**Recommendation**: Restructure
```
src/blanc/
├── partition/          # Partition and conversion
│   ├── conversion.py
│   ├── strategies.py   (from generation/partition.py)
│
├── instance_generation/  # Actual instance generation
│   ├── generator.py    (from author/generation.py)
│   ├── criticality.py  (from author/support.py)
│   └── distractors.py  (from generation/distractor.py)
│
└── metrics/            # Analysis metrics
    └── yield.py        (from author/metrics.py)
```

**5. generation/** - Orphaned utilities
- Currently has: partition.py, distractor.py
- These should be with instance generation, not separate

---

### ❌ UNUSED/CONFUSING

**6. backends/** - Not used (0% coverage)
- Contains alternative backends (ASP, Prolog)
- Never used in current pipeline
- Adds confusion

**Recommendation**: Move to `src/blanc/backends_legacy/` or delete

**7. knowledge_bases/** - Not used (0% coverage)
- Registry and loaders never used
- We load KBs directly from examples/

**Recommendation**: Delete or move to legacy

---

## Interface Analysis

### ✅ CLEAN Interfaces

**Reasoning**:
```python
defeasible_provable(theory, query) -> bool
build_derivation_tree(theory, query) -> Tree
```
- Simple, clear
- One responsibility
- Easy to test

**Codec**:
```python
encode_m4(element) -> str
decode_d1(text, candidates) -> element
```
- Consistent pattern
- Modular
- Extensible

---

### ⚠️ COMPLEX Interfaces

**Instance Generation**:
```python
generate_level2_instance(
    theory,           # Converted theory
    target,           # Target conclusion
    critical_element, # Element to ablate
    k_distractors,    # Number of distractors
    distractor_strategy  # Strategy name
) -> AbductiveInstance
```

**Issues**:
- Too many parameters
- Mixes concerns (what vs how)
- Hard to extend

**Better**:
```python
class InstanceGenerator:
    def __init__(self, theory, config):
        self.theory = theory
        self.config = config
    
    def generate(self, target, level) -> AbductiveInstance:
        # Configuration handles k, strategy, etc.
```

---

### ❌ UNCLEAR Interfaces

**Conversion**:
```python
phi_kappa(theory, partition_fn) -> Theory
convert_theory_to_defeasible(theory, mode, k=None, delta=None) -> Theory
```

**Issues**:
- Two functions do similar things
- Optional parameters based on mode (confusing)
- Not clear which to use when

**Better**: Single converter with strategy pattern
```python
class TheoryConverter:
    def convert(self, theory, strategy: PartitionStrategy) -> Theory
```

---

## Dependency Analysis

### Current Dependencies

**Problematic**:
- `author/generation.py` imports from `generation/distractor.py`
- `codec/m3_encoder.py` imports from `codec/encoder.py`
- Circular potential between author/ and generation/

**Clean**:
- `reasoning/` only depends on `core/`
- `core/` has no dependencies
- `codec/` modules independent

---

## Recommended Refactoring

### Priority 1: Reorganize Modules (2-3 hours)

**Create clearer structure**:
```
src/blanc/
├── core/              # Data structures (no change)
│   ├── theory.py
│   ├── query.py
│   └── result.py
│
├── reasoning/         # Logic engine (no change)
│   ├── defeasible.py
│   └── derivation_tree.py
│
├── conversion/        # Theory conversion (NEW)
│   ├── converter.py   (from author/conversion.py)
│   └── partition.py   (from generation/partition.py)
│
├── instance/          # Instance generation (NEW)
│   ├── generator.py   (from author/generation.py)
│   ├── criticality.py (from author/support.py)
│   └── distractor.py  (from generation/distractor.py)
│
├── codec/             # Encoding/decoding (expand)
│   ├── encoders.py    # All encoders in one file
│   ├── decoders.py    # All decoders in one file
│   └── nl_mapping.py
│
├── analysis/          # Metrics and statistics (NEW)
│   ├── yield.py       (from author/metrics.py)
│   └── statistics.py  (from experiments/)
│
└── kb_extraction/     # KB utilities (RENAME)
    ├── extractors/    (from ontology/)
    └── expert_kbs/    (from knowledge_bases/)
```

**Benefits**:
- Clear module purposes
- No mixed concerns
- Easier to find code
- Better for refactoring during experiments

---

### Priority 2: Unify Codec (1-2 hours)

**Current**: 6 separate files in codec/  
**Better**: Group by function

```python
# codec/encoders.py
class M4Encoder: ...
class M3Encoder: ...
class M2Encoder: ...
class M1Encoder: ...  # Future

# codec/decoders.py  
class D1Decoder: ...
class D2Decoder: ...
class D3Decoder: ...  # Future

# codec/pipeline.py
class CascadingDecoder:
    def decode(self, text, candidates):
        # Try D1, then D2, then D3
```

**Benefits**:
- Easier to compare encoders
- Consistent interface
- Simpler imports

---

### Priority 3: Clean Up Unused Code (30 min)

**Delete or archive**:
- `backends/` (not used, 0% coverage)
- `knowledge_bases/loaders.py` (not used)
- `knowledge_bases/registry.py` (not used)

**Benefits**:
- Less confusing
- Clearer what's actually used
- Smaller codebase

---

### Priority 4: Improve Instance Generation API (2-3 hours)

**Current**: Functions with many parameters  
**Better**: Configuration-based

```python
@dataclass
class InstanceConfig:
    level: int = 2
    k_distractors: int = 5
    distractor_strategy: str = "syntactic"
    partition_strategy: PartitionStrategy = None

class InstanceGenerator:
    def __init__(self, theory: Theory, config: InstanceConfig):
        self.theory = theory
        self.config = config
    
    def generate(self, target: str) -> AbductiveInstance:
        # Uses config for all parameters
        # Easy to extend
        # Easy to batch generate
```

**Benefits**:
- Easier to configure experiments
- Can change parameters without changing calls
- Better for batch generation
- Clearer code

---

## Testing Strategy

### After Refactoring

**1. Keep all existing tests** (250 passing)  
**2. Update imports** as modules move  
**3. Add integration tests** after refactoring  
**4. Verify coverage maintains** or improves

**Target**: 250+ tests still passing after refactoring

---

## Refactoring Plan

### Phase 1: Non-Breaking Changes (2 hours)

1. **Unify codec into fewer files**
   - Merge encoders
   - Merge decoders
   - Update tests

2. **Clean up unused code**
   - Move backends/ to legacy/
   - Remove unused KB infrastructure

**Test**: All 250 tests still pass

---

### Phase 2: Module Reorganization (3-4 hours)

3. **Rename author/ → instance/**
   - More accurate name
   - Update all imports
   - Update tests

4. **Move partition code**
   - Create conversion/ module
   - Move partition.py
   - Update imports

5. **Create analysis/ module**
   - Move metrics
   - Move statistics
   - Organize experiments

**Test**: All tests still pass with new imports

---

### Phase 3: API Improvements (2-3 hours)

6. **Configuration-based generation**
   - Create InstanceConfig
   - Refactor generator to use config
   - Backward compatible wrappers

7. **Unified codec interface**
   - Create EncoderPipeline
   - Create DecoderPipeline
   - Consistent API

**Test**: All tests pass, new APIs work

---

## Total Refactoring Estimate

**Time**: 7-10 hours  
**Risk**: Medium (breaking changes)  
**Benefit**: Much cleaner for experiments

---

## Do We Refactor Now?

### Arguments For:
- ✅ Better structure for Weeks 6-14
- ✅ Easier experiments
- ✅ Cleaner codebase
- ✅ Fix confusion now

### Arguments Against:
- ⚠️ Takes time (7-10 hours)
- ⚠️ Risk of breaking things
- ⚠️ Delays Week 6 start

### Recommendation

**Do targeted refactoring**:
- Clean up unused code (30 min) ✅
- Unify codec (1-2 hours) ✅
- Leave module reorganization for later (not critical)

**Defer**:
- Full module restructuring (can do between phases)
- API changes (backward compatible wrappers later)

**Result**: 2-3 hours of cleanup now, major refactoring deferred

---

## Immediate Actions

**Execute now** (2-3 hours):
1. Remove unused backends/ and knowledge_bases/ code
2. Unify codec into cleaner structure
3. Add __init__.py exports for cleaner imports
4. Verify all 250 tests still pass

**Defer to later**:
5. Module reorganization (author/ → instance/)
6. Configuration-based APIs
7. Full architectural overhaul

---

**Ready to execute targeted refactoring?**

---

**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Architecture audit complete, refactoring plan ready
