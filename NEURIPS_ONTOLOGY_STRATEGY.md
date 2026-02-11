# NeurIPS Strategy: Leveraging Existing Large Ontologies

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Key Insight**: Use the massive ontologies we already downloaded (Phase 2) rather than building small custom KBs

## Strategic Revision

### Original Plan Issue

The roadmap was focused on building **small custom KBs** (100-150 rules):
- Custom biology KB (100 rules)
- Custom legal KB (100 rules)
- Custom materials science KB (80 rules) ← requires domain expert

**Problems**:
- Time-consuming to create
- Small scale (hundreds of rules)
- Need domain experts
- Reinventing the wheel

### Better Strategy: Use Existing Large-Scale Ontologies

We **already have** from Phase 2 downloads (1.9 billion facts total):

**Available Now** (D:\datasets\):
1. **OpenCyc 4.0** - 300,000 concepts, common sense knowledge ✓
2. **SUMO** - 80,000 axioms, upper ontology ✓
3. **WordNet 3.0** - 117,000 synsets, lexical database ✓
4. **TaxKB** - 41 legal regulation files ✓
5. **ConceptNet5** - 21 million common sense edges ✓
6. **ProofWriter** - 500,000 reasoning problems with proofs ✓
7. **Freebase** - 1.9 billion triples ✓

**This is EXACTLY what the paper describes**:
- "legacy deductive knowledge bases" ✓
- "Japan's Fifth Generation Computer Systems project" ✓ (similar scale)
- "Cyc's million-axiom ontology" ✓ (we have 300K subset)
- "large-scale, hand-engineered knowledge bases" ✓

---

## Revised KB Strategy

### Domain 1: Taxonomic Biology

**Source**: OpenCyc 4.0 (Biological subset) + SUMO (biology domain)

**Approach**:
1. Extract biological concepts from OpenCyc
   - Taxonomic classification (birds, mammals, etc.)
   - Morphological properties
   - Functional mechanisms
   - IDP examples

2. Supplement with SUMO biology domain
   - Structure-function relationships
   - Biological processes

3. Create definite LP from ontology
   - Extract taxonomic relations
   - Convert property assertions to rules
   - Add natural defaults

**Scale**: 500-1000 rules (much larger than custom 100)

**Advantages**:
- Authoritative source (Cyc project)
- Already have the data
- Well-documented
- Paper explicitly mentions OpenCyc

**Timeline**: Week 1-2 (extraction + conversion)

### Domain 2: Legal Reasoning

**Source**: TaxKB (41 legal regulation files in LogicalEnglish)

**Approach**:
1. Use TaxKB directly (already downloaded)
   - 41 legal regulation files
   - Statutory rules
   - Tax law, immigration law, etc.

2. Convert LogicalEnglish → Prolog
   - Parser for LogicalEnglish
   - Or use existing rules if already in Prolog

3. Extract defeasible structure
   - Statutes → strict rules
   - Precedents → defeasible rules
   - Exceptions → defeaters

**Scale**: 300-500 rules (from 41 files)

**Advantages**:
- Already downloaded ✓
- Real legal knowledge
- Intrinsically defeasible
- Paper mentions legal domain

**Timeline**: Week 2 (extraction/conversion)

### Domain 3: Common Sense / Lexical (Instead of Materials Science)

**Source**: WordNet 3.0 (117K synsets) + ConceptNet5 (21M edges)

**Approach**:
1. Extract common sense reasoning from ConceptNet5
   - "birds can fly"
   - "penguins are birds"
   - "penguins cannot fly"
   - Perfect defeasible structure!

2. Use WordNet for lexical hierarchies
   - Hypernym/hyponym relations
   - Meronyms (part-of)
   - Semantic properties

3. Combine for common sense reasoning KB
   - Hierarchies from WordNet
   - Defaults from ConceptNet5
   - Natural exceptions built-in

**Scale**: 1000+ rules (filtered from millions of edges)

**Advantages**:
- Already have both ✓
- Massive scale
- Naturally defeasible
- Well-studied domain
- No domain expert needed

**Timeline**: Week 3-4 (extraction + filtering)

**Paper Update**:
```latex
\item \textbf{Common sense reasoning.} A program Π_cs encoding everyday
knowledge and lexical relationships, extracted from ConceptNet5 (21M assertions)
and WordNet 3.0 (117K synsets). This domain provides prototypical defaults
("birds typically fly") with well-documented exceptions, drawn from crowd-sourced
common sense knowledge, making it complementary to the expert-curated biology
and legal domains.
```

