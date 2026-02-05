# Phase 2 Implementation Plan: Backend Integration

## Date: February 5, 2026

## Objectives

1. Implement fully functional Prolog backend (PySwip)
2. Implement fully functional ASP backend (Clingo/Clorm)
3. Integrate substantive historical and modern knowledge bases
4. Create comprehensive Jupyter notebook demonstration

## Implementation Strategy

### Part 1: Prolog Backend (PySwip)

#### Prerequisites
- SWI-Prolog 8.4.2+ installed
- PySwip 0.3.3+ (already installed)
- Architecture match (64-bit Python + 64-bit SWI-Prolog)

#### Implementation Steps

**1.1 Query Translation Engine**
- Convert Query objects to Prolog syntax
- Handle variable bindings (X, Y, etc.)
- Support compound queries with multiple conditions
- Translate defeasible rules to Prolog representation

**1.2 Result Parsing**
- Parse Prolog query results into Result objects
- Extract variable bindings from solutions
- Handle multiple solutions (backtracking)
- Convert Prolog terms to Python objects

**1.3 Theory Loading**
- Load .pl files into Prolog session
- Assert Theory objects as Prolog facts/rules
- Handle imports and includes
- Manage Prolog session lifecycle

**1.4 Derivation Tracing**
- Implement proof tree extraction using SWI-Prolog debugging
- Use `trace/0`, `spy/1`, or `prolog_trace_interception/4`
- Build DerivationTree from trace output
- Track rule applications

**1.5 Minimal Support Computation**
- Implement backwards reasoning from goal
- Collect all facts/rules used in derivation
- Find minimal sufficient subset
- Handle multiple derivation paths

#### Testing Strategy
- Unit tests for query translation
- Integration tests with simple Prolog programs
- Tests with each knowledge base
- Performance benchmarks for large KBs

### Part 2: ASP Backend (Clingo/Clorm)

#### Prerequisites
- Clingo 5.8.0+ (already installed)
- Clorm 1.6.1+ (already installed)

#### Implementation Steps

**2.1 Predicate Definition**
- Define Clorm Predicate classes for common patterns
- Create Field specifications for different data types
- Support for function symbols and constants
- Handle complex terms

**2.2 Theory Translation**
- Convert Theory objects to ASP syntax
- Translate rules to ASP program format
- Handle constraints and optimization
- Support choice rules for abduction

**2.3 Query Execution**
- Use Clorm Control wrapper
- Execute ASP programs
- Parse answer sets into ResultSet
- Handle multiple stable models

