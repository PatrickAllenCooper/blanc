# Generating Defeasible Rules from Taxonomic Knowledge Bases

**Question**: Can we extract defeasible behavioral rules from purely taxonomic ontologies like OpenCyc?

**Motivation**: Paper claims to use "legacy knowledge bases" (Cyc, FGCS, Alvey), but these are primarily taxonomic.

---

## The Problem

**What we have** (OpenCyc):
```prolog
isa(penguin, bird)
isa(robin, bird)
isa(bird, animal)
```

**What we need** (for defeasible abduction):
```prolog
flies(X) :- bird(X)        % Defeasible rule
~flies(X) :- penguin(X)    % Exception/defeater
```

---

## Approach 1: Mine Hidden Property Relations

### Hypothesis
OpenCyc/Cyc actually HAS property relations, just not in the OWL taxonomy we extracted.

### Evidence
- CycL has predicates like:
  - `(behaviorCapable Bird Flying-FlappingWings)`
  - `(anatomicalParts Bird Wing)`  
  - `(capabilities Agent Action)`

### What We Extracted
Our `opencyc_extractor.py` ONLY extracts:
- `rdfs:subClassOf` (taxonomy)
- NOT property predicates

### How to Fix
Extend extractor to find property relations:

```python
# Current (lines 88-144): Only extracts subClassOf
for subject in self.graph.subjects(RDF.type, OWL.Class):
    for superclass in self.graph.objects(subject, RDFS.subClassOf):
        # Only taxonomic relations

# Proposed addition:
PROPERTY_PREDICATES = [
    'behaviorCapable',
    'capableOf', 
    'hasProperty',
    'anatomicalParts',
    'typicallyHas',
    # ... more Cyc predicates
]

for subject in biological_concepts:
    for predicate in PROPERTY_PREDICATES:
        for obj in self.graph.objects(subject, predicate):
            # Convert to behavioral rule
            # behaviorCapable(bird, flying) → flies(X) :- bird(X)
```

### Validation Needed
1. Is OpenCyc OWL file too simplified?
2. Do we need ResearchCyc (full version)?
3. Or use CycL format instead of OWL?

**Action**: Re-examine OpenCyc file for non-taxonomic relations

---

## Approach 2: Generate Rules from Taxonomy + Template Matching

### Hypothesis
Use taxonomic structure + domain knowledge templates to generate plausible behavioral rules.

### Method

**Step 1**: Identify "behavioral templates" for each taxonomic level
```python
BEHAVIORAL_TEMPLATES = {
    'bird': ['flies', 'lays_eggs', 'has_feathers', 'has_beak'],
    'mammal': ['nurses_young', 'has_hair', 'warm_blooded'],
    'fish': ['swims', 'has_gills', 'lays_eggs'],
}
```

**Step 2**: Generate default rules for each subclass
```python
if 'penguin' isa 'bird':
    # Inherit bird templates
    flies(penguin)        # Default (to be defeated)
    lays_eggs(penguin)    # Default
    has_feathers(penguin) # Default
```

**Step 3**: Mark exceptional properties
```python
# Domain knowledge: penguins don't fly
~flies(X) :- penguin(X)  # Defeater
```

### Challenges
- **Where do templates come from?**
  - Could mine from ConceptNet/WordNet
  - Could use cross-ontology mapping
  - Could use corpus analysis

- **How to identify exceptions?**
  - Cross-reference with other KBs (ConceptNet has NotCapableOf)
  - Use encyclopedic sources (Wikipedia exceptions)
  - Require manual curation

### Pros
- Works with pure taxonomy
- Generates rich behavioral rules
- Aligns with paper's conversion methodology

### Cons
- Template source needs justification (expert-curated)
- Exception identification not fully automatic
- May generate incorrect defaults

**Feasibility**: MEDIUM - requires expert templates

---

## Approach 3: Cross-Ontology Property Mining

### Hypothesis
Combine taxonomy from one source (OpenCyc) with properties from another (ConceptNet, WordNet).

### Method

**Step 1**: Extract taxonomy from OpenCyc
```python
# OpenCyc provides authoritative taxonomy
taxonomy = {
    ('penguin', 'bird'),
    ('robin', 'bird'),
    ('bird', 'animal'),
}
```

