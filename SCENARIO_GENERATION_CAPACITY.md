# Scenario Generation Capacity: Full Domain Coverage

**Assuming Cross-Ontology Implementation Succeeds**

Using OpenCyc (239K terms, 2M triples) + ConceptNet (34M edges)

---

## Available Domains from Large-Scale KBs

### OpenCyc 4.0 Coverage (239,000 terms)

**Major categories** (from upper ontology structure):

1. **Biology & Life Sciences** (~50,000 concepts)
   - Organisms, taxonomy, anatomy, physiology
   - Behavioral properties, ecological relationships
   - Genetics, molecular biology, evolution

2. **Chemistry & Materials** (~30,000 concepts)
   - Chemical elements, compounds, reactions
   - Materials, alloys, properties
   - Phase behavior, synthesis

3. **Geography & Geopolitics** (~20,000 concepts)
   - Countries, regions, cities
   - Geographic features, climate
   - Political entities, boundaries

4. **Human Activities** (~40,000 concepts)
   - Professions, roles, organizations
   - Events, processes, activities
   - Social structures

5. **Artifacts & Technology** (~25,000 concepts)
   - Tools, machines, devices
   - Buildings, infrastructure
   - Transportation, communication

6. **Abstract Concepts** (~30,000 concepts)
   - Mathematics, logic
   - Time, space, measurement
   - Qualities, attributes

7. **Legal & Governance** (~10,000 concepts)
   - Laws, regulations, statutes
   - Legal entities, jurisdictions
   - Governmental structures

8. **Medicine & Health** (~15,000 concepts)
   - Diseases, symptoms, treatments
   - Medical procedures, drugs
   - Healthcare systems

9. **Food & Nutrition** (~5,000 concepts)
   - Foods, ingredients, dishes
   - Nutritional properties

10. **Arts & Culture** (~10,000 concepts)
    - Music, literature, visual arts
    - Cultural practices, traditions

**Remaining**: ~14,000 (miscellaneous, meta-knowledge)

### ConceptNet 5.8 Coverage (34M edges)

**Relation types** (behavioral properties):
- CapableOf: ~3M edges (behavioral capabilities)
- NotCapableOf: ~300K edges (exceptions/defeaters!)
- HasProperty: ~2M edges
- UsedFor: ~1.5M edges
- AtLocation: ~2M edges
- IsA: ~8M edges (taxonomy)
- Causes: ~500K edges
- HasA: ~1M edges

**Domain distribution** (estimated):
- General/everyday: 60% (~20M edges)
- Science/technical: 20% (~7M edges)
- Abstract/conceptual: 15% (~5M edges)
- Domain-specific: 5% (~2M edges)

---

## Projected Scenario Generation by Domain

### Conservative Estimates

**Method**: Cross-ontology extraction
- Extract concepts from OpenCyc (taxonomy)
- Match with ConceptNet properties
- Generate defeasible rules
- Instance yield: ~0.16 instances per rule (current ratio)

### 1. Biology & Life Sciences

**Scale**:
- OpenCyc concepts: 50,000
- ConceptNet bio edges: ~500,000 (filtered from 34M)
- Average properties per concept: ~10
- Generated rules: **100,000-200,000**

**Scenarios**:
- Level 2 (rule abduction): ~16,000-32,000
- Level 3 (defeater from NotCapableOf): ~2,000-5,000
- **Total: 18,000-37,000 scenarios**

**Sub-domains**:
- Zoology (vertebrates, invertebrates): 8,000-15,000
- Botany (plants, fungi): 3,000-6,000
- Microbiology: 2,000-4,000
- Ecology: 2,000-4,000
- Genetics/molecular: 3,000-8,000

---

### 2. Chemistry & Materials Science

**Scale**:
- OpenCyc concepts: 30,000
- ConceptNet chem edges: ~100,000
- Generated rules: **30,000-80,000**

**Scenarios**:
- Level 2: ~5,000-13,000
- Level 3: ~500-1,500
- **Total: 5,500-14,500 scenarios**

**Sub-domains**:
- Inorganic chemistry: 2,000-5,000
- Organic chemistry: 1,500-4,000
- Materials science: 1,500-4,000
- Physical chemistry: 500-1,500

---

### 3. Medicine & Health

**Scale**:
- OpenCyc concepts: 15,000
- ConceptNet medical edges: ~200,000
- Generated rules: **40,000-80,000**

