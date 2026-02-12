# Knowledge Base Requirements: Comprehensive Audit

**Date**: 2026-02-12  
**Purpose**: Comprehensive audit of ALL KB requirements before proceeding  
**Status**: CRITICAL - Complete this before any development  
**Author**: Patrick Cooper

---

## Paper Requirements (Section 4.1)

### Required Domains (3 Total)

Paper specifies THREE knowledge bases spanning different domains:

#### 1. Taxonomic Biology (Π_bio)

**Paper Description** (lines 317-318):
> "A definite logic program encoding phylogenetic classification, morphological properties, and functional mechanisms, drawn from the biological subset of the OpenCyc ontology and supplemented with curated Prolog formalizations of textbook biological knowledge."

**Specifications**:
- **Content**: Phylogenetic classification, morphological properties, functional mechanisms
- **Source**: OpenCyc biology subset + curated Prolog
- **Examples**: Natural defaults ("birds typically fly"), exceptions (penguins, ostriches, IDPs)
- **Target Size**: 100-150 rules (per roadmap)
- **Must Have**: Intrinsically disordered proteins (IDPs) example

**Source Requirements**:
- ✅ Expert-curated: OpenCyc (Cycorp ontology engineers)
- ✅ Citeable: OpenCyc publications
- ✅ Verifiable: Public knowledge base

#### 2. Legal Reasoning (Π_law)

**Paper Description** (lines 319-320):
> "A program encoding statutory rules, case-based precedents, and jurisdictional hierarchies, adapted from existing Prolog formalizations of legal knowledge."

**Specifications**:
- **Content**: Statutory rules, case-based precedents, jurisdictional hierarchies
- **Source**: Existing Prolog legal formalizations (cite: Nute 1997)
- **Examples**: Statutes with exceptions, precedent overruling, jurisdictional conflicts
- **Target Size**: 80-120 rules (per roadmap)
- **Must Have**: Natural defeasibility (statutes admit exceptions, precedents overrule)

**Source Requirements**:
- ✅ Expert-curated: Legal scholars' Prolog formalizations
- ✅ Citeable: Nute 1997 paper
- ⚠️ Need to locate: Actual Prolog programs from paper

#### 3. Materials Science (Π_mat)

**Paper Description** (lines 321-322):
> "A program encoding structure-property relationships, synthesis conditions, and phase behavior, constructed from domain ontologies and handcrafted rules validated by domain experts."

**Specifications**:
- **Content**: Structure-property relationships, synthesis conditions, phase behavior
- **Source**: Domain ontologies + expert-validated rules
- **Examples**: "Crystalline materials are brittle" with exceptions (shape-memory alloys, metallic glasses)
- **Target Size**: 60-100 rules (per roadmap)
- **Must Have**: Expert validation for all rules

**Source Requirements**:
- ⚠️ Expert-curated: Requires domain expert consultation
- ⚠️ Citeable: Need domain ontology source
- ❌ High complexity: Most challenging KB to source

---

## Current Status

### What We Have

1. **YAGO 4.5 (Expert-Curated)** ✅
   - Source: Télécom Paris (2024)
   - Rules: 584 biology-related inference rules
   - Depth: 7 (exceeds requirement)
   - License: Creative Commons Attribution-ShareAlike
   - Citation: Suchanek et al., SIGIR 2024
   - Status: Downloaded and extracted

2. **ConceptNet 5 (Partial)** ⚠️
   - Source: Crowdsourced + expert datasets
   - Status: Previously explored (15,583 biology edges)
   - Issue: Max depth 1 (insufficient)
   - Use case: Validation data only

3. **OpenCyc (Partial)** ⚠️
   - Source: Cycorp ontology engineers
   - Status: Previously explored (33,583 elements)
   - Issue: Max depth 0 (only isa relations)
   - Use case: May need deeper subset

### What We Need

#### For Biology KB

**Current**: YAGO 4.5 (584 rules, depth 7)

**Gaps**:
- [ ] Organism instances (facts) - need to extract from YAGO entities
- [ ] Morphological properties - need to verify YAGO has these
- [ ] Functional mechanisms - need to verify YAGO has these
- [ ] IDP example specifically - need to add or find in YAGO
- [ ] Defeasible rules - YAGO only has strict subclass relationships

