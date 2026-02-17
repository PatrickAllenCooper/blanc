# Complete Inventory: Government-Sponsored Knowledge Bases

**All Large-Scale Government KB Programs for BLANC**

---

## 1980s-1990s Legacy Programs (Paper's Focus)

### 1. Cyc / OpenCyc (USA - DARPA Strategic Computing Initiative)

**Agency**: DARPA (1984-present), now Cycorp  
**Scale**:
- Full Cyc: 25 million assertions (2024)
- OpenCyc 4.0: 239,000 terms, 2,093,000 triples
- ResearchCyc: Larger than OpenCyc (license required)

**Content**: Upper ontology, common sense, all domains  
**Format**: CycL (higher-order logic)  
**Status**: ✅ OpenCyc freely available  
**Extraction potential**: 100K-300K defeasible rules

---

### 2. Fifth Generation Computer Systems (Japan - MITI)

**Agency**: MITI (Ministry of International Trade and Industry), ICOT  
**Timeline**: 1982-1993  
**Scale**: 
- Kappa parallel DBMS
- Quixote constraint logic programming
- Application-specific KBs

**Content**: Logic programming, parallel inference  
**Format**: Prolog, KL1 parallel logic  
**Status**: ⚠️ Mostly unavailable publicly (research archives)  
**Extraction potential**: Unknown (need to locate artifacts)

---

### 3. Alvey Programme (UK Government)

**Agency**: UK Department of Trade and Industry  
**Timeline**: 1983-1990  
**Budget**: £200 million  
**Scale**: Multiple IKBS demonstrator projects

**Content**: Expert systems, knowledge-based systems  
**Format**: Various (Prolog-based)  
**Status**: ⚠️ Artifacts scattered, limited public access  
**Extraction potential**: Unknown

---

### 4. ESPRIT (European Union)

**Agency**: European Commission  
**Timeline**: 1983-1993 (Phase I-II)  
**Scale**: Multiple knowledge engineering projects (KADS, NOMOS, etc.)

**Content**: Domain ontologies, problem-solving models  
**Format**: Various standards  
**Status**: ⚠️ Some standards available, full KBs unclear  
**Extraction potential**: 10K-50K rules (if accessible)

---

## US Government Programs

### 5. UMLS - Unified Medical Language System (NIH/NLM)

**Agency**: National Institutes of Health, National Library of Medicine  
**Timeline**: 1986-present  
**Scale** (2025 release):
- 3.45 million medical concepts
- 17.1 million unique concept names
- 190 source vocabularies
- Semantic network: 127 semantic types, 54 relations

**Content**: Medical terminology, diseases, treatments, anatomy  
**Format**: RRF (Rich Release Format), RDF  
**Status**: ✅ Freely available (license required)  
**Extraction potential**: 500K-2M defeasible rules

---

### 6. MeSH - Medical Subject Headings (NIH/NLM)

**Agency**: National Library of Medicine  
**Timeline**: 1960s-present (2026 release available)  
**Scale**:
- ~30,000 descriptors (hierarchical)
- ~89 qualifiers
- 280,000+ entry terms
- 15+ hierarchical categories

**Content**: Medical subjects, diseases, procedures, chemicals  
**Format**: XML, RDF, MARC  
**Status**: ✅ Freely available  
**Extraction potential**: 50K-150K defeasible rules

---

### 7. Gene Ontology (NIH + NSF)

**Agency**: National Human Genome Research Institute (NIH), NSF  
**Timeline**: 1998-present  
**Scale** (2026):
- 180,000+ research papers
- 1 million+ experimental annotations
- 1,500+ GO-CAM causal activity models
- 50,000+ GO terms

**Content**: Molecular functions, biological processes, cellular components  
**Format**: OBO, RDF  
**Status**: ✅ Freely available  
**Extraction potential**: 100K-300K defeasible rules

---

### 8. WordNet (NSF)

**Agency**: National Science Foundation  
**Timeline**: 1985-present (Princeton)  
**Scale**:
- 117,000 synsets
- 161,705 words
- 207,000+ semantic relations

**Content**: English lexicon, semantic network  
**Format**: Database, RDF  
**Status**: ✅ Freely available (we already use: 334 rules)  
**Current use**: 334 rules  
**Full extraction potential**: 50K-100K rules

---

### 9. NELL - Never Ending Language Learning (DARPA + NSF)

**Agency**: DARPA, NSF, Google (Carnegie Mellon)  
**Timeline**: 2010-2019  
**Scale**:
- 120 million confidence-weighted beliefs
- Thousands of interrelated functions
- Web-scale extraction