**Scenarios**:
- Level 2: ~6,000-13,000
- Level 3: ~800-2,000
- **Total: 6,800-15,000 scenarios**

**Sub-domains**:
- Diseases & symptoms: 2,500-5,000
- Treatments & procedures: 2,000-4,000
- Anatomy & physiology: 1,500-3,000
- Pharmacology: 800-3,000

---

### 4. Geography & Geopolitics

**Scale**:
- OpenCyc concepts: 20,000
- ConceptNet geo edges: ~150,000
- Generated rules: **25,000-60,000**

**Scenarios**:
- Level 2: ~4,000-10,000
- Level 3: ~400-1,000
- **Total: 4,400-11,000 scenarios**

**Sub-domains**:
- Physical geography: 1,500-4,000
- Political geography: 1,500-3,000
- Urban geography: 800-2,000
- Cultural geography: 600-2,000

---

### 5. Legal & Governance

**Scale**:
- OpenCyc concepts: 10,000
- LKIF Core: 201 rules (current)
- ConceptNet legal edges: ~50,000
- Generated rules: **15,000-40,000**

**Scenarios**:
- Level 2: ~2,400-6,400
- Level 3: ~300-800
- **Total: 2,700-7,200 scenarios**

**Sub-domains**:
- Constitutional law: 800-2,000
- Contract law: 600-1,500
- Criminal law: 500-1,500
- Administrative law: 400-1,200
- International law: 400-1,000

---

### 6. Technology & Engineering

**Scale**:
- OpenCyc concepts: 25,000
- ConceptNet tech edges: ~200,000
- Generated rules: **35,000-75,000**

**Scenarios**:
- Level 2: ~5,600-12,000
- Level 3: ~600-1,500
- **Total: 6,200-13,500 scenarios**

**Sub-domains**:
- Computer science: 2,000-4,000
- Electrical engineering: 1,500-3,000
- Mechanical engineering: 1,500-3,000
- Civil engineering: 800-2,000
- Software engineering: 400-1,500

---

### 7. Social Sciences

**Scale**:
- OpenCyc concepts: 15,000
- ConceptNet social edges: ~250,000
- Generated rules: **30,000-70,000**

**Scenarios**:
- Level 2: ~4,800-11,200
- Level 3: ~500-1,400
- **Total: 5,300-12,600 scenarios**

**Sub-domains**:
- Psychology: 1,500-3,500
- Economics: 1,200-3,000
- Sociology: 1,200-2,500
- Anthropology: 800-2,000
- Political science: 600-1,600

---

### 8. Food & Nutrition

**Scale**:
- OpenCyc concepts: 5,000
- ConceptNet food edges: ~100,000
- Generated rules: **15,000-35,000**

**Scenarios**:
- Level 2: ~2,400-5,600
- Level 3: ~250-700
- **Total: 2,650-6,300 scenarios**

---

### 9. Everyday Objects & Activities

**Scale**:
- OpenCyc concepts: 20,000
- ConceptNet everyday edges: ~500,000 (largest!)
- Generated rules: **50,000-120,000**

**Scenarios**:
- Level 2: ~8,000-19,200
- Level 3: ~1,000-2,400
- **Total: 9,000-21,600 scenarios**

**Sub-domains**:
- Household items: 3,000-7,000
- Clothing & fashion: 1,500-3,500
- Sports & recreation: 2,000-5,000
- Transportation: 1,500-3,500
- Tools & equipment: 1,000-2,600

---

### 10. Arts & Entertainment

**Scale**:
- OpenCyc concepts: 10,000
- ConceptNet arts edges: ~80,000
- Generated rules: **12,000-30,000**

**Scenarios**:
- Level 2: ~1,900-4,800
- Level 3: ~200-600
- **Total: 2,100-5,400 scenarios**

---

## TOTAL CAPACITY ESTIMATES

### By Domain (Top 10)

| Domain | Rules | Level 2 | Level 3 | Total Scenarios |
|--------|-------|---------|---------|-----------------|
| Biology | 100K-200K | 16K-32K | 2K-5K | **18K-37K** |
| Everyday | 50K-120K | 8K-19K | 1K-2.4K | **9K-21K** |
| Chemistry | 30K-80K | 5K-13K | 0.5K-1.5K | **5.5K-14.5K** |
| Technology | 35K-75K | 5.6K-12K | 0.6K-1.5K | **6.2K-13.5K** |
| Medicine | 40K-80K | 6.4K-13K | 0.8K-2K | **6.8K-15K** |
| Social Sci | 30K-70K | 4.8K-11K | 0.5K-1.4K | **5.3K-12.6K** |
| Geography | 25K-60K | 4K-10K | 0.4K-1K | **4.4K-11K** |
| Legal | 15K-40K | 2.4K-6.4K | 0.3K-0.8K | **2.7K-7.2K** |
| Food | 15K-35K | 2.4K-5.6K | 0.25K-0.7K | **2.65K-6.3K** |
| Arts | 12K-30K | 1.9K-4.8K | 0.2K-0.6K | **2.1K-5.4K** |

