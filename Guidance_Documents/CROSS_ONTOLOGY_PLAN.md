# Cross-Ontology Extraction Plan: 10-100x Scale Expansion

**Date**: 2026-02-13  
**Trigger**: User insight - OpenCyc + ConceptNet can massively scale ruleset  
**Goal**: Leverage large-scale legacy KBs to generate 100K+ defeasible rules  
**Timeline**: Week 8.5a (proof) + Week 8.6 (full extraction)

---

## Executive Summary

### The Opportunity

**Current benchmark**:
- 2,318 expert rules
- 374 development instances
- Small-scale proof-of-concept

**With cross-ontology extraction**:
- 100,000-350,000 rules (43-151x multiplier)
- 16,000-56,000 instances (43-150x multiplier)
- **Large-scale production benchmark**

**Method**: Combine OpenCyc taxonomy (300K concepts) with ConceptNet properties (21M assertions)

**Paper impact**: Actually leverages "million-axiom" legacy KBs as claimed

---

## The Three Methods (Ranked)

### Method 1: Cross-Ontology (OpenCyc + ConceptNet) ⭐ RECOMMENDED

**Sources**:
- **OpenCyc**: 300,000 concepts (authoritative taxonomy)
- **ConceptNet 5.7**: 21,000,000 assertions (behavioral properties)

**Algorithm**:
```python
For each concept in OpenCyc taxonomy:
  1. Get parent classes (bird → animal → organism)
  2. Inherit properties from all parents via ConceptNet
     - bird.CapableOf(fly) → flies(X) :- bird(X) [DEFEASIBLE]
  3. Add concept-specific properties
     - penguin.CapableOf(swim) → swims(X) :- penguin(X)
  4. Add concept-specific exceptions
     - penguin.NotCapableOf(fly) → ~flies(X) :- penguin(X) [DEFEATER]
```

**Generated rules for penguin**:
```prolog
% Taxonomic (from OpenCyc)
bird(X) :- penguin(X).              [STRICT]
animal(X) :- bird(X).               [STRICT]

% Inherited from 'bird' (from ConceptNet)
flies(X) :- penguin(X).             [DEFEASIBLE - inherited]
sings(X) :- penguin(X).             [DEFEASIBLE - inherited]

% Penguin-specific (from ConceptNet)
~flies(X) :- penguin(X).            [DEFEATER - overrides inherited!]
swims(X) :- penguin(X).             [DEFEASIBLE - specific]
```

**Yield estimate**:
- Biology: 50,000 concepts × 2-4 rules avg = **100,000-200,000 rules**
- Defeaters: ~5-10% of rules = **5,000-20,000 defeaters** (LEVEL 3 GOLD MINE!)

**Pros**:
- ✅ Fully automated from expert sources
- ✅ ConceptNet explicitly has NotCapableOf (defeaters!)
- ✅ Leverages both large-scale legacy systems
- ✅ Maintains expert provenance
- ✅ Perfect for Level 3 generation

**Cons**:
- ⚠️ Requires concept alignment (solvable)
- ⚠️ Two dependencies
- ⚠️ 1 week implementation time

**Feasibility**: HIGH - proven methods

---

### Method 2: ConceptNet Standalone

**Source**: ConceptNet alone (has both IsA and properties)

**Algorithm**:
```python
From ConceptNet assertions:
  1. IsA relations → taxonomy
  2. CapableOf → defeasible rules
  3. NotCapableOf → defeaters
  4. HasProperty → property rules
```

**Yield estimate**:
- Biology edges: ~500,000 in ConceptNet
- After filtering: **50,000-100,000 rules**

**Pros**:
- ✅ Single source (simpler)
- ✅ Has defeaters built-in
- ✅ Already validated (Week 1)
- ✅ Faster extraction

**Cons**:
- ⚠️ Crowdsourced (less authoritative than Cyc)
- ⚠️ May have quality issues
- ⚠️ Taxonomy less canonical than OpenCyc

**Feasibility**: VERY HIGH - already works

---

### Method 3: YAGO Full Extraction