**Content**: General knowledge from web  
**Format**: Database dumps  
**Status**: ✅ Available on Hugging Face  
**Quality**: ~3% high confidence (2023)  
**Extraction potential**: 1M-5M rules (quality filtering needed)

---

## European Government Programs

### 10. YAGO (French Government - Télécom Paris)

**Agency**: Télécom Paris (French government institution)  
**Timeline**: 2007-present  
**Scale** (YAGO 4.5):
- 49 million entities
- 109 million facts
- French Open Research Award 2023

**Content**: General knowledge, Wikidata + schema.org  
**Format**: TTL, TSV  
**Status**: ✅ Freely available (we already use: 584 rules)  
**Current use**: 584 biology rules  
**Full extraction potential**: 1M-5M defeasible rules

---

### 11. DBpedia (German/EU)

**Agency**: University of Leipzig, FU Berlin (German government universities)  
**Timeline**: 2007-present  
**Scale**:
- 1 billion triples (English Wikipedia)
- 21 billion triples total (all languages monthly)
- 400+ classes, 2,000+ properties

**Content**: Structured Wikipedia data, all domains  
**Format**: RDF, N-Triples  
**Status**: ✅ Freely available  
**Extraction potential**: 2M-10M defeasible rules

---

### 12. BabelNet (EU - European Research Council)

**Agency**: European Research Council  
**Timeline**: 2010-present (Sapienza University Rome)  
**Scale** (v5.3, 2023):
- 13.8 million Babel synsets
- 119 million Babel senses
- 380 million semantic relations
- 272 languages

**Content**: Multilingual lexical-semantic network  
**Format**: API, dumps  
**Status**: ✅ Available (license for full dump)  
**Extraction potential**: 500K-2M defeasible rules

---

## Domain-Specific Government Programs

### 13. SUMO - Suggested Upper Merged Ontology (US Military)

**Agency**: Department of Defense (initial), IEEE standard  
**Developer**: Teknowledge, Articulate Software  
**Scale**:
- 20,000 terms
- 60,000 axioms
- 288,000 nodes, 496,000 edges total

**Content**: Upper ontology, military, government  
**Format**: SUO-KIF (higher-order logic)  
**Status**: ✅ Open source  
**Extraction potential**: 30K-80K defeasible rules

---

### 14. MatOnto (US Materials Genome Initiative)

**Agency**: Materials Genome Initiative (US government program)  
**Timeline**: 2011-present  
**Scale**:
- 1,190 structure-property relationships
- Materials science domain

**Content**: Materials, properties, synthesis  
**Format**: OWL  
**Status**: ✅ Available (we already use: 1,190 rules)  
**Current use**: 1,190 rules  
**Full extraction potential**: 50K-200K rules (if expanded)

---

### 15. LKIF Core (EU - ESTRELLA Project)

**Agency**: EU Framework Programme  
**Developer**: University of Amsterdam  
**Scale**:
- 201 legal inference rules
- 7 depth levels

**Content**: Legal norms, actions, roles  
**Format**: OWL  
**Status**: ✅ Freely available (we already use: 201 rules)  
**Current use**: 201 rules  
**Expansion potential**: Limited (complete extraction)

---

## Archived/Historical (Still Usable)

### 16. Freebase (Google, archived 2016)

**Original funding**: Metaweb, later Google  
**Scale** (final dump):
- 1.9 billion triples
- 72.4 million nodes
- 306.7 million edges
- 4,335 edge types

**Content**: General knowledge, all domains  
**Format**: RDF dumps (archived)  
**Status**: ✅ Historical dumps available  
**Extraction potential**: 5M-20M defeasible rules

---

## ConceptNet (Hybrid: Academic + Crowd)

### 17. ConceptNet 5.8 (MIT + crowd)

**Original funding**: MIT Media Lab, various NSF grants  
**Scale**:
- 34 million edges
- ~3M CapableOf relations
- ~300K NotCapableOf (defeaters!)
- 10+ languages

**Content**: Common sense, behavioral knowledge  
**Format**: CSV, JSON, API  
**Status**: ✅ Freely available  
**Extraction potential**: 1M-3M defeasible rules

---

## TOTAL INVENTORY SUMMARY

**15+ Government-Sponsored Knowledge Bases Available**:

