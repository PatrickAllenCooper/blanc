# Knowledge Base Policy: Expert-Curated Sources Only

**Status**: MANDATORY - Core Project Requirement  
**Author**: Anonymous Authors  
**Date**: 2026-02-12  
**Enforcement**: ALL knowledge bases must comply

---

## Fundamental Rule

**ALL KNOWLEDGE BASES MUST BE HUMAN EXPERT-POPULATED**

We do NOT create hand-crafted, synthetic, or artificial knowledge bases.  
We ONLY use knowledge bases that have been populated by human domain experts.

---

## Rationale

### Why Expert-Curated Only?

1. **Scientific Validity**: Expert knowledge represents validated, peer-reviewed understanding
2. **Real-World Grounding**: Experts encode actual domain knowledge, not synthetic examples
3. **Benchmark Integrity**: Evaluations must test against real human expertise
4. **Reproducibility**: Expert sources can be cited and verified
5. **Paper Merit**: Using expert KBs demonstrates real-world applicability

### Why NOT Hand-Crafted?

Hand-crafted KBs suffer from:
- **Author bias**: Reflects creator's limited knowledge
- **Limited scope**: Cannot match breadth of expert curation
- **Validation issues**: No peer review or expert verification
- **Credibility gap**: Reviewers will question synthetic data
- **Wasted effort**: Experts have already done this work

---

## Approved Sources

### Currently Used

1. **YAGO 4.5**
   - Source: Télécom Paris, expert-curated
   - Based on: Wikidata (human-edited) + schema.org
   - Size: 49M entities, 109M facts
   - Quality: Peer-reviewed, SIGIR 2024 publication
   - Status: ✅ APPROVED

### Under Consideration

2. **DBpedia**
   - Source: Wikipedia extraction
   - Quality: Human-edited Wikipedia content
   - Status: ⏳ EVALUATE

3. **ConceptNet 5**
   - Source: Crowdsourced + expert datasets
   - Quality: Mix of expert and crowd validation
   - Status: ⏳ EVALUATE (for validation only)

4. **WordNet**
   - Source: Princeton linguists
   - Quality: Expert lexicographers
   - Status: ⏳ EVALUATE

5. **OpenCyc**
   - Source: Cycorp ontology engineers
   - Quality: Professional ontologists
   - Status: ⏳ EVALUATE

6. **NELL (CMU)**
   - Source: Machine learning + human verification
   - Quality: Human-verified assertions
   - Status: ⏳ EVALUATE (verify human validation rate)

### NOT Approved

- ❌ Hand-written rules by project author
- ❌ Synthetic generated examples
- ❌ LLM-generated knowledge
- ❌ Unvalidated crowdsourced data
- ❌ Student-created toy examples

---

## Evaluation Criteria

Before using any knowledge base, verify:

1. **Expert Authorship**
   - [ ] Created/curated by domain experts
   - [ ] Documented authorship/provenance
   - [ ] Peer-reviewed or professionally maintained

2. **Quality Control**
   - [ ] Validation process documented
   - [ ] Error correction mechanism
   - [ ] Community review or expert oversight

3. **Citability**
   - [ ] Published dataset with DOI
   - [ ] Academic paper describing creation
   - [ ] Version control and updates

4. **Accessibility**
   - [ ] Publicly downloadable
   - [ ] Open or research-friendly license
   - [ ] Documented format and schema

5. **Scale**
   - [ ] Sufficient size for benchmark (100+ rules minimum)
   - [ ] Depth >= 2 for derivation chains
   - [ ] Multiple domains/categories available

---

## Enforcement

### Required Actions

1. **Before Adding Any KB**:
   - Document source and authorship
   - Verify expert curation
   - Add to "Approved Sources" section
   - Cite original publication

2. **In Code**:
   - Add provenance comments to KB files
   - Include citation in module docstring
   - Link to original source

3. **In Paper**:
   - Cite original KB papers
   - Acknowledge expert creators
   - Describe curation process

### Violation Response

If hand-crafted KB is discovered:
1. STOP using immediately
2. Revert to last compliant state
3. Find expert-curated replacement
4. Document why it was non-compliant

---

## Current Project Status

### Week 1 Issue (RESOLVED)

**Problem**: Created `biology_curated.py` with hand-written rules  
**Status**: ❌ NON-COMPLIANT  
**Resolution**: Replaced with YAGO extraction  
**New Source**: YAGO 4.5 (584 expert-curated rules)

### Going Forward

All future KBs must:
- Use YAGO, DBpedia, WordNet, or similar expert sources
- Extract and transform (NOT create)
- Maintain provenance chain to expert source
- Document extraction methodology

---

## KB Development Workflow

### Correct Approach

```
1. Identify expert-curated source (YAGO, DBpedia, etc.)
2. Download/access original data
3. Extract relevant subset
4. Transform to our format (preserving semantics)
5. Document provenance and extraction process
6. Verify against original source
7. Add to project with full citation
```

### Incorrect Approach (DO NOT DO)

```
❌ 1. Think about domain knowledge
❌ 2. Write rules based on your understanding
❌ 3. Add facts you think are true
❌ 4. Create your own taxonomy
```

---

## Examples

### ✅ CORRECT: YAGO Extraction

```python
"""
Biology KB extracted from YAGO 4.5.

Source: YAGO 4.5 (Télécom Paris, 2024)
Citation: Suchanek et al., "YAGO 4.5: A Large and Clean Knowledge Base 
          with a Rich Taxonomy", SIGIR 2024
Expert Curation: Wikidata editors + schema.org + YAGO team
Extraction: Taxonomic subclass relationships for biology domain
"""
```

### ❌ INCORRECT: Hand-Crafted

```python
"""
Biology KB.

Created based on general knowledge of biology.
Rules written by author.
"""
```

---

## FAQ

**Q: What if we need rules not in existing KBs?**  
A: Either (1) find a different expert KB that has them, or (2) acknowledge the limitation and use what exists. Do NOT create them yourself.

**Q: Can we clean/filter expert KBs?**  
A: YES - extraction, filtering, and transformation are allowed. Creation is not.

**Q: Can we add defeasible annotations to strict rules?**  
A: YES - semantic transformation preserving original meaning is allowed.

**Q: What about the MVP avian biology KB?**  
A: It was a prototype for algorithm development. Full benchmark MUST use expert sources.

**Q: Can we validate extracted rules against our knowledge?**  
A: NO - validate against OTHER expert sources (cross-reference). Your knowledge is not authoritative.

---

## Compliance Checklist

Before committing any KB:

- [ ] Source is expert-curated (documented)
- [ ] Provenance documented in code
- [ ] Original publication cited
- [ ] Extraction methodology documented
- [ ] No hand-written rules added
- [ ] Cross-validated against other expert sources (if possible)

---

## References

1. YAGO 4.5: https://yago-knowledge.org/
2. DBpedia: https://www.dbpedia.org/
3. ConceptNet 5: https://conceptnet.io/
4. WordNet: https://wordnet.princeton.edu/
5. OpenCyc: http://www.cyc.com/opencyc/

---

**REMEMBER**: We are evaluating foundation models on how well they match EXPERT knowledge, not our personal understanding. The KBs must represent expert consensus, not individual opinion.

---

**Status**: ACTIVE POLICY  
**Last Updated**: 2026-02-12  
**Next Review**: Before each new KB addition