**Source**: Full YAGO 4.5 (109M facts, we use tiny subset)

**Current**: 584 rules from YAGO subset  
**Potential**: Extract from full YAGO → **10,000-50,000 rules**

**Pros**:
- ✅ We already use YAGO (proven)
- ✅ Single expert source
- ✅ High quality

**Cons**:
- ⚠️ Smaller scale than Cyc+ConceptNet
- ⚠️ May not have explicit defeaters

**Feasibility**: HIGH - incremental improvement

---

## Recommended Plan: Hybrid Approach

### Week 8.5a: Proof-of-Concept (1 day) ← DO FIRST

**Goal**: Validate that cross-ontology approach achieves 10x scale

**Script**: `scripts/validate_cross_ontology_scale.py` (already created)

**Tasks**:
1. Load 1,000 concepts from OpenCyc (sample)
2. Load 100,000 assertions from ConceptNet (sample)
3. Generate combined rules
4. Measure: rules, defeaters, quality
5. Extrapolate to full scale

**Success criteria**:
- [ ] Generates >= 5,000 rules from sample (5x multiplier)
- [ ] Generates >= 100 defeaters
- [ ] Quality validation passes on 10 random rules
- [ ] Projected full scale >= 50,000 rules

**Timeline**: 4-8 hours

**Decision point**:
- ✅ If success → proceed to Week 8.6 (full extraction)
- ❌ If failure → stick with current sources

---

### Week 8.5b: Level 3 Manual Generation (3-5 days)

**Run in parallel** with proof-of-concept

**Goal**: Generate 35-50 Level 3 instances from current KBs

**Why parallel**:
- Proof may fail (need Level 3 either way)
- Proof may take time to debug
- Level 3 is critical for paper

**See**: REVISED_IMPLEMENTATION_PLAN.md Week 8.5 section

---

### Week 8.6: Full Cross-Ontology Extraction (1 week) ← OPTIONAL

**Conditional on**: Week 8.5a proof succeeding

**Goal**: Generate 100K+ rules from full sources

#### Day 1-2: Enhanced Extractors

**Enhance** `src/blanc/ontology/opencyc_extractor.py`:
```python
class OpenCycExtractor:
    def extract_full_taxonomy(self):
        """Extract complete taxonomy (50K concepts)."""
        # Current: Only extracts biology keywords
        # New: Extract full biological hierarchy
        
    def extract_properties(self):
        """Extract property assertions if they exist."""
        # Check for: behaviorCapable, typicallyHas, etc.
```

**Enhance** `src/blanc/ontology/conceptnet_extractor.py`:
```python
class ConceptNetExtractor:
    def extract_all_behavioral(self, domain='biology'):
        """Extract all behavioral relations."""
        # CapableOf, NotCapableOf, HasProperty
        # UsedFor, HasA, MadeOf (for materials)
        # Causes, HasSubevent (for legal)
```

**Create** `src/blanc/ontology/cross_ontology.py`:
```python
class CrossOntologyGenerator:
    """Combine taxonomy from one source with properties from another."""
    
    def __init__(self, taxonomy_source, property_source):
        self.taxonomy = taxonomy_source
        self.properties = property_source
    
    def generate_defeasible_rules(self):
        """Main algorithm: property inheritance + exceptions."""
        # Implementation from validate_cross_ontology_scale.py
```

#### Day 3-4: Biology Domain Extraction

**Extract**:
- OpenCyc: 50,000 biological concepts
- ConceptNet: 500,000 biology assertions
- Generate: **100,000-200,000 rules**

**Validate**:
- Sample 100 random rules
- Check against encyclopedic sources
- Verify depth >= 2 for samples
- Measure defeater percentage

#### Day 5: Legal & Materials Domains

**Legal**:
- OpenCyc: 10,000 legal/governmental concepts
- ConceptNet: 50,000 legal assertions
- Generate: **10,000-50,000 rules**

**Materials**:
- OpenCyc: chemistry/materials concepts
- ConceptNet: materials properties
- MatOnto: structure-property (existing)
- Generate: **50,000-100,000 rules**