**GRAND TOTAL: 62,650-143,500 scenarios**

### Aggregate Statistics

**Rules Generated**: 352,000-850,000 (total across all domains)

**Scenarios**:
- Level 2 (rule abduction): 57,500-126,800
- Level 3 (defeater abduction): 5,150-16,700
- **Total: 62,650-143,500**

**Multiplier vs Current**:
- Current: 374 scenarios
- Conservative: 62,650 scenarios = **167x**
- Optimistic: 143,500 scenarios = **383x**

---

## Realistic Production Targets

### For NeurIPS Submission (Week 14)

**Focus on 3 core domains** (as planned):
- Biology: 18,000-37,000
- Legal: 2,700-7,200
- Materials: 5,500-14,500
- **Total: 26,200-58,700 scenarios**

**For paper**: "We generate 26,000-59,000 evaluation instances across three expert domains"

### For Follow-Up Work

**Add 2-3 additional domains**:
- Medicine: 6,800-15,000
- Everyday objects: 9,000-21,600
- Geography: 4,400-11,000
- **Additional: 20,200-47,600 scenarios**

**Total benchmark**: 46,400-106,300 scenarios

---

## By Defeasibility Type

### Defeasible Defaults (from CapableOf)

**Source**: ConceptNet CapableOf (~3M edges)  
**After domain filtering**: ~500K biology/chemistry/materials  
**Generated rules**: ~200K-400K defeasible defaults

**Examples**:
- flies(X) :- bird(X)
- swims(X) :- fish(X)
- conductive(X) :- metal(X)
- can_sign_contract(X) :- adult(X)

### Defeaters (from NotCapableOf)

**Source**: ConceptNet NotCapableOf (~300K edges)  
**After domain filtering**: ~30K-50K defeaters  
**Level 3 scenarios**: **5,000-17,000** (automatic!)

**Examples**:
- ~flies(X) :- penguin(X)
- ~walks(X) :- whale(X)
- ~brittle(X) :- metallic_glass(X)
- can_sign_contract(X) :- emancipated_minor(X) [exception with superiority]

### Property Rules (from HasProperty)

**Source**: ConceptNet HasProperty (~2M edges)  
**Generated rules**: ~100K-300K property rules

**Examples**:
- has_feathers(X) :- bird(X)
- has_gills(X) :- fish(X)
- has_valence_electrons(X) :- metal(X)

---

## Quality Tiers

### Tier 1: High Confidence (Core Domains)

**Domains**: Biology, Chemistry, Materials (current focus)  
**Filtering**: ConceptNet weight > 5.0, OpenCyc core taxonomy  
**Expected quality**: 90-95% accuracy  
**Scenarios**: ~20,000-30,000  
**Use**: Primary benchmark, paper results

### Tier 2: Medium Confidence

**Domains**: Medicine, Technology, Legal, Geography  
**Filtering**: ConceptNet weight > 3.0  
**Expected quality**: 85-90% accuracy  
**Scenarios**: ~25,000-50,000  
**Use**: Extended benchmark, robustness testing

### Tier 3: Exploratory

**Domains**: Social sciences, Arts, Everyday objects, Food  
**Filtering**: ConceptNet weight > 2.0  
**Expected quality**: 75-85% accuracy  
**Scenarios**: ~15,000-60,000  
**Use**: Future work, domain expansion

---

## Specific Domain Breakdowns

### Biology (Most Developed)

**Vertebrates**:
- Mammals: 5,000-10,000 scenarios
- Birds: 3,000-6,000 scenarios
- Fish: 2,000-4,000 scenarios
- Reptiles: 1,500-3,000 scenarios
- Amphibians: 1,000-2,000 scenarios

**Invertebrates**:
- Insects: 2,000-4,000 scenarios
- Arthropods (other): 800-2,000 scenarios
- Mollusks: 500-1,200 scenarios