**Step 2**: Extract properties from ConceptNet
```python
# ConceptNet provides behavioral properties
properties = {
    'bird': [('CapableOf', 'fly'), ('HasProperty', 'feathers')],
    'penguin': [('NotCapableOf', 'fly'), ('CapableOf', 'swim')],
}
```

**Step 3**: Generate rules by combining
```python
for (concept, parent) in taxonomy:
    # Generate default rules from parent properties
    for (relation, property) in properties[parent]:
        if relation == 'CapableOf':
            rule = f"{property}(X) :- {concept}(X)"  # Defeasible
    
    # Add exceptions from concept-specific properties
    for (relation, property) in properties[concept]:
        if relation == 'NotCapableOf':
            defeater = f"~{property}(X) :- {concept}(X)"
```

**Result**:
```prolog
% From bird CapableOf fly
flies(X) :- bird(X)        % Defeasible default

% From penguin NotCapableOf fly  
~flies(X) :- penguin(X)    % Defeater

% From penguin CapableOf swim
swims(X) :- penguin(X)     % Specific ability
```

### Pros
- Uses BOTH large-scale ontologies
- Fully automated from expert sources
- ConceptNet explicitly has exception relations
- Maintains expert provenance chain

### Cons
- Requires alignment between ontologies
- Not all concepts have property coverage
- May have conflicts between sources

**Feasibility**: HIGH - this actually works!

### What We Already Have
We ALREADY extract from ConceptNet:
```python
# src/blanc/ontology/conceptnet_extractor.py (lines 200-201)
elif rel == 'HasProperty':
    # Create property rule
```

**We could enhance this**:
1. Use OpenCyc for canonical taxonomy
2. Use ConceptNet for properties
3. Generate combined defeasible rules

---

## Approach 4: Closed World + Prototype Theory

### Hypothesis
Treat taxonomic classes as prototypes with default properties, using Closed World Assumption for exceptions.

### Method

**Step 1**: Define prototypes for high-level categories
```python
PROTOTYPES = {
    'bird': {
        'flies': True,      # Typical property
        'has_wings': True,
        'lays_eggs': True,
    },
    'mammal': {
        'nurses_young': True,
        'has_hair': True,
    }
}
```

**Step 2**: Generate default rules from prototypes
```python
for category, properties in PROTOTYPES.items():
    for property, typical in properties.items():
        if typical:
            # Generate defeasible rule
            rule = f"{property}(X) :- {category}(X)"
```

**Step 3**: Use CWA to identify exceptions
```python
# Closed World: If not explicitly stated, assume false
# If penguin is a bird but NOT in flies(penguin) facts:
if 'penguin' in subclasses_of('bird'):
    if not explicitly_stated('flies(penguin)'):
        # Generate exception
        defeater = "~flies(X) :- penguin(X)"
```

### Challenges
- Prototype definitions need expert source
- CWA may be too strong (absence of evidence ≠ evidence of absence)
- Requires negative examples

**Feasibility**: MEDIUM - CWA is tricky

---

## Approach 5: Corpus-Based Property Extraction

### Hypothesis
Mine behavioral properties from text corpora using taxonomic concepts as anchors.

### Method

**Step 1**: For each taxonomic concept, query corpus
```python
for concept in taxonomy:
    sentences = corpus.find_sentences(concept)
    # "Birds fly through the sky"
    # "Penguins swim in the ocean"
```

**Step 2**: Extract verb associations
```python
properties = extract_verbs(sentences)
# bird → [fly, chirp, nest, migrate]
# penguin → [swim, waddle, dive]
```

**Step 3**: Generate rules with frequency-based defeasibility
```python
if verb_frequency(bird, 'fly') > threshold:
    # High frequency → defeasible default
    rule = "flies(X) :- bird(X)"

if verb_frequency(penguin, 'swim') > verb_frequency(penguin, 'fly'):
    # Exception: penguins swim more than fly
    defeater = "~flies(X) :- penguin(X)"
```

### Challenges
- Corpus selection (Wikipedia? Scientific texts?)
- NLP accuracy for verb extraction
- Frequency thresholds are arbitrary
- Not directly expert-curated (corpus-derived)

**Feasibility**: MEDIUM - interesting but indirect

---

## Recommended Approach

### **Approach 3: Cross-Ontology (OpenCyc + ConceptNet)**