| Source | Agency | Scale | Status | Rules Potential |
|--------|--------|-------|--------|-----------------|
| Cyc/OpenCyc | DARPA | 25M assertions | ✅ Partial | 100K-300K |
| YAGO 4.5 | France (Télécom) | 109M facts | ✅ Full | 1M-5M |
| DBpedia | Germany/EU | 1B-21B triples | ✅ Full | 2M-10M |
| WordNet | NSF | 117K synsets | ✅ Full (using) | 50K-100K |
| ConceptNet | MIT/NSF | 34M edges | ✅ Full | 1M-3M |
| UMLS | NIH | 3.45M concepts | ✅ License | 500K-2M |
| Gene Ontology | NIH/NSF | 1M annotations | ✅ Full | 100K-300K |
| MeSH | NIH | 30K descriptors | ✅ Full | 50K-150K |
| BabelNet | EU (ERC) | 13.8M synsets | ✅ License | 500K-2M |
| SUMO | DOD | 60K axioms | ✅ Full | 30K-80K |
| MatOnto | US MGI | 1.2K rules | ✅ Full (using) | 50K-200K |
| LKIF Core | EU | 201 rules | ✅ Full (using) | (complete) |
| Freebase | Google | 1.9B triples | ✅ Archive | 5M-20M |
| NELL | DARPA/NSF | 120M beliefs | ✅ Full | 1M-5M |
| FGCS | Japan MITI | Unknown | ⚠️ Limited | Unknown |
| Alvey | UK DTI | Unknown | ⚠️ Limited | Unknown |
| ESPRIT | EU | Unknown | ⚠️ Limited | 10K-50K |

**TOTAL POTENTIAL**: 12-54 million defeasible rules (if we extract from ALL sources)

---

## Projected Scenario Generation (ALL SOURCES)

### If We Use ALL Available Government KBs

**Conservative estimate** (careful filtering, quality > 85%):
- **Rules**: 5-10 million
- **Level 1**: 1-2 million scenarios
- **Level 2**: 800K-1.6M scenarios
- **Level 3**: 80K-200K scenarios
- **TOTAL: 1.88-3.8 MILLION scenarios**

**Aggressive estimate** (all sources, quality > 70%):
- **Rules**: 12-54 million
- **Level 1**: 2.5-10 million scenarios
- **Level 2**: 2-9 million scenarios
- **Level 3**: 200K-900K scenarios
- **TOTAL: 4.7-19.9 MILLION scenarios**

---

## Recommended Phased Approach

### Phase 1: Core 3 Domains from Primary Sources (NeurIPS)

**Sources**: YAGO, WordNet, LKIF, MatOnto, ConceptNet, OpenCyc  
**Domains**: Biology, Legal, Materials  
**Rules**: 115K-280K  
**Scenarios**: **50K-100K**  
**Timeline**: Weeks 8-14 (as planned)

### Phase 2: Medical Domain (Follow-up Paper #1)

**Sources**: UMLS, Gene Ontology, MeSH, YAGO medical, DBpedia  
**Rules**: 650K-2.5M  
**Scenarios**: **100K-400K**  
**Timeline**: 2-6 months post-NeurIPS

### Phase 3: Multilingual Expansion (Follow-up Paper #2)

**Sources**: BabelNet, DBpedia (all languages), multilingual ConceptNet  
**Rules**: 2M-8M  
**Scenarios**: **300K-1.3M**  
**Timeline**: 6-12 months post-NeurIPS

### Phase 4: Web-Scale Knowledge (Follow-up Paper #3)

**Sources**: NELL, Freebase, full YAGO, full DBpedia  
**Rules**: 5M-20M  
**Scenarios**: **800K-3.2M**  
**Timeline**: 1-2 years post-NeurIPS

### Phase 5: Everything (Comprehensive Benchmark)

**Sources**: All 15+ government KBs combined  
**Rules**: 12M-54M  
**Scenarios**: **1.9M-19.9M** (conservative: 1.9M, aggressive: 19.9M)  
**Timeline**: Multi-year effort

---

## Domain Coverage with ALL Sources

### Enhanced Biology (YAGO + Gene Ontology + UMLS bio + DBpedia)

**Sources**: 4 major KBs  
**Rules**: 1M-3M  
**Scenarios**: **160K-480K**

**Sub-domains**:
- Genetics & molecular biology: 40K-120K
- Disease biology: 30K-90K
- Ecology & evolution: 25K-75K
- Anatomy & physiology: 25K-75K
- Zoology: 20K-60K
- Botany: 15K-45K
- Microbiology: 5K-15K

---

### Medical & Health (UMLS + MeSH + Gene Ontology)

**Sources**: 3 NIH KBs  
**Rules**: 650K-2.5M  
**Scenarios**: **100K-400K**

**Sub-domains**:
- Diseases (UMLS): 30K-120K
- Treatments & drugs (UMLS, MeSH): 25K-100K
- Anatomy (UMLS, MeSH): 15K-60K
- Medical procedures: 15K-60K
- Genetics (GO): 10K-40K
- Pharmacology: 5K-20K

---

### Multilingual Common Sense (BabelNet + ConceptNet)