**2.4 Abductive Reasoning**
- Implement generate-and-test for hypotheses
- Use ASP choice rules for hypothesis generation
- Add minimization criteria (#minimize statements)
- Extract minimal explanations

**2.5 Defeasible Reasoning**
- Encode defeasible logic in ASP
- Implement superiority relations
- Use weak constraints for preferences
- Compute extensions (skeptical/credulous)

#### Testing Strategy
- Test with classic ASP examples (graph coloring, Hamiltonian path)
- Abductive reasoning tests (diagnosis problems)
- Defeasible reasoning tests (Nixon diamond, Tweety)
- Performance tests with large programs

### Part 3: Knowledge Base Integration

#### Target Knowledge Bases

**Historical/Academic KBs**
1. **Cyc Knowledge Base** (Common Sense)
   - Source: Kaggle dataset (if available) or OpenCyc
   - Format: CycL → Convert to Prolog
   - Size: ~3M facts
   - Download to: D:\datasets\cyc\

2. **TaxKB** (Legal/Tax Domain)
   - Source: https://github.com/mcalejo/TaxKB
   - Format: Native Prolog
   - Features: LogicalEnglish, tax regulations
   - Download to: D:\datasets\taxkb\

3. **NephroDoctor** (Medical Domain)
   - Source: https://github.com/nicoladileo/NephroDoctor
   - Format: Native Prolog
   - Domain: Nephrology diagnosis
   - Download to: D:\datasets\nephrodoc\

**Create Custom KBs for Research**
4. **IDP Discovery KB** (From Paper)
   - Encode structure-function dogma
   - Add IDP examples (alpha-synuclein, etc.)
   - Demonstrate defeasible reasoning

5. **Scientific Discovery KB**
   - Prion diseases
   - Horizontal gene transfer
   - Epigenetic inheritance
   - Other examples from paper

6. **ProofWriter-style KB** (Benchmark)
   - Simple deductive rules
   - For testing and validation
   - Compare against published benchmarks

#### Integration Process

**Step 1: Download and Organize**
```
D:\datasets\
├── cyc\
│   ├── raw\          # Original CycL files
│   └── prolog\       # Converted to Prolog
├── taxkb\
│   └── regulations.pl
├── nephrodoc\
│   └── nephro_kb.pl
└── blanc_research\
    ├── idp_discovery.pl
    ├── scientific_revolutions.pl
    └── proofwriter_benchmark.pl
```

**Step 2: Create KB Registry**
```python
# src/blanc/knowledge_bases/registry.py
KnowledgeBaseRegistry with metadata:
- Name, domain, size
- File paths, format
- Citation information
- Difficulty level for benchmarking
```

**Step 3: Create Loaders**
```python
# src/blanc/knowledge_bases/loaders.py
- CycLoader: Convert CycL to Prolog
- GitHubLoader: Clone and prepare repos
- PrologLoader: Direct .pl file loading
- ASPLoader: Load .lp files
```

**Step 4: Create Benchmark Suite**
```python
# tests/benchmark/
- test_cyc_queries.py
- test_taxkb_reasoning.py
- test_nephro_diagnosis.py
- test_idp_discovery.py
```

### Part 4: Jupyter Notebook Demonstration

#### Notebook Structure

**Notebook: `notebooks/BLANC_Tutorial.ipynb`**

**Section 1: Introduction (10 minutes)**
- Project overview and motivation
- Abductive reasoning challenge for LLMs
- Defeasible logic as solution

**Section 2: Quick Start (5 minutes)**
- Install dependencies
- Import BLANC
- Create first theory
- Execute simple query

**Section 3: Theory Construction (15 minutes)**
- Rule types explained (strict, defeasible, defeater)
- Building theories programmatically
- Format conversion demo
- Real example: Tweety the penguin

**Section 4: Query Modes (20 minutes)**
- Deductive queries
  * Medical diagnosis example
  * Multiple solutions
- Abductive queries
  * Hypothesis generation
  * Minimal explanations
- Defeasible queries
  * Superiority relations
  * Conflict resolution

**Section 5: Prolog Backend (15 minutes)**
- Load knowledge base from file
- Execute queries against TaxKB
- Derivation tracing
- Minimal support computation

**Section 6: ASP Backend (15 minutes)**
- Define predicates with Clorm
- Solve with Clingo
- Multiple answer sets
- Optimization problems

**Section 7: Research Applications (20 minutes)**
- IDP Discovery scenario
- Generate incomplete theories
- Abductive dataset generation
- Evaluation metrics

**Section 8: Working with Historical KBs (15 minutes)**
- Load Cyc knowledge base
- Query common sense knowledge
- Compare reasoning modes
- Performance considerations

**Section 9: Advanced Topics (10 minutes)**
- Custom backend implementation
- Extending rule types
- Integration with LLMs
- Future directions

**Section 10: Exercises (Self-paced)**
- Exercise 1: Create medical diagnosis theory
- Exercise 2: Implement abductive reasoning task
- Exercise 3: Generate dataset from KB
- Exercise 4: Benchmark your own KB

#### Notebook Features
- Interactive widgets for query construction
- Visualization of derivation trees (NetworkX + Matplotlib)
- Performance profiling
- Download links for all datasets
- Export results to files

## Implementation Timeline

### Session 1: Core Backends (Current)
- [x] Plan creation
- [ ] Prolog backend implementation (1-2 hours)
- [ ] ASP backend implementation (1-2 hours)
- [ ] Unit tests for both backends
- [ ] Basic integration tests

### Session 2: Knowledge Base Integration
- [ ] Download knowledge bases to D:\datasets\
- [ ] Create KB registry and loaders
- [ ] Integration tests with each KB
- [ ] Benchmark suite creation

### Session 3: Notebook Development
- [ ] Create notebook structure
- [ ] Write all sections with examples
- [ ] Test all code cells
- [ ] Add visualizations
- [ ] Polish and document

## Technical Decisions

### Prolog Backend Architecture
```python
class PrologBackend(KnowledgeBaseBackend):
    def __init__(self):
        from pyswip import Prolog
        self.prolog = Prolog()
        self._loaded_files = []
        
    def _translate_query(self, query: Query) -> str:
        """Convert Query to Prolog syntax"""
        
    def _parse_solution(self, solution: dict) -> Result:
        """Convert Prolog solution to Result"""
        
    def _get_proof_tree(self, goal: str) -> DerivationTree:
        """Extract proof using trace/spy"""
```

### ASP Backend Architecture
```python
class ASPBackend(KnowledgeBaseBackend):
    def __init__(self):
        from clorm import Control, Predicate
        self.control = Control()
        self.predicates = {}
        
    def _theory_to_asp(self, theory: Theory) -> str:
        """Convert Theory to ASP program"""
        
    def _extract_models(self, solve_handle) -> ResultSet:
        """Parse answer sets to ResultSet"""
        
    def _generate_abductive_program(self, query: Query) -> str:
        """Create ASP program for abduction"""
```

### Error Handling Strategy
- Graceful degradation if SWI-Prolog not installed
- Clear error messages for missing dependencies
- Validation before query execution
- Timeout handling for long-running queries

### Performance Optimizations
- Lazy loading of knowledge bases
- Query result caching
- Prolog session reuse
- Incremental theory updates

## Success Criteria

### Functional Requirements
- [x] Plan complete and documented
- [ ] Prolog backend executes all query types
- [ ] ASP backend executes all query types
- [ ] At least 3 knowledge bases integrated
- [ ] Notebook runs end-to-end without errors
- [ ] All examples produce expected results

### Quality Requirements
- [ ] >80% test coverage for backends
- [ ] All knowledge bases documented with citations
- [ ] Notebook is self-contained and educational
- [ ] Performance acceptable (<1s for simple queries)

### Research Requirements
- [ ] Can generate abductive dataset from KB
- [ ] Minimal support computation works
- [ ] Derivation tracing produces valid trees
- [ ] Theory ablation tools functional

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SWI-Prolog installation issues | High | Provide detailed install guide, use Docker fallback |
| Cyc dataset unavailable | Medium | Use OpenCyc or create synthetic common sense KB |
| Performance issues with large KBs | Medium | Implement indexing, caching, query optimization |
| CycL conversion complexity | Medium | Start with subset, use existing converters |
| PySwip API changes | Low | Pin version, have fallback to subprocess calls |

## Resources

### Documentation Links
- PySwip: https://pyswip.readthedocs.io/
- Clorm: https://clorm.readthedocs.io/
- SWI-Prolog: https://www.swi-prolog.org/
- Clingo: https://potassco.org/clingo/

### Dataset Sources
- Cyc: https://www.kaggle.com/datasets/therohk/cyc-kb
- TaxKB: https://github.com/mcalejo/TaxKB
- NephroDoctor: https://github.com/nicoladileo/NephroDoctor

### Papers to Reference
- PySwip documentation
- Clorm ORM paper
- Nute's defeasible logic papers
- ProofWriter benchmark

## Next Steps

1. **Immediate**: Implement Prolog backend query translation
2. **Then**: Implement result parsing and theory loading
3. **Then**: Implement ASP backend with Clorm
4. **Then**: Download and integrate first KB (TaxKB - smallest)
5. **Finally**: Create comprehensive notebook

## File Structure After Phase 2

```
blanc/
├── src/blanc/
│   ├── backends/
│   │   ├── prolog.py (IMPLEMENTED)
│   │   ├── asp.py (IMPLEMENTED)
│   ├── knowledge_bases/
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── loaders.py
│   │   └── converters.py
├── notebooks/
│   └── BLANC_Tutorial.ipynb
├── tests/
│   ├── backends/
│   │   ├── test_prolog_backend.py
│   │   └── test_asp_backend.py
│   └── benchmark/
│       ├── test_taxkb.py
│       ├── test_nephro.py
│       └── test_cyc.py
└── D:\datasets\
    ├── cyc\
    ├── taxkb\
    ├── nephrodoc\
    └── blanc_research\
```

---

**Implementation begins now.**