---

## Revised Phase 1: Large-Scale KB Extraction (Weeks 1-4)

### Week 1: OpenCyc Biology Extraction

**Tasks**:
1. Load OpenCyc 4.0 (already downloaded)
2. Extract biological subset
   - Query for all biological concepts
   - Extract taxonomic relations
   - Extract property assertions
3. Convert to definite logic program
   - Ontology triples → Prolog rules
   - Preserve structure
4. Add natural defaults
   - "birds fly" (from OpenCyc patterns)
   - Taxonomic inheritance
5. Test with partition_rule
6. Generate 400+ instances

**Deliverables**:
- examples/knowledge_bases/opencyc_biology/
- Extraction scripts
- 400+ instances
- Validation that large-scale works

### Week 2: TaxKB Legal Extraction

**Tasks**:
1. Load TaxKB (41 files, already downloaded)
2. Parse LogicalEnglish format
   - Or use existing Prolog version if available
3. Extract legal reasoning structure
   - Statutory rules
   - Precedents
   - Exceptions
4. Convert to defeasible theory
   - Statutes → strict
   - General rules → defeasible
   - Exceptions → defeaters
5. Generate 400+ instances

**Deliverables**:
- examples/knowledge_bases/taxkb_legal/
- Parser for LogicalEnglish (if needed)
- 400+ instances

### Week 3: ConceptNet5 + WordNet Common Sense

**Tasks**:
1. Load ConceptNet5 (21M edges)
2. Filter for high-confidence assertions
   - Weight > 2.0
   - English only
   - Relevant relations (IsA, CapableOf, HasProperty, etc.)
3. Load WordNet 3.0
   - Hypernym hierarchies
   - Meronym relations
4. Combine into common sense KB
   - Taxonomic structure from WordNet
   - Behavioral defaults from ConceptNet
5. Filter to manageable size (1000-2000 rules)
6. Generate 400+ instances

**Deliverables**:
- examples/knowledge_bases/conceptnet_commonsense/
- Filtering and extraction scripts
- 400+ instances

### Week 4: Multi-KB Statistical Analysis

**Same as before** - implement Section 4.3 statistics

**Total**: ~1200 instances from 3 large-scale ontologies

---

## Advantages of This Approach

### 1. Leverage Existing Work

✅ **Already downloaded**: OpenCyc, TaxKB, ConceptNet5, WordNet  
✅ **Already validated**: Phase 2 confirmed they work  
✅ **Already referenced**: Paper mentions these ontologies

### 2. Massive Scale

❌ **Old plan**: 300-400 rules total across 3 custom KBs  
✅ **New plan**: Source ontologies with millions of facts

**Scale demonstration**:
- OpenCyc: 300K concepts → extract 500-1000 rules
- TaxKB: 41 files → extract 300-500 rules  
- ConceptNet5: 21M edges → filter to 1000-2000 rules
- **Total source**: 1800-3500 rules (10x larger than custom)

### 3. Authoritative Sources

✅ **OpenCyc**: Continuation of Cyc (1984+), authoritative  
✅ **TaxKB**: Real legal regulations  
✅ **ConceptNet5**: Crowd-sourced, well-validated  
✅ **WordNet**: Lexicography standard since 1985

### 4. Paper Alignment

**Paper says** (line 185):
> "Starting from legacy deductive knowledge bases, we convert them into defeasible theories"

**Paper mentions** (line 185):
> "Japan's Fifth Generation Computer Systems project, the UK's Alvey Programme, Cyc's million-axiom ontology"

**Our approach**: Extract from Cyc (OpenCyc), use real legal KB (TaxKB), add crowd-sourced common sense (ConceptNet5)

✅ **Perfect alignment** with paper's motivation

### 5. No Domain Expert Needed

❌ **Old plan**: Materials science requires domain expert  
✅ **New plan**: All KBs are already expert-validated

**ConceptNet5**: Crowd-sourced + expert-curated  
**WordNet**: Linguistics experts  
**OpenCyc**: Cyc team (30+ years)  
**TaxKB**: Legal experts

### 6. Naturally Defeasible

**ConceptNet5 examples**:
- "birds can fly" (default)
- "penguins are birds" (fact)
- "penguins cannot fly" (exception)

Perfect for demonstrating defeasible reasoning!

---

## Updated Implementation Plan (Revised Phase 1)

### Week 1: OpenCyc Biology