#### Day 6-7: Instance Generation & Validation

**Regenerate development instances**:
- Use large-scale KB
- Generate 2,000-5,000 instances per domain
- **Total**: 6,000-15,000 instances (vs 374)

**Validate**:
- Run tests (ensure all pass)
- Quality check on sample
- Verify encoder/decoder compatibility
- Statistical analysis

---

## Timeline Integration

### Original Timeline (Before Cross-Ontology)
```
Week 8:    Evaluation Infrastructure         ✅ COMPLETE
Week 8.5:  Level 3 Manual Generation         (3-5 days)
Week 9:    Pilot Evaluation                  (2-3 days)
Week 10:   Full Evaluation                   (5-7 days)
Weeks 11-12: Advanced Analyses               (2 weeks)
Weeks 13-14: HPC Production                  (2 weeks)
```

### Revised Timeline (With Cross-Ontology)
```
Week 8:    Evaluation Infrastructure         ✅ COMPLETE
Day 8.5a:  Cross-Ontology Proof              (1 day) ← NEW
Week 8.5b: Level 3 Manual Generation         (3-5 days, parallel)
Week 8.6:  Full Cross-Ontology Extraction    (1 week) ← CONDITIONAL
Week 9:    Pilot Evaluation (Large-Scale)    (2-3 days)
Week 10:   Full Evaluation (10K+ instances)  (1-2 weeks)
Weeks 11-12: Advanced Analyses               (2 weeks)
Weeks 13-14: HPC Production (100K scale)     (2 weeks)
```

**Added time**: 1 day (proof) + 1 week (conditional) = 1-8 days  
**Benefit**: 10-100x scale, leverages legacy KBs, stronger paper

---

## Cost-Benefit Analysis

### Costs

**Time**:
- Proof-of-concept: 1 day (low risk)
- Full extraction: 1 week (conditional)
- Total: 1-8 days added

**Technical**:
- Enhanced extractors (code complexity)
- Cross-ontology alignment (algorithmic)
- Validation at scale (testing)

**Risk**:
- Alignment may have errors
- Quality may be lower than hand-curated
- Debugging may take longer than expected

### Benefits

**For Paper**:
- ✅ Actually uses "million-axiom" legacy KBs
- ✅ 10-100x scale increase
- ✅ Novel extraction methodology (publishable!)
- ✅ Stronger empirical results

**For Benchmark**:
- ✅ 16,000-56,000 instances (vs 374)
- ✅ Statistical power for all analyses
- ✅ Comprehensive coverage
- ✅ Production-ready immediately

**For Level 3**:
- ✅ Automatic defeater generation from NotCapableOf
- ✅ 5,000-20,000 defeaters (vs manual 35-50)
- ✅ Natural exceptions already in ConceptNet

**For Research Impact**:
- ✅ Cross-ontology method is reusable
- ✅ Bridges taxonomy and behavioral KBs
- ✅ Could be separate publication
- ✅ Enables future work at scale

---

## Risk Assessment

### High Probability, Low Impact ⚠️

**Quality variations**:
- Some auto-generated rules may be incorrect
- **Mitigation**: Sample validation, confidence filtering
- **Impact**: Low - can filter low-quality rules

**Alignment errors**:
- OpenCyc "bird" ≠ ConceptNet "bird" edge cases
- **Mitigation**: String matching works for 90%+, manual alignment for edge cases
- **Impact**: Low - affects small percentage

### Low Probability, High Impact 🔴

**Extraction completely fails**:
- Technical issues with large files
- **Mitigation**: Proof-of-concept first (1 day)
- **Impact**: High - but we detect early and pivot

**Generated rules too low quality**:
- Can't use for benchmark
- **Mitigation**: Quality threshold filtering, expert validation
- **Impact**: High - but we have fallback (current sources)

### Mitigation Strategy

**Phase-gated approach**:
1. **Proof** (1 day) - validate feasibility
2. **Go/No-Go** decision
3. **Full extraction** (1 week) - only if proof succeeds
4. **Fallback**: Current sources (2,318 rules) work

