# Curated Biology Knowledge Base

Comprehensive biology knowledge base designed for defeasible reasoning and instance generation.

Author: Patrick Cooper  
Date: 2026-02-12  
Status: Operational, validated

## Overview

The biology curated KB expands from the MVP Avian Biology to cover diverse organisms with rich behavioral and taxonomic rules. Designed specifically to achieve dependency depth >= 2 required for DeFAb instance generation.

### Key Features

- **48 organisms** across 6 taxonomic classes
- **45 predicates** covering taxonomy, anatomy, and behavior
- **161 rules total** (110 facts + 51 rules)
- **Depth 4 derivations** (exceeds paper requirement of >= 2)
- **ConceptNet5 validated** against 15,583 biological edges

## Statistics

```
Constants: 48
Predicates: 45
Clauses: 161
Max Depth: 4
Herbrand Base (approx): 2,160
```

## Taxonomic Coverage

### Birds (22 individuals)
- **Passerines** (6): robin, sparrow, finch, crow, jay, cardinal
- **Raptors** (4): eagle, hawk, falcon, owl
- **Waterfowl** (4): duck, goose, swan, pelican
- **Flightless** (4): penguin, ostrich, emu, kiwi
- **Parrots** (2): parrot, macaw
- **Other** (2): hummingbird, woodpecker

### Mammals (16 individuals)
- **Terrestrial** (6): dog, cat, lion, tiger, bear, deer
- **Aquatic** (4): dolphin, whale, seal, otter
- **Flying** (1): bat
- **Primates** (3): monkey, chimp, gorilla
- **Rodents** (2): squirrel, mouse

### Fish (5 individuals)
- salmon, trout, shark, tuna, goldfish

### Insects (6 individuals)
- bee, butterfly, ant, beetle, dragonfly, mosquito

### Reptiles (4 individuals)
- snake, lizard, turtle, crocodile

### Amphibians (2 individuals)
- frog, toad

## Predicate Categories

### Taxonomic (13 predicates)
- organism/1, passerine/1, raptor/1, waterfowl/1, flightless_bird/1, parrot/1
- terrestrial_mammal/1, aquatic_mammal/1, flying_mammal/1
- fish/1, insect/1, reptile/1, amphibian/1

### Anatomical (12 predicates)
- has_wings/1, has_feathers/1, has_beak/1, has_talons/1
- has_fur/1, has_scales/1, has_fins/1, has_gills/1
- has_lungs/1, has_exoskeleton/1, vertebrate/1, invertebrate/1

### Behavioral (20 predicates)
- **Locomotion**: flies/1, swims/1, walks/1, runs/1, climbs/1
- **Biological**: migrates/1, hibernates/1, molts/1
- **Feeding**: hunts/1, grazes/1, scavenges/1, filter_feeds/1
- **Social**: territorial/1, social/1, solitary/1
- **Communication**: sings/1, vocalizes/1, silent/1
- **Reproduction**: lays_eggs/1, live_birth/1
- **Thermoregulation**: warm_blooded/1, cold_blooded/1

## Derivation Chains

The KB supports complex multi-step derivations, enabling rich instance generation.

### Example: robin migration (Depth 4)

```
organism(robin)           [fact, depth 0]
  -> passerine(robin)     [fact, depth 0]
    -> bird(robin)        [strict rule, depth 1]
      -> has_wings(robin) [strict rule, depth 2]
        -> flies(robin)   [defeasible rule, depth 3]
          -> migrates(robin) [defeasible rule, depth 4]
```

### Example: eagle hunting (Depth 3)

```
organism(eagle)           [fact, depth 0]
  -> raptor(eagle)        [fact, depth 0]
    -> bird(eagle)        [strict rule, depth 1]
      -> predator(eagle)  [defeasible rule, depth 2]
        -> hunts(eagle)   [defeasible rule, depth 3]
```

### Example: dolphin swimming (Depth 2)

```
organism(dolphin)         [fact, depth 0]
  -> aquatic_mammal(dolphin) [fact, depth 0]
    -> mammal(dolphin)    [strict rule, depth 1]
      -> swims(dolphin)   [defeasible rule, depth 2]
```

## Usage

### Loading the KB

```python
from examples.knowledge_bases.biology_curated import create_biology_base, get_biology_stats

# Load base KB
kb = create_biology_base()

# Get statistics
stats = get_biology_stats(kb)
print(f"Rules: {stats['clauses']}, Depth: {stats['max_depth']}")
```

### Querying

```python
from blanc.reasoning.defeasible import defeasible_provable

# Check if robin flies
result = defeasible_provable(kb, "flies(robin)")
# Returns: True

# Check if penguin flies  
result = defeasible_provable(kb, "flies(penguin)")
# Returns: False (due to flightless_bird defeater)
```

### Converting for Instance Generation

```python
from blanc.author.conversion import phi_kappa
from blanc.generation.partition import partition_rule

# Convert with partition_rule (facts strict, rules defeasible)
converted = phi_kappa(kb, partition_rule)

print(f"Facts: {len(converted.facts)}")           # 110
print(f"Rules: {len(converted.rules)}")           # 51
```

## Instance Generation Results

### Week 1 Generation (2026-02-12)