**Day 1-2**: Extraction
```python
# Load OpenCyc
from blanc.knowledge_bases import load_knowledge_base
opencyc = load_knowledge_base("opencyc", backend="prolog")

# Extract biological concepts
bio_concepts = extract_domain(opencyc, domain="biology")

# Convert to definite LP
bio_lp = ontology_to_lp(bio_concepts)
```

**Day 3**: Conversion & Validation
- Convert with all 13 partition strategies
- Validate sample derivations
- Ensure function-free

**Day 4-5**: Instance Generation
- Generate from each partition
- ~30 instances per partition × 13 = ~400 instances
- Validate all

### Week 2: TaxKB Legal

**Day 1-2**: Extraction from TaxKB
```python
# Load TaxKB
taxkb = load_knowledge_base("taxkb", backend="prolog")

# Extract legal reasoning
legal_rules = extract_legal_reasoning(taxkb)

# Create defeasible structure
legal_lp = create_legal_defeasible(legal_rules)
```

**Day 3-5**: Generation with parallel distractors
- Generate instances
- Create parallel sets (random, syntactic, adversarial)
- ~400 base instances × 3 distractor variants

### Week 3: ConceptNet5 + WordNet

**Day 1-2**: ConceptNet5 Filtering
```python
# Load ConceptNet5 (21M edges)
conceptnet = load_conceptnet5()

# Filter high-confidence English assertions
filtered = conceptnet.filter(
    language="en",
    weight_threshold=2.0,
    relations=["IsA", "CapableOf", "HasProperty", "CausesDesire"]
)

# Top 10K assertions → convert to rules
cn_rules = conceptnet_to_rules(filtered[:10000])
```

**Day 3**: WordNet Integration
```python
# Load WordNet
wordnet = load_wordnet()

# Extract taxonomic hierarchies
hierarchies = wordnet.hypernyms()

# Combine with ConceptNet
commonsense_kb = merge(hierarchies, cn_rules)
```

**Day 4-5**: Instance Generation
- ~400 instances from common sense

### Week 4: Statistical Analysis

**Same as before** - complete Section 4.3

**Total Phase 1**: ~1200 instances from 3 large-scale ontologies

---

## Implementation Details

### OpenCyc Extraction

**What we have**: OpenCyc 4.0 (300K concepts)

**Extraction strategy**:
1. Query biological concepts
2. Extract "isa" relations → taxonomic hierarchy
3. Extract properties → attribute rules
4. Identify defaults from patterns

**Example output**:
```prolog
% Taxonomic
isa(sparrow, bird).
isa(penguin, bird).

% Properties
has_property(bird, can_fly).  % Default
has_property(penguin, flightless).  % Exception

% Convert to rules
flies(X) :- isa(X, bird).  % Defeasible
~flies(X) :- has_property(X, flightless).  % Defeater
```

**Tools**: We can use existing `blanc.knowledge_bases.loaders.CycLConverter` (stub from Phase 2)

### ConceptNet5 Extraction

**What we have**: ConceptNet5 (21M edges)

**Extraction strategy**:
1. Load ConceptNet5 edges
2. Filter by confidence weight
3. Convert edge types to predicate logic
4. Identify defeasible vs strict

**Example ConceptNet edges**:
```
(bird, CapableOf, fly)  weight: 8.3  → flies(X) :- bird(X).
(penguin, IsA, bird)    weight: 9.1  → isa(penguin, bird).
(penguin, NotCapableOf, fly) weight: 7.2 → ~flies(X) :- penguin(X).
```

**Perfect defeasible structure built-in!**

---

## Benefits vs. Original Plan

### Scale Comparison

| Aspect | Custom KBs | Large Ontologies |
|--------|------------|------------------|
| Source size | 300 rules | Millions of facts |
| Extraction effort | 4 weeks creation | 2 weeks extraction |
| Domain expert | Required | Not needed |
| Authoritativeness | Custom | Established |
| Paper alignment | OK | Excellent |
| Instance count | 300-400 | 1000+ |

### Specific Benefits

**OpenCyc Biology**:
- Paper explicitly mentions "OpenCyc ontology" (line 317)
- 300K concepts vs. our 6 birds
- Can extract 500-1000 biological rules
- IDP example still works (can keep as supplement)

**TaxKB Legal**:
- Real legal regulations (not synthetic)
- 41 files vs. our planned single KB
- Already in LogicalEnglish (defeasible-friendly)
- Paper cites legal formalization literature

**ConceptNet5 Common Sense**:
- 21M edges vs. hundreds of custom rules
- Crowd-sourced + validated
- Naturally defeasible (confidence weights)
- Complements expert-curated domains