**Options**:
1. Extract instances from yago-entities.jsonl (678MB file we have)
2. Supplement YAGO with OpenCyc biology subset
3. Find Prolog biology formalizations (textbook knowledge)

#### For Legal KB

**Current**: Nothing

**Need to Source**:
- [ ] Find Nute 1997 Prolog legal knowledge formalizations
- [ ] Alternative: Look for TaxKB or other legal KBs
- [ ] Alternative: Find court case reasoning databases
- [ ] Verify expert curation and citability

**Search Strategy**:
1. Search for "Nute defeasible logic legal" Prolog code
2. Search for TaxKB legal knowledge base
3. Search for legal ontologies (e.g., LKIF, LegalRuleML)
4. Check if any legal KBs in Prolog format exist

#### For Materials Science KB

**Current**: Nothing

**Need to Source**:
- [ ] Find materials science ontology (MatOnto, materials genome, etc.)
- [ ] Identify domain expert for validation
- [ ] Find structure-property relationship databases
- [ ] Verify expert curation

**Search Strategy**:
1. Search for materials science ontologies
2. Look for materials genome initiative data
3. Search for crystallography databases with rules
4. Identify if any materials KBs in logic format exist

---

## Detailed Source Requirements

### Per Paper Section 4.1

For each KB, must report:

1. **Signature Statistics**:
   - |C| (number of constants)
   - |P| (number of predicates)  
   - |Π| (number of clauses)
   - Dependency graph depth
   - |HB| (Herbrand base size after grounding)

2. **Properties**:
   - Function-free (datalog) ✓ Required
   - Polynomial grounding ✓ Required
   - Depth >= 2 ✓ Required for instance generation

3. **Provenance**:
   - Source documentation
   - Expert authorship verification
   - Citation information
   - License compatibility

---

## Additional Requirements from Roadmap

### Week-by-Week Breakdown

**Week 1: Biology**
- Target: 100-150 rules
- Must include: phylogenetic classification, morphological properties, functional mechanisms, IDPs
- Source: OpenCyc subset + curated Prolog
- Instances: ~400 across 13 partition strategies

**Week 2: Legal**
- Target: 80-120 rules
- Must include: statutory rules, precedents, jurisdictional hierarchies
- Source: Nute 1997 Prolog formalizations
- Instances: ~400 across 13 partition strategies
- Plus: parallel distractor sets (3 strategies)

**Week 3: Materials Science**
- Target: 60-100 rules
- Must include: structure-property, synthesis, phase behavior
- Source: Domain ontologies + expert validation
- Instances: ~350 across 13 partition strategies
- Requires: Domain expert consultation

**Total**: ~1150-1200 instances across 3 KBs

---

## Compliance Checklist

### Before Proceeding with Biology KB

- [x] Expert-curated source identified (YAGO 4.5)
- [x] Source downloaded and accessible
- [x] Rules extracted (584 strict subclass rules)
- [x] Depth verified (depth 7, exceeds requirement)
- [ ] **Organism instances extracted**
- [ ] **Morphological properties verified**
- [ ] **Functional mechanisms verified**
- [ ] **IDP example added**
- [ ] **Defeasible rules added** (need conversion or behavioral rules)
- [ ] Size target met (100-150 rules)
- [ ] Provenance documented
- [ ] Tests passing

### Before Proceeding with Legal KB

- [ ] **Expert-curated source identified**
- [ ] **Source located and accessible**
- [ ] **Nute 1997 code found OR alternative located**
- [ ] Statutory rules extracted
- [ ] Precedent rules extracted
- [ ] Jurisdictional hierarchy extracted
- [ ] Depth >= 2 verified
- [ ] Size target met (80-120 rules)
- [ ] Provenance documented
- [ ] Tests passing

### Before Proceeding with Materials Science KB

- [ ] **Expert-curated source identified**
- [ ] **Domain ontology located**
- [ ] **Domain expert identified for validation**
- [ ] Structure-property rules extracted
- [ ] Synthesis condition rules extracted
- [ ] Phase behavior rules extracted
- [ ] Examples added (crystalline/brittle + exceptions)
- [ ] Expert validation completed
- [ ] Size target met (60-100 rules)
- [ ] Provenance documented
- [ ] Tests passing

---

## Critical Issues to Resolve

### Issue 1: Biology KB Completeness