**No sunk cost**: 1 day for proof is low risk

---

## Implementation Details

### Proof-of-Concept (Day 8.5a)

**Morning** (2-4 hours):
```bash
# 1. Create validation script (DONE)
# scripts/validate_cross_ontology_scale.py

# 2. Run on sample
python scripts/validate_cross_ontology_scale.py

# Expected output:
#   Sample: 1,000 concepts, 100,000 ConceptNet edges
#   Generated: 5,000-15,000 rules
#   Defeaters: 100-500
#   Projected full: 50,000-150,000 rules
```

**Afternoon** (2-4 hours):
```bash
# 3. Quality validation
python scripts/validate_sample_quality.py

# Check:
#   - 100 random rules against encyclopedic sources
#   - Depth >= 2 for sample targets
#   - Instance generation yield

# 4. Decision
#   - If 10x achieved → plan Week 8.6
#   - If not → document findings, continue with current
```

### Full Extraction (Week 8.6)

**File structure**:
```
src/blanc/ontology/
  opencyc_extractor.py          # ENHANCE
  conceptnet_extractor.py       # ENHANCE
  cross_ontology.py             # NEW
  yago_full_extractor.py        # NEW (optional)

scripts/
  extract_cross_ontology_biology.py    # NEW
  extract_cross_ontology_legal.py      # NEW
  extract_cross_ontology_materials.py  # NEW
  validate_large_scale_kb.py           # NEW

examples/knowledge_bases/
  biology_kb_large.py           # NEW (100K rules)
  legal_kb_large.py             # NEW (10K rules)
  materials_kb_large.py         # NEW (50K rules)
```

**Timeline**:
- Day 1-2: Enhance extractors, create cross_ontology.py
- Day 3-4: Biology extraction (100K rules)
- Day 5: Legal extraction (10K rules)
- Day 5: Materials extraction (50K rules)
- Day 6-7: Validation, instance generation, testing

---

## Quality Assurance

### Automated Checks

For each generated rule:
```python
# 1. Syntactic validity
assert is_valid_prolog(rule)

# 2. Derivation depth
theory_subset = sample_around_rule(rule, size=100)
assert max_depth(theory_subset) >= 2

# 3. Defeater coherence (for Level 3)
if rule.type == DEFEATER:
    # Check there exists a defeasible rule to defeat
    assert has_corresponding_default(rule, theory)
```

### Manual Validation (Sample)

**Sample**: 100 random rules

**Check against**:
- Wikipedia articles
- Textbook knowledge
- Other ontologies (cross-validation)

**Quality threshold**: >= 85% correct

**If below threshold**:
- Filter by ConceptNet confidence weight
- Use stricter concept matching
- Validate specific problematic patterns

---

## Expected Outcomes by Domain

### Biology

**OpenCyc taxonomy**:
- Organisms: ~50,000 concepts
- Depth: 5-10 levels (kingdom → species)

**ConceptNet properties**:
- Biology edges: ~500,000 (filtered from 21M)
- CapableOf: ~200,000
- NotCapableOf: ~50,000 (defeaters!)
- HasProperty: ~250,000

**Generated rules**:
- Taxonomic: 50,000
- Behavioral: 100,000-150,000
- Defeaters: 10,000-20,000
- **Total: 160,000-220,000 rules**

**Level 3 potential**: 10,000+ defeater-based instances automatically!

### Legal

**OpenCyc taxonomy**:
- Legal/governmental concepts: ~10,000

**ConceptNet properties**:
- Limited (legal is underrepresented)
- Augment with legal corpus

**Other sources**:
- LKIF Core: 201 rules (current)
- Potential legal ontologies

**Generated rules**: 10,000-30,000

**Note**: May need domain-specific legal sources

### Materials

**OpenCyc taxonomy**:
- Chemistry/materials: ~30,000 concepts

**ConceptNet properties**:
- Materials: ~100,000 edges

**MatOnto** (existing):
- 1,190 structure-property rules

**Combined**: 50,000-100,000 rules

---

## Integration with Level 3 Generation

### The Synergy