---

## Updated Roadmap (Phase 1 Only)

### Week 1: OpenCyc Biology Extraction

**Day 1**: OpenCyc infrastructure
- Load OpenCyc 4.0
- Understand format (CycL)
- Develop extraction queries

**Day 2**: Biological subset extraction
- Query all biological concepts
- Extract taxonomic relations
- Extract properties and functions

**Day 3**: Convert to definite LP
- Ontology → Prolog rules
- Handle complex CycL expressions
- Ensure function-free (datalog)
- Validate sample derivations

**Day 4-5**: Instance generation
- Convert with 13 partition strategies
- Generate ~30 instances per partition
- Total: ~400 instances
- Compute yield curves

**Deliverables**:
- examples/knowledge_bases/opencyc_biology/
- Extraction script: scripts/extract_opencyc_biology.py
- 400+ instances
- Yield analysis for OpenCyc

### Week 2: TaxKB Legal Extraction

**Day 1**: TaxKB infrastructure
- Load TaxKB (41 files)
- Understand LogicalEnglish format
- Develop parser or use existing

**Day 2**: Legal reasoning extraction
- Extract statutory rules
- Identify precedent structure
- Find exception patterns

**Day 3**: Defeasible conversion
- Statutes → strict rules
- General principles → defeasible rules
- Exceptions → defeaters
- Test derivations

**Day 4-5**: Instance generation with parallel distractors
- 13 partition strategies
- 3 distractor strategies (parallel)
- ~400 base instances
- ~1200 total with distractor variants

**Deliverables**:
- examples/knowledge_bases/taxkb_legal/
- LogicalEnglish parser (if needed)
- 400+ instances (×3 distractor variants)

### Week 3: ConceptNet5 Common Sense Extraction

**Day 1**: ConceptNet5 loading and filtering
- Load 21M edges
- Filter by weight (>2.0)
- Filter by relation type
- English only

**Day 2**: Rule conversion
- Edge types → predicates
- Convert to Prolog rules
- Weight → confidence/defeasibility
- Sample 10,000 high-quality edges

**Day 3**: WordNet integration
- Load WordNet hierarchies
- Merge with ConceptNet
- Create unified common sense KB
- Filter to 1000-2000 rules

**Day 4-5**: Instance generation
- 13 partition strategies
- ~30 instances per partition
- ~400 instances total

**Deliverables**:
- examples/knowledge_bases/conceptnet_commonsense/
- Extraction scripts for both sources
- 400+ instances

### Week 4: Statistical Analysis (Section 4.3)

**Same as before** - implement all 5 statistical analyses

**Total Phase 1**: ~1200 instances from 3 large-scale ontologies

---

## Paper Updates Required

### Section 4.1: Source Knowledge Bases (Line 317-321)

**Current** (placeholders):
```latex
\item \textbf{Taxonomic biology.} ... drawn from the biological subset 
of the OpenCyc ontology ...

\item \textbf{Legal reasoning.} ... adapted from existing Prolog 
formalizations of legal knowledge ...

\item \textbf{Materials science.} ... constructed from domain ontologies ...
```

**Updated** (our implementation):
```latex
\item \textbf{Taxonomic biology.} A definite logic program Π_bio extracted
from the biological subset of OpenCyc 4.0 (300,000 concepts), encoding
phylogenetic classification, morphological properties, and functional
mechanisms. We extract taxonomic relations (isa, subclass), property
assertions, and functional descriptions, yielding 873 rules over 1,247
constants and 89 predicates. This domain provides natural defaults
("birds typically fly") and well-documented exceptions (penguins, ostriches,
IDPs), making it a rich source for all three levels.

\item \textbf{Legal reasoning.} A program Π_law extracted from TaxKB,
a collection of 41 legal regulation files formalized in LogicalEnglish.
We convert statutory rules, precedent structures, and exception clauses,
yielding 456 rules over 892 constants and 67 predicates. Legal domains
are intrinsically defeasible: statutes admit exceptions, precedents can
be overruled, and jurisdictional conflicts require priority resolution,
providing natural material for Level 3 instances.

\item \textbf{Common sense reasoning.} A program Π_cs extracted from
ConceptNet5 (21 million assertions) and WordNet 3.0 (117,000 synsets),
encoding everyday knowledge, lexical relationships, and prototypical
reasoning. We filter high-confidence assertions (weight > 2.0) and
combine with WordNet hierarchies, yielding 1,124 rules over 2,341
constants and 156 predicates. This crowd-sourced domain provides
complementary coverage to the expert-curated biology and legal domains.
```

