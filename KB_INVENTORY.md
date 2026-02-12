# Knowledge Base Inventory: Complete Download Status

**Date**: 2026-02-12  
**Status**: ALL REQUIRED KBs DOWNLOADED  
**Policy**: Expert-curated sources only (see KNOWLEDGE_BASE_POLICY.md)

---

## Summary

Successfully downloaded **6 expert-curated knowledge bases** covering all 3 required domains:

- **Biology**: YAGO 4.5 + WordNet + OpenCyc
- **Legal**: LKIF Core + DAPRECO GDPR
- **Materials**: MatOnto

**Total Size**: ~600 MB  
**All Sources**: Expert-curated, citeable, compliant with policy

---

## Downloaded Knowledge Bases

### 1. YAGO 4.5 (PRIMARY - Biology/General)

**Purpose**: Primary biology KB (taxonomic, morphological, functional)

**Details**:
- **Source**: Télécom Paris (Suchanek et al., 2024)
- **Citation**: "YAGO 4.5: A Large and Clean Knowledge Base with a Rich Taxonomy", SIGIR 2024
- **Expert Curation**: Wikidata editors + schema.org + YAGO team
- **License**: Creative Commons Attribution-ShareAlike
- **Format**: Turtle (RDF)
- **Size**: 191.5 MB (tiny version) + 144.7 MB (entities)
- **Content**: 
  - 49M entities total
  - 109M facts total
  - Biology subset extracted: 584 rules, depth 7
- **Location**: `data/yago/`
  - `yago-4.5.0.2-tiny/yago-tiny.ttl` (1.7 GB uncompressed)
  - `yago-entities.jsonl/yago-entities.jsonl` (678 MB uncompressed)
- **Status**: ✅ Downloaded and extracted
- **Extracted Rules**: `examples/knowledge_bases/yago_biology_extracted.py` (584 rules)

**What We Can Extract**:
- Taxonomic hierarchy (subClassOf chains)
- Organism instances (from entities file)
- Biological properties
- Phylogenetic classification

**Limitations**:
- Only strict rules (no defeasible defaults yet)
- Need to extract instances from entities file
- Need behavioral predicates from other sources

---

### 2. WordNet 3.0 (SUPPLEMENTARY - Biology/Linguistics)

**Purpose**: Lexical taxonomic relationships, synonym/hypernym chains

**Details**:
- **Source**: Princeton University (linguist experts)
- **Citation**: Miller, G. A. (1995). WordNet: A lexical database for English
- **Expert Curation**: Princeton lexicographers
- **License**: Free for research and commercial use
- **Format**: NLTK corpus
- **Size**: Standard NLTK package
- **Content**:
  - 117,659 synsets total
  - 82,115 noun synsets
  - 13,767 verb synsets
  - 26+ bird hyponyms
- **Location**: `data/wordnet/` (reference) + NLTK data directory
- **Status**: ✅ Downloaded via NLTK
- **Access**: `from nltk.corpus import wordnet as wn`

**What We Can Extract**:
- Hypernym/hyponym chains (is-a relationships)
- Biological organism taxonomy
- Behavioral verbs (flies, swims, etc.)
- Meronyms (part-of relationships)

**Use Cases**:
- Supplement YAGO with linguistic relationships
- Extract behavioral predicates
- Cross-validate biological taxonomy
- Add depth to derivation chains

---

### 3. OpenCyc 2012 (SUPPLEMENTARY - Biology/General)

**Purpose**: Million-axiom expert ontology (paper-cited source)

**Details**:
- **Source**: Cycorp (professional ontology engineers)
- **Citation**: Lenat, D. B. (1995). CYC: A Large-Scale Investment in Knowledge Infrastructure
- **Expert Curation**: Cycorp ontology engineers (hand-crafted axioms)
- **License**: Apache 2.0
- **Format**: OWL (XML-compatible)
- **Size**: 26.8 MB compressed
- **Content**: 
  - ~240K concepts
  - ~2M assertions
  - Biology subset previously analyzed: 33,583 elements
- **Location**: `data/opencyc/opencyc-2012-05-10-readable.owl.gz`
- **Status**: ✅ Downloaded
- **Previous Extraction**: Done (see prior work - had max depth 0 issue)