**Problem we identified**:
- Need Level 3 (defeater abduction) instances
- Manual generation is slow (35-50 instances in 3-5 days)

**Solution with cross-ontology**:
- ConceptNet NotCapableOf relations ARE defeaters
- 10,000-20,000 defeaters in generated KB
- **Automatic Level 3 instance generation!**

**Algorithm**:
```python
For each defeater in generated KB:
  1. Find the default rule it defeats
     - ~flies(X) :- penguin(X) defeats flies(X) :- bird(X)
  
  2. Create challenge theory without defeater
     - D^- = D \ {~flies(X) :- penguin(X)}
  
  3. Verify anomaly exists
     - D^- ⊢∂ flies(penguin) [wrong!]
  
  4. Create Level 3 instance
     - Anomaly: flies(penguin)
     - Gold: ~flies(X) :- penguin(X)
     - Auto-generated!
```

**Yield**: 
- Manual approach: 35-50 instances in 3-5 days
- Automated approach: **1,000-5,000 instances in 1 day**
- **100x efficiency improvement!**

---

## Updated Week 8.5-9 Timeline

### Week 8.5a: Cross-Ontology Proof (1 day)

**Morning**:
- [ ] Run `scripts/validate_cross_ontology_scale.py`
- [ ] Analyze results
- [ ] Decision: proceed or not?

**Afternoon**:
- If YES: Plan Week 8.6 details
- If NO: Continue with manual Level 3

**Output**: Go/No-Go decision with data

---

### Week 8.5b: Level 3 Instances (3-5 days, parallel)

**If cross-ontology fails**: Manual generation (35-50 instances)

**If cross-ontology succeeds**: SKIP manual generation
- Wait for Week 8.6 automated defeaters
- 100x more efficient

---

### Week 8.6: Full Extraction (1 week, conditional)

**Only if**: Proof-of-concept succeeds

**Day 1-2**: Enhance extractors
**Day 3-4**: Biology extraction (100K rules)
**Day 5**: Legal + materials extraction
**Day 6**: Generate Level 3 instances (1,000+)
**Day 7**: Validation & testing

---

### Week 9: Pilot on Large-Scale (2-3 days)

**Test set**:
- 100 instances (mix of Level 2 + Level 3)
- From large-scale KB
- All three domains

**Validates**:
- Large-scale KB works
- Automatic Level 3 generation works
- Evaluation pipeline scales

---

## Success Metrics

### Proof-of-Concept (Week 8.5a)

**Must achieve**:
- [ ] 5x rule multiplier (sample)
- [ ] 100+ defeaters in sample
- [ ] Quality >= 80% on validation
- [ ] Projected full scale >= 50K rules

**Nice to have**:
- [ ] 10x rule multiplier
- [ ] Instance generation works on sample
- [ ] Alignment accuracy >= 90%

### Full Extraction (Week 8.6)

**Must achieve**:
- [ ] Biology: 100K+ rules
- [ ] Legal: 10K+ rules
- [ ] Materials: 50K+ rules
- [ ] Defeaters: 5K+ (for Level 3)
- [ ] Quality >= 85%
- [ ] All tests pass

**Nice to have**:
- [ ] 200K+ biology rules
- [ ] 20K+ defeaters
- [ ] Quality >= 90%
- [ ] Automatic Level 3: 1,000+ instances

---

## Paper Implications

### Abstract Update (If Successful)

**Current**:
> "Starting from legacy deductive knowledge bases..."

**Enhanced**:
> "We demonstrate a cross-ontology extraction method that combines taxonomic structure from OpenCyc (300K concepts) with behavioral properties from ConceptNet (21M assertions), generating 100,000+ defeasible rules from 1980s legacy knowledge systems. This bridges purely taxonomic ontologies with the behavioral reasoning requirements of modern foundation model evaluation."

### Additional Contribution

**Separate from benchmark**:
> "**Extraction methodology**: We introduce a general method for synthesizing defeasible rule-based knowledge bases from heterogeneous ontology sources, demonstrating that taxonomic ontologies (OpenCyc, YAGO) can be augmented with behavioral property sources (ConceptNet, WordNet) to generate rich defeasible theories suitable for non-monotonic reasoning tasks."