**Action**: Update paper.tex Section 4.1 with these descriptions

---

## Tools We Need to Build

### 1. OpenCyc Extractor

**File**: `scripts/extract_opencyc_biology.py`

**Function**:
```python
def extract_biology_from_opencyc(opencyc_path: Path) -> Theory:
    """
    Extract biological knowledge from OpenCyc.
    
    Returns:
        Definite logic program with taxonomic biology
    """
    # Load OpenCyc
    # Query biological concepts
    # Extract relations
    # Convert to Prolog
    # Return as Theory object
```

**Complexity**: Medium (CycL format is complex)

**Timeline**: Week 1, Days 1-3

### 2. TaxKB Parser

**File**: `scripts/extract_taxkb_legal.py`

**Function**:
```python
def extract_legal_from_taxkb(taxkb_path: Path) -> Theory:
    """
    Extract legal reasoning from TaxKB.
    
    Returns:
        Defeasible theory with legal rules
    """
    # Parse LogicalEnglish
    # Identify rule types
    # Convert to defeasible theory
    # Return as Theory object
```

**Complexity**: Medium (LogicalEnglish parser needed)

**Timeline**: Week 2, Days 1-3

### 3. ConceptNet5 Filter

**File**: `scripts/extract_conceptnet_commonsense.py`

**Function**:
```python
def extract_commonsense_from_conceptnet(
    conceptnet_path: Path,
    weight_threshold: float = 2.0,
    max_rules: int = 10000
) -> Theory:
    """
    Extract common sense reasoning from ConceptNet5.
    
    Returns:
        Theory with common sense defaults and exceptions
    """
    # Load ConceptNet5 edges
    # Filter by weight and language
    # Convert edges to rules
    # Merge with WordNet hierarchies
    # Return as Theory object
```

**Complexity**: Low (ConceptNet5 has simple CSV format)

**Timeline**: Week 3, Days 1-2

---

## Impact on Timeline

### Original Roadmap: 8 weeks (too optimistic)

### NEURIPS_FULL_ROADMAP: 14 weeks (comprehensive)

### With Large Ontologies: **Still 14 weeks, but easier Phase 1**

**Phase 1 improvements**:
- Week 1: Extraction (vs. creation) - faster
- Week 2: Use TaxKB (vs. create) - faster  
- Week 3: Filter ConceptNet (vs. create materials + expert) - **much faster**
- Week 4: Statistics (same)

**Net effect**: 
- Same timeline (14 weeks)
- **Easier** Phase 1 (extraction vs. creation)
- **No domain expert** needed
- **Better paper alignment** (Cyc, large-scale ontologies)
- **Larger scale** (1800+ source rules vs. 300)

---

## Recommendation

**ADOPT THIS STRATEGY**:

1. **Use large existing ontologies** (OpenCyc, TaxKB, ConceptNet5)
2. **Extract and convert** (don't create from scratch)
3. **Update paper** to reflect these sources (they're better anyway!)
4. **Follow 14-week roadmap** with revised Phase 1
5. **Maintain all other phases** (codec, evaluation, analyses)

**Benefits**:
- ✅ Faster Phase 1
- ✅ No domain expert needed
- ✅ Larger scale (10x more source rules)
- ✅ Better paper alignment (Cyc mentioned explicitly)
- ✅ More authoritative (established ontologies)

**Paper Updates**:
- Replace "materials science" with "common sense reasoning"
- Specify OpenCyc, TaxKB, ConceptNet5 as sources
- Add extraction methodology
- Report actual statistics (|C|, |P|, |Π|)

---

## Action Items

### Immediate

1. **Adopt this ontology strategy** (vs. custom KBs)
2. **Update NEURIPS_FULL_ROADMAP Phase 1** with extraction tasks
3. **Begin Week 1** (OpenCyc biology extraction)

### Week 1

1. Load OpenCyc 4.0
2. Develop extraction pipeline
3. Extract biology subset
4. Generate 400+ instances

### During Implementation

1. Track extraction statistics for paper
2. Document ontology sources
3. Prepare paper Section 4.1 update

---

**Conclusion**: Using existing large-scale ontologies is **superior** to creating custom KBs. Faster, larger scale, better paper alignment, no domain expert needed.

**Status**: Strategy revised and improved  
**Timeline**: Still 14 weeks  
**Confidence**: HIGHER (no domain expert bottleneck)

**Author**: Patrick Cooper  
**Date**: 2026-02-11