**What We Can Extract**:
- BiologicalOrganism hierarchy
- Morphological properties  
- Functional mechanisms
- Cross-validation with YAGO

**Limitations**:
- OWL format (need parser)
- Previously found depth 0 (only isa relations)
- May need deeper property extraction

---

### 4. LKIF Core (PRIMARY - Legal)

**Purpose**: Primary legal KB (legal concepts, actions, norms)

**Details**:
- **Source**: University of Amsterdam (ESTRELLA project)
- **Citation**: Hoekstra, Boer, van den Berg - LKIF Core ontology
- **Expert Curation**: Legal informatics researchers
- **License**: Open source
- **Format**: OWL
- **Size**: ~194 KB total (10 modules)
- **Content**:
  - 154 classes
  - 96 properties
  - Maximum depth: 7
- **Location**: `data/lkif-core/`
  - `lkif-core.owl` (main)
  - `action.owl`, `legal-action.owl`, `legal-role.owl`
  - `norm.owl`, `expression.owl`
  - `mereology.owl`, `process.owl`, `role.owl`, `time.owl`
- **Status**: ✅ Downloaded (10/12 files - 2 don't exist in repo)

**What We Can Extract**:
- Legal action taxonomy
- Normative rules (obligations, permissions, prohibitions)
- Legal role hierarchies
- Temporal legal reasoning

**Modules**:
- **norm.owl** (44 KB): Deontic concepts, legal norms
- **legal-action.owl** (17 KB): Legal acts, procedures
- **expression.owl** (56 KB): Legal expressions, propositions
- **action.owl** (17 KB): General action taxonomy

**Potential for Defeasibility**:
- Norms can be defeasible (exceptions to rules)
- Legal actions can have conditional applicability
- Jurisdiction hierarchies for priority

---

### 5. DAPRECO GDPR (SUPPLEMENTARY - Legal)

**Purpose**: GDPR legal rules (largest LegalRuleML KB)

**Details**:
- **Source**: University of Luxembourg (Robaldo, Bartolini, Lenzini)
- **Citation**: "The DAPRECO Knowledge Base: Representing the GDPR in LegalRuleML", LREC 2020
- **Expert Curation**: Legal scholars (GDPR formalization)
- **License**: Open source (GitHub)
- **Format**: LegalRuleML (XML)
- **Size**: 5.6 MB
- **Content**:
  - GDPR provisions as deontic rules
  - If-then rules in reified I/O logic
  - Based on PrOnto (Privacy Ontology)
- **Location**: `data/dapreco/rioKB_GDPR.xml`
- **Status**: ✅ Downloaded

**What We Can Extract**:
- Deontic legal rules (obligations, permissions)
- Conditional legal reasoning
- Exception handling (GDPR has many qualifications)
- Privacy-related legal concepts

**Advantages**:
- Explicit rule format (easier to parse)
- Naturally defeasible (legal qualifications)
- Expert-validated GDPR representation
- Published and peer-reviewed

---

### 6. MatOnto (PRIMARY - Materials Science)

**Purpose**: Primary materials science KB

**Details**:
- **Source**: MatPortal (materials science community)
- **Citation**: Bryan Miller (contact), matportal.org
- **Expert Curation**: Materials science researchers
- **License**: Open (MatPortal)
- **Format**: OWL
- **Size**: 1.3 MB
- **Content**:
  - 848 classes (updated from earlier 1,307)
  - 131 individuals
  - 96 properties
  - Maximum depth: 10
- **Location**: `data/matonto/MatOnto-ontology.owl`
- **Status**: ✅ Downloaded
- **Based On**: BFO (Basic Formal Ontology) upper ontology

**What We Can Extract**:
- Material class hierarchy
- Structure-property relationships
- Synthesis/processing concepts
- Phase behavior

**Requires**:
- OWL parser
- Domain expert validation of extracted rules
- Verification against paper requirements

---

## Data Organization

```
data/
├── yago/                       # Primary biology source
│   ├── yago-4.5.0.2-tiny/
│   │   └── yago-tiny.ttl      (1.7 GB - taxonomy, schema, facts)
│   ├── yago-entities.jsonl/
│   │   └── yago-entities.jsonl (678 MB - entity instances)
│   ├── yago-4.5.0.2-tiny.zip  (191 MB - original)
│   └── yago-entities.jsonl.zip (145 MB - original)
│
├── wordnet/                    # Supplementary biology/linguistics
│   └── wordnet_info.txt       (NLTK corpus reference)
│
├── opencyc/                    # Supplementary biology (paper-cited)
│   └── opencyc-2012-05-10-readable.owl.gz (27 MB)
│
├── lkif-core/                  # Primary legal source
│   ├── lkif-core.owl          (2.7 KB - main ontology)
│   ├── norm.owl               (44 KB - legal norms)
│   ├── legal-action.owl       (17 KB - legal actions)
│   ├── legal-role.owl         (4.4 KB - legal roles)
│   ├── expression.owl         (56 KB - legal expressions)
│   ├── action.owl             (17 KB - general actions)
│   ├── mereology.owl          (12 KB - part-whole relations)
│   ├── process.owl            (14 KB - processes)
│   ├── role.owl               (16 KB - role ontology)
│   └── time.owl               (13 KB - temporal concepts)
│
├── dapreco/                    # Supplementary legal
│   └── rioKB_GDPR.xml         (5.6 MB - GDPR legal rules)
│
└── matonto/                    # Primary materials science
    └── MatOnto-ontology.owl   (1.3 MB - materials ontology)
```

**Total Downloaded**: ~600 MB (compressed) + ~2.5 GB (uncompressed)

---

## Mapping to Paper Requirements

### Domain 1: Biology (Π_bio)

**Paper Requires**: Phylogenetic classification, morphological properties, functional mechanisms

**Sources Available**:
- **Primary**: YAGO 4.5
  - ✅ Phylogenetic: 584 taxonomic rules, depth 7
  - ⚠️ Morphological: Need to verify/extract from YAGO
  - ⚠️ Functional: Need to extract or supplement
  - ⚠️ Instances: Need to extract from entities file

- **Supplementary**: WordNet
  - ✅ Taxonomic: 82K noun synsets (hypernym chains)
  - ✅ Behavioral: 13K verb synsets
  - ✅ Can provide organism taxonomy

- **Supplementary**: OpenCyc
  - ✅ Paper-cited source
  - ⚠️ Previously had depth 0 issue
  - ⚠️ May need better extraction strategy

**Status**: ✅ Sources downloaded, extraction in progress

### Domain 2: Legal (Π_law)

**Paper Requires**: Statutory rules, case precedents, jurisdictional hierarchies

**Sources Available**:
- **Primary**: LKIF Core
  - ✅ Legal norms: 154 classes, depth 7
  - ✅ Legal actions: Explicit legal act hierarchy
  - ✅ Legal roles: Jurisdictional concepts
  - ⚠️ Need to extract rules format

- **Supplementary**: DAPRECO GDPR
  - ✅ Explicit rules: If-then legal rules
  - ✅ Deontic logic: Obligations, permissions
  - ✅ Naturally defeasible: GDPR exceptions
  - ✅ Largest LegalRuleML KB available

**Status**: ✅ Sources downloaded, extraction needed

**Note**: Did NOT find Nute 1997 Prolog code (may not be publicly available)
**Alternative**: LKIF + DAPRECO provide expert legal knowledge in structured format

### Domain 3: Materials Science (Π_mat)

**Paper Requires**: Structure-property relationships, synthesis conditions, phase behavior

**Sources Available**:
- **Primary**: MatOnto
  - ✅ Materials classes: 848 classes, depth 10
  - ✅ Materials properties: 96 properties
  - ✅ Materials instances: 131 individuals
  - ⚠️ Need to verify structure-property rules
  - ⚠️ Need domain expert validation

**Status**: ✅ Source downloaded, expert validation needed

**Gap**: Still need domain expert to:
- Validate extracted rules
- Verify structure-property mappings
- Confirm synthesis/phase behavior coverage
- Review defeasible defaults (e.g., "crystalline → brittle")

---

## Extraction Status

### Completed

- [x] YAGO 4.5 biology: 584 rules extracted, depth 7
- [x] All sources downloaded
- [x] Directory structure organized

### In Progress

- [ ] YAGO entities: Extract organism instances (678 MB to parse)
- [ ] YAGO properties: Extract morphological/functional predicates
- [ ] WordNet: Extract biological taxonomy and behaviors
- [ ] OpenCyc: Extract biology subset (retry with better strategy)

### Not Started

- [ ] LKIF Core: Extract legal rules
- [ ] DAPRECO: Parse LegalRuleML to our format
- [ ] MatOnto: Extract materials science rules
- [ ] All KBs: Add instance facts
- [ ] All KBs: Verify depth >= 2
- [ ] All KBs: Add defeasible rules

---

## Expert Curation Verification

### Biology Sources

1. **YAGO 4.5**: ✅ VERIFIED
   - Creators: Télécom Paris research team
   - Process: Wikidata (human-edited) + schema.org + YAGO curation
   - Publication: SIGIR 2024 (peer-reviewed)
   - Quality: Logical consistency, SHACL constraints

2. **WordNet**: ✅ VERIFIED
   - Creators: Princeton University linguists
   - Process: Expert lexicographers
   - Publication: Miller (1995), widely cited
   - Quality: Gold standard lexical database

3. **OpenCyc**: ✅ VERIFIED
   - Creators: Cycorp professional ontologists
   - Process: Hand-crafted axioms (1984-2012)
   - Publication: Lenat (1995), multiple papers
   - Quality: Million-axiom scale, 28 years of curation

### Legal Sources

1. **LKIF Core**: ✅ VERIFIED
   - Creators: University of Amsterdam researchers
   - Process: European ESTRELLA project
   - Publication: Multiple papers on legal ontologies
   - Quality: Used in legal informatics research

2. **DAPRECO**: ✅ VERIFIED
   - Creators: University of Luxembourg legal scholars
   - Process: Expert GDPR formalization
   - Publication: LREC 2020 (peer-reviewed)
   - Quality: Largest LegalRuleML KB available

### Materials Science Sources

1. **MatOnto**: ✅ VERIFIED
   - Creators: Materials science research community
   - Process: MatPortal community curation
   - Contact: Bryan Miller (domain expert)
   - Quality: BFO-based, 848 classes, 10 depth levels

**ALL SOURCES MEET EXPERT-CURATION REQUIREMENTS**

---

## Next Steps

### Immediate (This Week)

1. **Extract YAGO biology completely**
   - Parse yago-entities.jsonl for organism instances
   - Extract morphological properties
   - Extract functional mechanisms
   - Verify depth >= 2 with instances
   - Add defeasible behavioral rules

2. **Extract legal KB**
   - Parse LKIF Core OWL files
   - Extract norm hierarchies
   - Add DAPRECO GDPR rules
   - Combine into unified legal KB
   - Ensure 80-120 rules, depth >= 2

3. **Extract materials KB**
   - Parse MatOnto OWL
   - Extract class hierarchy
   - Extract property relationships
   - Contact domain expert for validation
   - Ensure 60-100 rules, depth >= 2

### This Month

4. **Generate instances from all 3 KBs**
   - ~400 instances per KB
   - All 13 partition strategies
   - Levels 1-2 initially
   - Total: ~1200 instances

5. **Validate all KBs**
   - Verify expert provenance
   - Cross-reference facts
   - Document extraction methodology
   - Ensure policy compliance

---

## File Sizes

```
Downloaded (compressed):
  yago-4.5.0.2-tiny.zip:              191.5 MB
  yago-entities.jsonl.zip:            144.7 MB
  opencyc-2012-05-10-readable.owl.gz:  26.8 MB
  MatOnto-ontology.owl:                 1.3 MB
  rioKB_GDPR.xml:                       5.6 MB
  LKIF Core (10 files):                ~0.2 MB
  WordNet (NLTK):                       ~10 MB
  ----------------------------------------
  TOTAL COMPRESSED:                    ~380 MB

Uncompressed:
  yago-tiny.ttl:                      1698 MB
  yago-entities.jsonl:                 678 MB
  opencyc (to extract):               ~300 MB (est)
  Others:                               ~10 MB
  ----------------------------------------
  TOTAL UNCOMPRESSED:                ~2,686 MB
```

---

## Coverage Analysis

### Biology Coverage ✅ EXCELLENT

**Multiple expert sources covering**:
- Taxonomy: YAGO + WordNet + OpenCyc (highly redundant, good)
- Organisms: YAGO entities (49M entities, subset will be large)
- Behaviors: WordNet verbs (flies, swims, migrates)
- Properties: Need to extract from YAGO + OpenCyc

**Confidence**: HIGH - Multiple expert sources, can cross-validate

### Legal Coverage ✅ GOOD

**Two complementary expert sources**:
- Ontology: LKIF Core (legal concepts and norms)
- Rules: DAPRECO (explicit GDPR rules)

**Confidence**: MEDIUM-HIGH - Have expert sources, need to verify rule extraction
**Risk**: No case precedents explicitly (may need to synthesize from norms)

### Materials Coverage ⚠️ ADEQUATE

**One expert source**:
- MatOnto: Materials ontology (expert-curated)

**Confidence**: MEDIUM - Have expert source, but:
- Need domain expert validation
- Need to verify structure-property rules exist
- Need to verify synthesis/phase rules exist
- May need supplementary sources

**Risk**: Highest of three domains, may need expert consultation

---

## Compliance Status

### Expert-Curated Policy ✅ COMPLIANT

ALL 6 knowledge bases are expert-curated:
- ✅ YAGO: Télécom Paris researchers
- ✅ WordNet: Princeton linguists
- ✅ OpenCyc: Cycorp ontologists
- ✅ LKIF: University of Amsterdam researchers
- ✅ DAPRECO: University of Luxembourg legal scholars
- ✅ MatOnto: Materials science community

**NO hand-crafted KBs** - all from expert sources

### Citability ✅ COMPLIANT

ALL sources have:
- ✅ Published papers or official repositories
- ✅ Documented authorship
- ✅ Verifiable provenance
- ✅ Open licenses for research use

### Size Requirements ⚠️ TO BE VERIFIED

Need to extract and verify:
- [ ] Biology: 100-150 rules (have 584 extracted, need instances)
- [ ] Legal: 80-120 rules (need to extract from LKIF + DAPRECO)
- [ ] Materials: 60-100 rules (need to extract from MatOnto)

---

## Risk Assessment

### Low Risk ✅

- Biology KB sourcing: Multiple expert sources available
- Legal KB sourcing: Two good expert sources
- Expert curation policy: All sources verified
- Download infrastructure: All working

### Medium Risk ⚠️

- Materials KB coverage: Single source, need expert validation
- YAGO instance extraction: Large file (678 MB) to parse
- OpenCyc extraction: Previous depth issue, may need retry
- Rule format conversion: OWL → Prolog format

### Action Items to Mitigate

1. **Start materials expert search now** (don't wait until Week 3)
2. **Cross-validate all KBs** against each other
3. **Test depth on extracted rules** before proceeding
4. **Document all extraction methodologies** for paper

---

## Success Metrics

### Downloads ✅ COMPLETE

- [x] YAGO 4.5 downloaded (336 MB)
- [x] WordNet downloaded (via NLTK)
- [x] OpenCyc downloaded (27 MB)
- [x] LKIF Core downloaded (10 files)
- [x] DAPRECO downloaded (5.6 MB)
- [x] MatOnto downloaded (1.3 MB)

**Total**: 6/6 required KBs downloaded

### Organization ✅ COMPLETE

- [x] All KBs in data/ directory
- [x] Subdirectories per KB
- [x] Download scripts created
- [x] Inventory documented

### Extraction ⏳ IN PROGRESS

- [x] YAGO taxonomy extracted (584 rules, depth 7)
- [ ] YAGO instances to extract
- [ ] WordNet to extract
- [ ] OpenCyc to extract
- [ ] LKIF to extract
- [ ] DAPRECO to extract
- [ ] MatOnto to extract

---

## Conclusion

**STATUS**: ✅ ALL REQUIRED EXPERT-CURATED KBs DOWNLOADED

We have successfully sourced expert-curated knowledge bases for all 3 required domains:
- **Biology**: 3 expert sources (YAGO, WordNet, OpenCyc)
- **Legal**: 2 expert sources (LKIF, DAPRECO)
- **Materials**: 1 expert source (MatOnto) + expert validation needed

**Ready to proceed with extraction and KB building using ONLY expert-curated sources.**

---

**Next**: Extract instances and rules from all 6 sources  
**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Download phase complete, extraction phase ready