**Plants**:
- Flowering plants: 1,500-3,000 scenarios
- Trees: 800-1,800 scenarios
- Other: 400-1,000 scenarios

**Microorganisms**:
- Bacteria: 500-1,500 scenarios
- Viruses: 300-800 scenarios

**Total Biology**: 18,000-37,000

### Chemistry & Materials

**Inorganic**:
- Metals: 1,000-2,500 scenarios
- Non-metals: 600-1,500 scenarios
- Compounds: 800-2,000 scenarios

**Organic**:
- Hydrocarbons: 500-1,200 scenarios
- Functional groups: 600-1,500 scenarios
- Polymers: 400-1,000 scenarios

**Materials**:
- Alloys: 600-1,500 scenarios
- Ceramics: 400-1,000 scenarios
- Composites: 300-800 scenarios
- Semiconductors: 300-700 scenarios

**Total Chemistry/Materials**: 5,500-14,500

### Medicine & Health

**Diseases**:
- Infectious: 1,200-3,000 scenarios
- Chronic: 1,000-2,500 scenarios
- Genetic: 500-1,500 scenarios

**Treatments**:
- Pharmaceuticals: 1,200-2,500 scenarios
- Procedures: 800-2,000 scenarios
- Therapies: 500-1,500 scenarios

**Anatomy**:
- Organ systems: 1,000-2,500 scenarios
- Tissues: 600-1,500 scenarios

**Total Medicine**: 6,800-15,000

### Legal & Governance

**Statutory Law**:
- Federal statutes: 600-1,500 scenarios
- State law: 500-1,200 scenarios
- International law: 400-1,000 scenarios

**Case Law**:
- Precedents: 400-1,200 scenarios
- Doctrines: 300-800 scenarios

**Legal Entities**:
- Contracts: 300-800 scenarios
- Corporations: 200-700 scenarios

**Total Legal**: 2,700-7,200

---

## Novelty Distribution (Level 3 Only)

### By Novelty Level (Nov score)

**Nov = 0** (No novel predicates):
- Uses existing predicates only
- ~60-70% of Level 3 instances
- Examples: ~flies(X) :- penguin(X)
- **Count**: 3,000-11,000

**Nov = 0.25-0.5** (Some novel predicates):
- Introduces 1-2 new predicates
- ~25-30% of Level 3 instances
- Examples: ~brittle(X) :- amorphous_metal(X)
- **Count**: 1,300-5,000

**Nov = 0.5-1.0** (High novelty):
- Introduces multiple new predicates
- ~5-10% of Level 3 instances
- Examples: requires specialized concepts
- **Count**: 250-1,700

**Total Level 3**: 5,150-16,700 with novelty distribution

---

## Instance Distribution by Difficulty

### By Theory Size

**Small theories** (10-50 rules):
- ~30% of instances
- Easier for models
- **Count**: 19,000-43,000

**Medium theories** (50-200 rules):
- ~50% of instances
- Moderate difficulty
- **Count**: 31,000-72,000

**Large theories** (200+ rules):
- ~20% of instances
- Challenging
- **Count**: 12,500-28,700

### By Support Set Size

**Single support** (1 critical element):
- ~40% of instances
- **Count**: 25,000-57,400

**Multiple support** (2-5 critical elements):
- ~45% of instances
- **Count**: 28,000-64,500

**Complex support** (6+ critical elements):
- ~15% of instances
- **Count**: 9,400-21,500

---

## Evaluation Load Estimates

### Full Benchmark Evaluation

**Assumptions**:
- 60,000 scenarios (middle estimate)
- 5 models (GPT-4o, Claude, Gemini, Llama 70B/8B)
- 4 modalities (M1-M4)
- 2 strategies (direct, CoT)

**Total queries**: 60,000 × 5 × 4 × 2 = **2,400,000 queries**

**Cost** (at current rates):
- GPT-4o: 480K queries × $0.02 = $9,600
- Claude 3.5: 480K queries × $0.015 = $7,200 (batch)
- Gemini: 480K queries × $0.01 = $4,800
- Llama: Free (local)
- **Total: ~$21,600**

**Time** (with rate limits):
- GPT-4o: 500 RPM → 16 hours
- Claude batch: 24-48 hours
- Gemini: 2 RPM → 166 hours (need upgrade!)
- **Total: 2-7 days parallelized**

### Subset Evaluation (Realistic for Paper)

**Core 3 domains**: 26,000 scenarios  
**Queries**: 26,000 × 5 × 4 × 2 = 1,040,000