**This could be a separate paper or major contribution!**

### Related Work Addition

Compare to:
- Ontology alignment methods
- KB integration approaches
- Defeasible logic generation

Show our method is novel for:
- Generating defeaters automatically
- Scaling to 100K+ rules
- Maintaining expert provenance

---

## Decision Framework

### Criteria for Proceeding to Week 8.6

**MUST achieve** (all required):
1. ✅ Proof generates >= 5,000 rules from sample
2. ✅ Projected full scale >= 50,000 rules
3. ✅ Defeaters >= 100 in sample
4. ✅ Quality >= 80% on validation
5. ✅ No major technical blockers

**SHOULD achieve** (2 of 3):
1. ⭐ Generates >= 10,000 rules from sample
2. ⭐ Defeaters >= 500 in sample
3. ⭐ Quality >= 90%

**Decision**:
- All MUST + 2 SHOULD → **STRONG GO**
- All MUST + 1 SHOULD → **GO**
- All MUST + 0 SHOULD → **MARGINAL** (discuss)
- Any MUST fails → **NO-GO** (stick with current)

---

## Contingency Plans

### If Proof Fails (Day 8.5a)

**Fallback**:
- Document findings
- Stick with current 2,318 rules
- Manual Level 3 generation (35-50 instances)
- No change to timeline

**Learn**:
- Why didn't it work?
- Alternative approaches?
- Future work direction

### If Full Extraction Fails (Week 8.6)

**Fallback**:
- Use proof-of-concept sample (5K-15K rules)
- Better than current 2,318
- Still publishable

**Recovery**:
- Debug during Week 9
- Can continue with current sources
- No loss of core work

---

## Long-Term Vision

### NeurIPS Submission (Weeks 14)

**Baseline scenario** (current sources):
- 2,318 rules, 374 instances
- Publishable but modest scale

**Enhanced scenario** (cross-ontology):
- 100K-350K rules, 16K-56K instances
- Large-scale benchmark
- Novel extraction method
- **Significantly stronger paper**

### Follow-Up Publications

**If extraction method works**:
1. "Cross-Ontology Defeasible Rule Generation" (methodology paper)
2. "Scaling Defeasible Abduction to 100K Rules" (systems paper)
3. Apply to other domains (medical, engineering, etc.)

### Open Science

**Release**:
- Extraction code (reusable for any domain)
- Generated large-scale KBs
- Benchmark dataset at scale
- Enables community to scale further

---

## Immediate Actions

### Today (Next 4-8 hours)

1. **Run proof-of-concept**:
   ```bash
   python scripts/validate_cross_ontology_scale.py
   ```

2. **Analyze results**:
   - Did we hit 5x multiplier?
   - How many defeaters?
   - Quality acceptable?

3. **Make decision**:
   - GO → plan Week 8.6 in detail
   - NO-GO → document and continue with manual Level 3

4. **Update documentation**:
   - Add results to SCALE_OPPORTUNITY.md
   - Update REVISED_IMPLEMENTATION_PLAN.md
   - Update STATUS.md

---

## Summary

**Question**: Can we 10-100x our ruleset with OpenCyc + ConceptNet?

**Answer**: Almost certainly YES

**Method**: Cross-ontology property mining (taxonomy + behavioral relations)

**Plan**: 
- **Today**: 1-day proof-of-concept
- **If successful**: 1-week full extraction
- **Outcome**: 100K-350K rules, 16K-56K instances

**Impact**: 
- Paper claims validated (actually uses legacy KBs)
- Large-scale benchmark (not just proof-of-concept)
- Novel extraction methodology (publishable)
- Automatic Level 3 generation (5K-20K defeaters!)

**Risk**: Low (phased approach, fallback available)

**Recommendation**: **RUN THE PROOF NOW**

---

**Author**: Patrick Cooper  
**Date**: 2026-02-13  
**Status**: Ready to validate  
**Next**: Run `scripts/validate_cross_ontology_scale.py`