**Problem**: YAGO has taxonomic rules but we need:
- Organism instances (facts)
- Morphological properties
- Functional mechanisms
- Behavioral rules (for defeasibility)

**Options**:
A. Extract from yago-entities.jsonl (678MB) - instances of biological entities
B. Add OpenCyc biology subset for properties and mechanisms
C. Find Prolog biology textbook formalizations
D. Use WordNet for biological taxonomies

**Recommendation**: Start with A (YAGO entities), supplement with B if needed

### Issue 2: Legal KB Source

**Problem**: Paper cites "Nute 1997" but we don't have the actual Prolog code

**Options**:
A. Search for Nute's defeasible logic legal formalizations
B. Use TaxKB (tax law knowledge base) if available
C. Find alternative legal Prolog formalizations
D. Use LKIF (Legal Knowledge Interchange Format) ontology

**Recommendation**: Comprehensive search for A, B, C; D as last resort

### Issue 3: Materials Science Expert Validation

**Problem**: Paper explicitly requires "domain experts" to validate

**Options**:
A. Find existing expert-validated materials ontology
B. Hire materials science consultant ($1500-3000)
C. Collaborate with university materials science dept
D. Use MatOnto or similar if expert-validated

**Recommendation**: A first (find existing), then C (free collaboration), B if necessary

### Issue 4: Defeasible Rules

**Problem**: YAGO only has strict subclass relationships, but we need defeasible defaults

**Options**:
A. Identify which strict rules should be defeasible based on literature
B. Extract behavioral rules that are naturally defeasible
C. Use WordNet/ConceptNet for defeasible behavioral predicates
D. Expert consultation to mark defeasible vs strict

**Recommendation**: B + C (extract behavioral rules from other sources)

---

## Search Tasks (Immediate Action Items)

### Task 1: Complete YAGO Biology KB

1. **Extract organism instances** from yago-entities.jsonl
   - Parse JSONL format
   - Filter for biological entities
   - Convert to facts in our format
   - Verify coverage (need diverse organisms)

2. **Verify morphological coverage**
   - Search YAGO for anatomical properties
   - Check if "has_wings", "has_feathers" type predicates exist
   - Add from OpenCyc if missing

3. **Verify functional mechanisms**
   - Search YAGO for biological functions
   - Check if behavioral predicates exist
   - Add from domain sources if missing

4. **Add IDP example**
   - Either find in YAGO or add from literature
   - Cite original IDP discovery paper

### Task 2: Locate Legal KB Source

1. **Search for Nute legal Prolog**
   - Google Scholar: "Nute defeasible logic legal Prolog"
   - Check Nute's publications for code repositories
   - Email authors if necessary

2. **Search for TaxKB**
   - Google: "TaxKB tax law knowledge base download"
   - Check legal informatics conferences
   - Look for open legal data initiatives

3. **Alternative legal KBs**
   - LKIF (Legal Knowledge Interchange Format)
   - LegalRuleML repositories
   - Court decision databases with rules
   - European legal ontologies

### Task 3: Locate Materials Science KB

1. **Search for materials ontologies**
   - MatOnto (materials science ontology)
   - Materials Genome Initiative databases
   - Crystallography databases
   - Materials informatics repositories

2. **Search for expert-validated sources**
   - NIST materials databases
   - International materials science databases
   - Academic materials science repositories
   - Check if any in logic format

3. **Domain expert options**
   - University materials science departments
   - Materials science research institutes
   - Online expert networks (ResearchGate, etc.)

---

## Decision Points

### Decision 1: Proceed with Biology KB Now?

**Question**: Do we have enough to complete biology KB?

**Current State**:
- ✅ 584 expert rules from YAGO
- ✅ yago-entities.jsonl available (678MB)
- ⚠️ Need to extract instances
- ⚠️ Need to verify morphological/functional coverage

**Options**:
A. **YES** - Proceed with YAGO entity extraction, verify coverage, supplement if needed
B. **NO** - Wait until we source all 3 KBs comprehensively

**Recommendation**: **A** - Proceed with biology, but PAUSE after to ensure legal/materials sourced before Week 2

### Decision 2: Comprehensive Search First?

**Question**: Should we source all 3 KBs before building any?