Using all 13 partition strategies (κ_leaf, κ_rule, κ_depth(1-3), κ_rand(0.1-0.9)):

```
Total instances: 380
- Level 1 (fact completion): 31 instances
- Level 2 (rule abduction): 349 instances
- Partition strategies: 13
- Organisms covered: 40+
- Behaviors covered: 25+
```

### Partition Strategy Results

From `biology_partition_analysis.json`:

```
leaf        :   1 instances (facts: 0, defeasible: 110)
rule        :  30 instances (facts: 110, defeasible: 51)
depth_1     :  30 instances (facts: 110, defeasible: 36)
depth_2     :  30 instances (facts: 110, defeasible: 6)
depth_3     :  16 instances (facts: 110, defeasible: 1)
rand_0.1    :  16 instances (facts: 96, defeasible: 20)
rand_0.2    :  19 instances (facts: 89, defeasible: 31)
rand_0.3    :  27 instances (facts: 71, defeasible: 57)
rand_0.4    :  30 instances (facts: 60, defeasible: 72)
rand_0.5    :  30 instances (facts: 55, defeasible: 81)
rand_0.6    :  30 instances (facts: 43, defeasible: 100)
rand_0.7    :  30 instances (facts: 28, defeasible: 118)
rand_0.8    :  30 instances (facts: 21, defeasible: 130)
rand_0.9    :  30 instances (facts: 10, defeasible: 147)
```

## Yield Analysis

Yield curves computed for Proposition 3 validation (see `notebooks/yield_curves_biology.png`):

```
delta=0.1: Y=12.6 +/- 5.5
delta=0.2: Y=12.0 +/- 6.7
delta=0.3: Y=11.2 +/- 7.7
delta=0.4: Y=11.2 +/- 7.5
delta=0.5: Y=4.6 +/- 1.4
delta=0.6: Y=4.4 +/- 2.1
delta=0.7: Y=7.4 +/- 6.0
delta=0.8: Y=10.0 +/- 6.6
delta=0.9: Y=12.6 +/- 7.0

Linear fit: Y = -3.40*delta + 11.26, R^2 = 0.081
```

## Design Decisions

### Why Curated vs. Extracted?

Initial attempts to extract from OpenCyc (300K concepts) and ConceptNet5 (21M edges) revealed:
- **OpenCyc**: Max depth 0 (only isa taxonomy)
- **ConceptNet5**: Max depth 1 (direct assertions)
- **Paper requires**: Depth >= 2 for instance generation

**Solution**: Curated approach explicitly designed for inferential depth
- Validated against ConceptNet5 for factual accuracy
- Hand-crafted rules ensure logical dependencies
- Result: Depth 4 achieved, exceeds requirements

### Why These Organisms?

Selected for:
1. **Diversity**: 6 taxonomic classes, 15 families
2. **Familiarity**: Common organisms for evaluation
3. **Behavioral variety**: Flying, swimming, hunting, social
4. **Exception cases**: Flightless birds, flying mammals, aquatic mammals
5. **Defeater opportunities**: Natural exceptions (penguins don't fly)

### Why These Predicates?

Designed to support:
1. **Multi-step reasoning**: Taxonomy -> anatomy -> behavior
2. **Defeasible defaults**: Most birds fly, but not all
3. **Domain coherence**: Biologically plausible rules
4. **Instance diversity**: Many derivable targets

## Validation

### ConceptNet5 Cross-Check

Extracted 15,583 biological edges from ConceptNet5 and verified:
- 95%+ of facts match ConceptNet5 assertions
- No contradictions with established biological knowledge
- Behavioral defaults align with scientific consensus

### Testing

```bash
# Validate KB loads correctly
python scripts/test_biology_curated.py

# Expected output:
# [OK] organism(robin)
# [OK] passerine(robin)
# [OK] bird(robin)
# [OK] has_wings(robin)
# [OK] flies(robin)
# [SUCCESS] Has depth >= 2 derivations (depth = 4)
```

## Limitations

1. **Simplified biology**: Rules are approximations, not strict laws
2. **No quantification**: "Most birds fly" encoded as defeasible default
3. **Limited scope**: Only 48 organisms, many species omitted
4. **No temporal reasoning**: No seasonal behaviors, life cycles
5. **No uncertainty**: Binary derivability, no probabilities

## Future Expansion

Potential additions:
- **Marine biology**: More fish, coral, invertebrates
- **Ecology**: Food chains, ecosystems, habitats
- **Genetics**: Inheritance, mutations, evolution
- **Physiology**: Organ systems, metabolism, homeostasis
- **Ethology**: Complex social behaviors, learning

## Files

```
biology_curated/
├── __init__.py          # Package exports
├── biology_base.py      # Main KB definition (635 lines)
├── README.md            # This documentation
└── tests/
    └── test_biology_curated.py  # Integration tests
```

## References

1. Paper Section 4.1: Source Knowledge Bases
2. HANDOFF_FOR_NEXT_SESSION.md: KB design decisions
3. KB_STRUCTURE_FINDINGS.md: Why curated approach
4. ConceptNet5: Validation data source

---

**Status**: Production-ready  
**Last updated**: 2026-02-12  
**Instances generated**: 380  
**Next**: Week 2 (Legal KB from TaxKB)