**Cost**: ~$9,360  
**Time**: 1-3 days parallelized

### Development/Pilot Subset

**Representative sample**: 500 scenarios  
**Queries**: 500 × 5 × 4 × 2 = 20,000

**Cost**: ~$180  
**Time**: 2-4 hours

---

## Recommended Phased Rollout

### Phase 1: Core 3 Domains (NeurIPS Submission)

**Domains**: Biology, Chemistry/Materials, Legal  
**Scenarios**: 26,200-58,700  
**Cost**: $9,000-21,000  
**Timeline**: Weeks 9-14 (as planned)

**Deliverable**: Large-scale benchmark, all three objectives tested

### Phase 2: Medical + Technical (Follow-up Paper)

**Add**: Medicine (6.8K-15K), Technology (6.2K-13.5K)  
**Total new**: 13,000-28,500  
**Cost**: $4,700-10,200  
**Timeline**: Post-submission (2-4 weeks)

**Deliverable**: Expanded benchmark, medical/technical domains

### Phase 3: Comprehensive (Full Release)

**Add**: Geography, Social sciences, Food, Arts, Everyday  
**Total new**: 23,500-57,000  
**Cost**: $8,500-20,500  
**Timeline**: 6-12 months post-submission

**Deliverable**: Comprehensive benchmark covering all domains

---

## HPC Requirements by Scale

### For 26K Scenarios (Core 3 Domains)

**Instance generation**:
- CPU cores: 64
- RAM: 128 GB
- Time: 4-8 hours
- CURC Alpine: Well within capacity

### For 60K Scenarios (Extended)

**Instance generation**:
- CPU cores: 128 (2 nodes)
- RAM: 256 GB
- Time: 8-16 hours
- CURC Alpine: Feasible

### For 140K Scenarios (Full)

**Instance generation**:
- CPU cores: 256 (4 nodes)
- RAM: 512 GB
- Time: 12-24 hours
- CURC Alpine: Requires allocation planning

---

## Summary: What We Can Generate

### Conservative Estimate (Focus on Quality)

**Domains**: 3 (biology, chemistry/materials, legal)  
**Rules**: 115,000-280,000  
**Scenarios**: **26,200-58,700**  
**Quality**: High (90-95%)  
**Cost**: $9,000-21,000  
**Timeline**: Achievable in Weeks 9-14

### Aggressive Estimate (Full Coverage)

**Domains**: 10 (all major categories)  
**Rules**: 352,000-850,000  
**Scenarios**: **62,650-143,500**  
**Quality**: Variable (75-95% by domain)  
**Cost**: $22,500-51,500  
**Timeline**: 6-12 months

### Recommended for NeurIPS

**Target**: 30,000-40,000 scenarios across 3 core domains  
**Quality tier**: Tier 1 (high confidence)  
**Cost**: $10,800-14,400  
**Impact**: Large-scale, production-quality benchmark

---

## Comparison to Current

**Current**:
- Domains: 3
- Rules: 2,318
- Scenarios: 374
- Level 3: 0

**With Cross-Ontology (Conservative)**:
- Domains: 3 (can expand to 10)
- Rules: 115,000 (**50x**)
- Scenarios: 26,200 (**70x**)
- Level 3: 3,400 (**automatic!**)

**With Cross-Ontology (Aggressive)**:
- Domains: 10
- Rules: 850,000 (**367x**)
- Scenarios: 143,500 (**383x**)
- Level 3: 16,700 (**automatic!**)

---

## Bottom Line

**Question**: "What fields can we generate scenarios for?"

**Answer**: **10+ major domains** with 62K-143K total scenarios

**Top domains by scenario count**:
1. Biology: 18K-37K
2. Everyday objects: 9K-21K
3. Medicine: 6.8K-15K
4. Chemistry/Materials: 5.5K-14.5K
5. Technology: 6.2K-13.5K
6. Social sciences: 5.3K-12.6K
7. Geography: 4.4K-11K
8. Legal: 2.7K-7.2K
9. Food: 2.65K-6.3K
10. Arts: 2.1K-5.4K

**Recommended for NeurIPS**: Focus on 3 core domains = 26K-59K scenarios (70-157x current)

**This is a game-changer**: Transforms from small proof-of-concept (374) to comprehensive large-scale benchmark (26K-143K scenarios).

---

**Generated**: 2026-02-13  
**Assumes**: Cross-ontology extraction succeeds  
**Next**: Run proof-of-concept to validate these numbers