**Sources**: 2 multilingual KBs  
**Rules**: 2M-5M  
**Scenarios**: **320K-800K**

**Languages**: 272 (BabelNet) + 10 major (ConceptNet)  
**Domains**: All everyday knowledge

---

### Web-Scale Knowledge (YAGO + DBpedia + Freebase + NELL)

**Sources**: 4 web-scale KBs  
**Rules**: 5M-15M  
**Scenarios**: **800K-2.4M**

**Coverage**: Encyclopedic, all domains

---

## Conservative Realistic Plan

### What We Can Actually Do (Given Time/Resources)

**For NeurIPS (Week 14)**:
- Sources: 6 (YAGO, WordNet, OpenCyc, ConceptNet, LKIF, MatOnto)
- Domains: 3 (Biology, Legal, Materials)
- Rules: 115K-280K
- **Scenarios: 50K-100K**

**For Follow-Up (6 months)**:
- Add: UMLS, MeSH, Gene Ontology (medical)
- Add: DBpedia subset
- Rules: 800K-3M total
- **Scenarios: 130K-480K**

**For Comprehensive (1-2 years)**:
- Add: BabelNet, NELL, Freebase, full DBpedia, full YAGO
- Rules: 5M-20M
- **Scenarios: 800K-3.2M**

---

## The Wide Net: Everything Combined

**Maximum theoretical capacity** using ALL government KBs:

**Sources**: 15+ government-sponsored programs  
**Rules**: 12-54 million  
**Scenarios**:
- Level 1: 2.5-10 million
- Level 2: 2-9 million
- Level 3: 200K-900K
- **TOTAL: 4.7-19.9 MILLION scenarios**

**Domains**: 50+ (every domain covered by human knowledge)

**This would be**: The largest defeasible reasoning benchmark ever created

---

## Prioritization by Impact

### Tier 1: Immediate (Weeks 8-14)

**Must have**:
- YAGO, WordNet (already have)
- OpenCyc + ConceptNet (cross-ontology)
- LKIF, MatOnto (already have)

**Result**: 50K-100K scenarios, 3 domains, publishable at NeurIPS

---

### Tier 2: High Value (Post-NeurIPS)

**Add**:
- UMLS (3.45M concepts - medical powerhouse)
- Gene Ontology (genetics/molecular)
- DBpedia (Wikipedia structured data)

**Result**: 130K-480K scenarios, medical domain added

---

### Tier 3: Expansion (6-12 months)

**Add**:
- BabelNet (multilingual)
- MeSH (medical hierarchy)
- SUMO (upper ontology, military)

**Result**: 300K-1M scenarios, multilingual + specialized domains

---

### Tier 4: Web-Scale (1-2 years)

**Add**:
- NELL (web-learned, quality filtered)
- Freebase (archived but huge)
- Full YAGO, full DBpedia

**Result**: 800K-3.2M scenarios, web-scale coverage

---

### Tier 5: Everything (Multi-year)

**Add**: All sources including FGCS/Alvey artifacts if found  
**Result**: 1.9M-19.9M scenarios, comprehensive

---

## Accessibility Summary

**Immediately Available** (✅ No barriers):
- OpenCyc, YAGO, WordNet, ConceptNet, DBpedia, Gene Ontology, MeSH, SUMO, MatOnto, LKIF

**License Required** (✅ Free for research):
- UMLS, BabelNet (full dumps)

**Archived but Available** (✅ Static):
- Freebase, NELL (2019 snapshot)

**Limited Availability** (⚠️ Need to locate):
- FGCS artifacts, Alvey demonstrators, ESPRIT projects

**Not Available** (❌):
- ResearchCyc (commercial license)

**Status**: 12 of 17 sources immediately or easily accessible

---

## Answer to "Cast a Wide Net"

**Widest possible net** (all government KBs):
- **15+ programs** from USA, Japan, UK, EU, France, Germany
- **12-54 million rules** combined
- **1.9-19.9 MILLION scenarios** across all three levels

**Realistic wide net** (accessible sources, 1-2 years):
- **10 programs** (high-quality, available)
- **5-20 million rules**
- **800K-3.2M scenarios**

**Conservative wide net** (6 months post-NeurIPS):
- **8 programs** (core + medical)
- **800K-3M rules**
- **130K-480K scenarios**

**For NeurIPS (Weeks 8-14)**:
- **6 programs** (core sources)
- **115K-280K rules**
- **50K-100K scenarios**

**Current**: 374 scenarios from 4 sources

**Multiplier (widest net)**: **5,080x to 53,200x** (!)

---

**Author**: Patrick Cooper  
**Date**: 2026-02-13  
**Purpose**: Complete inventory of government KB programs for maximum scale