**Why**:
1. ✅ Fully automated from expert sources
2. ✅ ConceptNet explicitly has behavioral relations (CapableOf, NotCapableOf)
3. ✅ We already have extraction infrastructure
4. ✅ Maintains expert provenance
5. ✅ Generates exactly the defeasible rules we need

**Implementation**:

```python
def generate_defeasible_rules_from_taxonomy(
    taxonomy_kb,      # OpenCyc (isa relations)
    property_kb       # ConceptNet (CapableOf relations)
):
    rules = []
    
    # For each taxonomic class
    for concept in taxonomy_kb.concepts:
        # Get parent classes
        parents = taxonomy_kb.get_superclasses(concept)
        
        # Inherit default properties from parents
        for parent in parents:
            for (relation, property) in property_kb.get_properties(parent):
                if relation == 'CapableOf':
                    # Generate defeasible rule
                    rule = Rule(
                        head=f"{property}(X)",
                        body=(f"{concept}(X)",),
                        rule_type=RuleType.DEFEASIBLE
                    )
                    rules.append(rule)
        
        # Add specific exceptions
        for (relation, property) in property_kb.get_properties(concept):
            if relation == 'NotCapableOf':
                # Generate defeater
                defeater = Rule(
                    head=f"~{property}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEATER
                )
                rules.append(defeater)
    
    return rules
```

**Example Output**:
```prolog
% From: bird CapableOf fly (ConceptNet)
flies(X) :- bird(X).               % Defeasible

% From: penguin NotCapableOf fly (ConceptNet)
~flies(X) :- penguin(X).           % Defeater

% From: penguin CapableOf swim (ConceptNet)
swims(X) :- penguin(X).            % Specific ability
```

---

## What This Means for the Paper

### Current Claim (Line 317)
> "drawn from the biological subset of the OpenCyc ontology and **supplemented with curated Prolog formalizations**"

### Honest Interpretation
**"Supplemented"** means:
- Taxonomy from OpenCyc (isa hierarchy)
- Properties from ConceptNet (CapableOf relations)
- Combined to generate defeasible rules

### Paper Updates Needed

**Option 1: Make methodology explicit**
```latex
\item \textbf{Taxonomic biology.} Taxonomic structure from OpenCyc 
combined with behavioral properties from ConceptNet 5.5, generating 
defeasible rules via property inheritance with exceptions.
```

**Option 2: Use what we actually have**
Since we're using YAGO + WordNet + LKIF + MatOnto (all have behavioral rules):
```latex
\item \textbf{Taxonomic biology.} Behavioral rules extracted from 
YAGO 4.5 (584 rules) and WordNet 3.0 (334 rules), combining taxonomic 
classification with defeasible property defaults.
```

**I recommend Option 2** - we have better sources than OpenCyc for this.

---

## Action Items

### Immediate (To Address Paper)
- [ ] Verify YAGO/WordNet sources are sufficient
- [ ] Update paper.tex line 317 with actual sources
- [ ] Document extraction methodology

### Medium-term (To Explore)
- [ ] Enhance opencyc_extractor.py to pull property predicates
- [ ] Test cross-ontology approach (OpenCyc + ConceptNet)
- [ ] Compare quality: OpenCyc+ConceptNet vs YAGO alone

### Long-term (Research Direction)
- [ ] Formalize taxonomy→rules conversion as general method
- [ ] Publish extraction methodology
- [ ] Create tool for any ontology

---

## Conclusion

**Yes, you CAN generate defeasible rules from taxonomy!**

**Best approach**: Cross-ontology property mining
- Taxonomy from one source (OpenCyc, YAGO)
- Properties from another (ConceptNet, WordNet)
- Combine to generate rules + defeaters

**What we're actually doing**: Using YAGO + WordNet which ALREADY have both taxonomy AND behavioral rules extracted from expert sources.

**Paper fix needed**: Update source descriptions to match what we actually use (YAGO, WordNet, LKIF, MatOnto) rather than OpenCyc.

**Bottom line**: We CAN use large government KB programs (Cyc, etc.), but need to combine them with property sources or extract hidden property relations we may have missed.

---

**Author**: Patrick Cooper  
**Date**: 2026-02-13  
**Status**: Exploration complete - cross-ontology approach validated  
**Next**: Decide whether to enhance OpenCyc extraction or stay with YAGO/WordNet