**Options**:
A. **Sequential**: Complete biology → search legal → complete legal → search materials → complete materials
B. **Parallel Search**: Search for all 3 sources NOW, then build all 3
C. **Staged**: Complete biology this week, search legal/materials in parallel for next week

**Recommendation**: **C** - Complete biology KB while searching for legal/materials

### Decision 3: Timeline Adjustment?

**Question**: If legal/materials take longer to source, adjust timeline?

**Options**:
A. **Strict**: Must have all 3 KBs within 3 weeks (as per roadmap)
B. **Flexible**: Extend Week 1-3 if sourcing takes longer
C. **Alternative**: Use 2 KBs (biology + legal OR biology + materials) if 3rd unsourceable

**Recommendation**: **B** - Quality over speed; proper sourcing is critical

---

## Next Steps (Priority Order)

### Immediate (Today)

1. **Extract YAGO organism instances**
   - Parse yago-entities.jsonl
   - Filter for biology
   - Generate facts
   - Verify coverage

2. **Search for legal KB sources**
   - Nute 1997 code
   - TaxKB
   - Alternative legal Prolog

3. **Search for materials KB sources**
   - MatOnto
   - Materials databases
   - Expert-validated sources

### This Week

4. **Complete biology KB**
   - Integrate YAGO rules + instances
   - Verify morphological properties
   - Verify functional mechanisms
   - Add IDP example
   - Document provenance
   - Test thoroughly

5. **Finalize legal KB source**
   - Obtain code/data
   - Verify expert curation
   - Verify citability
   - Plan extraction

6. **Finalize materials KB source**
   - Obtain code/data
   - Identify domain expert
   - Verify expert curation
   - Plan extraction

### Next Week

7. **Extract legal KB**
8. **Extract materials KB**
9. **Generate instances from all 3**

---

## Success Criteria

### Overall

- [ ] ALL 3 KBs are expert-curated (verified)
- [ ] ALL 3 KBs are citeable (papers/DOIs)
- [ ] ALL 3 KBs meet size requirements
- [ ] ALL 3 KBs have depth >= 2
- [ ] ALL 3 KBs are function-free (datalog)
- [ ] ALL 3 KBs have documented provenance
- [ ] Total ~1150-1200 instances generated

### Biology KB Specific

- [ ] 100-150 rules
- [ ] Phylogenetic classification ✓
- [ ] Morphological properties
- [ ] Functional mechanisms
- [ ] IDP example
- [ ] Natural defaults + exceptions
- [ ] Depth >= 2 ✓ (depth 7)

### Legal KB Specific

- [ ] 80-120 rules
- [ ] Statutory rules
- [ ] Case-based precedents
- [ ] Jurisdictional hierarchies
- [ ] Natural defeasibility
- [ ] Depth >= 2

### Materials KB Specific

- [ ] 60-100 rules
- [ ] Structure-property relationships
- [ ] Synthesis conditions
- [ ] Phase behavior
- [ ] Crystalline/brittle example + exceptions
- [ ] Expert validation
- [ ] Depth >= 2

---

## Risk Assessment

### High Risk

1. **Materials Science KB** - Requires expert validation, may be hard to source
2. **Legal KB Source** - Nute 1997 code may not be publicly available
3. **Timeline** - 3 KBs in 3 weeks is aggressive if sourcing is difficult

### Medium Risk

1. **Biology KB Completeness** - May need multiple sources to complete
2. **Defeasible Rules** - YAGO is strict only, need behavioral defeasibility
3. **IDP Example** - May not exist in standard KBs

### Low Risk

1. **Biology KB Core** - YAGO provides solid foundation
2. **Technical Infrastructure** - Extraction code proven to work
3. **Expert Curation** - YAGO verifiably expert-curated

---

## Blockers

### Current Blockers

1. **Biology**: Need to extract YAGO entities (in progress)
2. **Legal**: Need to locate source KB (not started)
3. **Materials**: Need to locate source KB AND expert (not started)

### Potential Blockers

1. **Legal**: Nute 1997 code unavailable → need alternative
2. **Materials**: No expert-validated ontology exists → need expert hire
3. **Timeline**: All 3 KBs take > 3 weeks → adjust roadmap

---

**Status**: AUDIT COMPLETE  
**Action**: Proceed with YAGO entity extraction while searching for legal/materials sources  
**Next Review**: After biology KB complete, before Week 2
