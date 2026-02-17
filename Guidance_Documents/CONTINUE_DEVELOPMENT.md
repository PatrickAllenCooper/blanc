# Continue Development: Handoff Document

**Date**: 2026-02-13 (UPDATED)  
**Current Status**: Week 8 Complete (Evaluation Infrastructure Done)  
**Critical Next**: Week 8.5 - Level 3 Instance Generation (3-5 days)  
**Why Critical**: Paper claims all 3 objectives, dataset only tests 1  
**For**: Future development sessions

**⚠️ IMPORTANT**: Read [OBJECTIVE_ACCOUNTING.md](../OBJECTIVE_ACCOUNTING.md) first to understand the gap

---

## Quick Status

**Progress**: 8 of 14.5 weeks complete (55%) ✅  
**Tests**: 343 passing, 0 failures ✅  
**Coverage**: 80% ✅  
**Blockers**: Level 3 instances needed (critical for paper claims) ⚠️

**Must do next**: Generate Level 3 (defeater abduction) instances  
**Then**: Run pilot evaluation → Week 9 full evaluation

**THE GAP**:
- Paper title: "Grounding, Novelty, and Belief Revision"
- Current dataset: Tests grounding only (0% novelty, 0% belief revision)
- Solution: Week 8.5 (3-5 days) to generate Level 3 instances
- See: [OBJECTIVE_ACCOUNTING.md](../OBJECTIVE_ACCOUNTING.md)

---

## What's Complete (Weeks 1-8)

### Week 8: LLM Evaluation Infrastructure ✅
- **5 model interfaces**: GPT-4o, Claude 3.5, Gemini 1.5, Llama 3 (70B/8B)
- **Prompting system**: Direct + CoT for all 4 modalities
- **Response caching**: Persistent storage with statistics
- **Evaluation pipeline**: End-to-end orchestration
- **Testing**: 50 new tests, 80% coverage
- **Files**: `experiments/*.py` (1,685 lines)

**Pilot ready**: `python experiments/run_pilot_evaluation.py` (needs API keys)

---

## What's Complete (Weeks 1-7)

### Expert KB Foundation ✅
- **2,318 expert-curated rules** from 4 peer-reviewed institutions
  - YAGO 4.5 (Télécom Paris): 584 rules
  - WordNet 3.0 (Princeton): 334 rules
  - LKIF Core (U Amsterdam): 201 rules
  - MatOnto (MatPortal): 1,190 rules
- **Policy**: Expert-only (see KNOWLEDGE_BASE_POLICY.md)
- **Files**: `examples/knowledge_bases/*.py`

### Development Dataset ✅
- **374 instances** from expert KB subsets
  - Biology: 114 instances
  - Legal: 168 instances
  - Materials: 92 instances
- **Files**: `instances/*.json`
- **Strategy**: Local dev with subsets, HPC for millions later

### Statistical Analysis ✅
- **Section 4.3** complete (4 of 5 subsections)
- Volume/balance, difficulty, yield, partition sensitivity
- **Files**: `experiments/*.py`, `results/*.json`, `figures/*.png`

### Complete Codec ✅
- **All 4 modalities**: M1 (narrative), M2 (semi-formal), M3 (annotated), M4 (formal)
- **All 3 decoders**: D1 (exact), D2 (template), D3 (semantic)
- **Cascading pipeline**: D1→D2→D3
- **Validation**: 75% (3 of 4 perfect: M4+D1, M3+D2, M2+D2 all 100%)
- **Files**: `src/blanc/codec/*.py`

### Quality Metrics ✅
- **Tests**: 310+ passing
- **Coverage**: 77-80% (87-99% on critical paths)
- **Architecture**: Clean, refactored, modular
- **No blockers**

---

## What Remains (Weeks 8-14)

### Week 8: LLM Evaluation Infrastructure (Next - 5-7 days)

**Tasks**:
1. Model interfaces (GPT-4o, Claude 3.5, Gemini 1.5 Pro, Llama 3 70B/8B)
2. API integration (OpenAI, Anthropic, Google)
3. Prompting infrastructure (direct + CoT)
4. Batch evaluation pipeline
5. Response caching

**Deliverables**:
- `experiments/model_interface.py`
- `experiments/prompting.py`
- `experiments/evaluation_pipeline.py`

**Estimate**: 20-30 hours

---

### Weeks 9-10: Core Evaluation + Analysis (2 weeks)

**Tasks**:
1. Run ~46,000 evaluations (5 models × 374 instances × 4 modalities × 2 prompts)
2. Collect and cache responses
3. Apply decoders, compute metrics
4. Error taxonomy (E1-E5)
5. Decomposed metrics

**Cost**: $450-700 (LLM API calls)

---

### Weeks 11-12: Advanced Analyses (2 weeks)

**Tasks**:
1. Scaling analysis (Llama 8B vs 70B)
2. Theory size scaling
3. Symbolic ceiling (ASP solver)
4. Partition sensitivity

---

### Weeks 13-14: HPC Production + Submission (2 weeks)

**Tasks**:
1. Deploy to CURC Alpine HPC
2. Generate 1M+ instances from full expert KBs
3. Final analyses on production scale
4. Paper integration
5. Submission

---

## How to Continue Development

### Setup and Verification (5 minutes)

```bash
# Navigate to repo
cd c:/Users/patri/code/blanc

# Check git status
git status
# Should be: "On branch main, up to date with origin/main"

# Pull latest (if needed)
git pull origin main

# Verify tests pass
python -m pytest tests/ --tb=no -q
# Expected: 310+ passed, 1 skipped

# Check coverage
python -m pytest tests/ --cov=src/blanc --cov-report=term | Select-String "TOTAL"
# Expected: 77-80%
```

**If all pass**: ✅ Ready to continue  
**If tests fail**: Check docs/completed_weeks/ for troubleshooting

---

## Key Files and Locations

### Current Status
- `STATUS.md` - Current development status
- `WEEK7_FINAL_STATUS.md` - Latest completed work
- `INFRASTRUCTURE_COMPLETE_FINAL.md` - Phase summary

### Technical References
- `IMPLEMENTATION_PLAN.md` - Complete technical specification
- `NEURIPS_FULL_ROADMAP.md` - 14-week plan
- `KNOWLEDGE_BASE_POLICY.md` - Expert-only policy (CRITICAL)

### Code
- `src/blanc/` - Production code (1,712 lines)
- `tests/` - Test suite (310+ tests)
- `examples/knowledge_bases/` - Expert KBs
- `experiments/` - Analysis and validation scripts

### Data
- `instances/` - 374 development instances
- `results/` - Statistical analysis results
- `figures/` - Publication figures

### Week Completion Reports
- `docs/completed_weeks/` - Weeks 3-7 completion docs

---

## Critical: Week 8.5 First (NEW - 3-5 days)

**Before Week 9 pilot, we MUST generate Level 3 instances**

### Why This is Essential

From paper.tex (line 192):
> "Level 3 (defeater abduction) asks models to construct novel exception rules satisfying the conservativity constraint, performing rational belief revision in the defeasible setting."

**Current state**:
- 374 instances (100% Level 2 - rule abduction)
- Tests: Grounding ✅
- Tests: Novelty ❌ (0% coverage)
- Tests: Belief Revision ❌ (0% coverage)

**Paper claims**: All three objectives  
**Dataset delivers**: One objective

**Solution**: Generate 35-50 Level 3 instances

### Week 8.5 Breakdown

**Day 1-2: Biology Defeaters** (15-20 instances)
```python
# Examples to create:
- Penguin: "~flies(X) :- penguin(X)"  # Classic exception
- Ostrich: "~flies(X) :- ostrich(X)"
- Whale: "~walks(X) :- whale(X)"
- Bat: "flies(X) :- bat(X)" + superiority over mammal rule
- Dolphin: "~walks(X) :- dolphin(X)"

# For each:
1. Define anomaly (what theory predicts but is false)
2. Create defeater rule
3. Validate conservativity (preserves other expectations)
4. Compute Nov(r, D) and d_rev
5. Generate 5 distractors
```

**Day 3: Legal Defeaters** (10-15 instances)
```python
# Examples:
- Emancipated minors: "can_sign_contract(X) :- emancipated_minor(X)"
- Jurisdictional exceptions
- Statute of limitations
- Good faith exceptions
- Qualified immunity

# Some with novel predicates → Nov > 0
```

**Day 4: Materials Defeaters** (10-15 instances)
```python
# Examples:
- Metallic glass: "~brittle(X) :- amorphous_metal(X)"
- Shape-memory alloys: "recovers_shape(X) :- shape_memory_alloy(X)"
- Graphene: transparency exception
- Aerogels: density exception
- Superconductors: resistance exception

# Target Nov > 0 for several instances
```

**Day 5: Validation & Testing**
```bash
# Checklist:
- [ ] All instances validate conservativity
- [ ] Compute Nov(gold, D) for each
- [ ] Compute d_rev for each
- [ ] Generate distractors (5 per instance)
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Documentation complete
```

### Implementation Checklist

**Setup**:
- [ ] Review `scripts/generate_level3_instances.py` (3 working examples)
- [ ] Review `author.py` lines 594-667 (conservativity, novelty, revision distance)
- [ ] Create `instances/biology_level3_instances.json`
- [ ] Create `instances/legal_level3_instances.json`
- [ ] Create `instances/materials_level3_instances.json`

**For Each Instance**:
```python
# Template
instance = {
    'level': 3,
    'domain': 'biology',  # or legal, materials
    'anomaly': 'flies(penguin)',  # What theory predicts wrongly
    'challenge_theory': D_minus,  # Theory without defeater
    'gold_resolution': {
        'rule': "~flies(X) :- penguin(X)",
        'superiority': [],  # If needed
        'Nov': 0.0,  # Compute with predicate_novelty()
        'd_rev': 1,  # Compute with revision_distance()
        'conservative': True  # Verify with is_conservative_resolution()
    },
    'candidates': [
        # 1 gold + 5 distractors
    ],
    'metadata': {
        'exception_type': 'weak_blocking',  # or strong, restructuring
        'source': 'textbook_biology',
        'validation_date': '2026-02-13'
    }
}
```

**Validation**:
```python
# For each instance, verify:
from blanc.author import is_conservative_resolution, predicate_novelty, revision_distance

# 1. Anomaly is defeasible
assert defeasible_provable(D_minus, negate(anomaly))
assert not strictly_provable(D_minus, negate(anomaly))

# 2. Gold resolves anomaly
D_with_gold = D_minus.copy()
D_with_gold.add_rule(gold_rule)
assert not defeasible_provable(D_with_gold, negate(anomaly))

# 3. Gold is conservative
expectations = compute_expectations(D_minus)
assert is_conservative_resolution(D_minus, {gold_rule}, anomaly, expectations)

# 4. Metrics correct
assert predicate_novelty(gold_rule, D_minus) == instance['gold_resolution']['Nov']
assert revision_distance(D_minus, D_with_gold) == instance['gold_resolution']['d_rev']
```

### Success Criteria

**Minimum (20-30 instances)**:
- [ ] 10 biology, 10 legal, 10 materials
- [ ] All validated for conservativity
- [ ] At least 5 with Nov > 0
- [ ] Ready for pilot

**Target (35-50 instances)**:
- [ ] 15-20 biology, 10-15 legal, 10-15 materials
- [ ] 10-15 with Nov > 0
- [ ] Mix of weak/strong/restructuring
- [ ] Statistical power for analysis

### Resources

**Code**:
- `scripts/generate_level3_instances.py` - Working examples
- `src/blanc/author/` - Generation framework
- `experiments/evaluation_pipeline.py` - Ready for Level 3

**Documentation**:
- [REVISED_IMPLEMENTATION_PLAN.md](REVISED_IMPLEMENTATION_PLAN.md) - Week 8.5 details
- [OBJECTIVE_ACCOUNTING.md](../OBJECTIVE_ACCOUNTING.md) - Why this matters
- [NEXT_STEPS_SUMMARY.md](../NEXT_STEPS_SUMMARY.md) - Executive summary

---

## Then: Week 9 Pilot (Original Plan)

### Day 1: OpenAI API Integration (6-8 hours)

**Tasks**:
1. Setup OpenAI API key
2. Create model interface for GPT-4o
3. Test on sample instances
4. Implement rate limiting and error handling

**File to create**: `experiments/model_interfaces/openai_interface.py`

---

### Day 2: Additional Model APIs (6-8 hours)

**Tasks**:
1. Anthropic API (Claude 3.5 Sonnet)
2. Google API (Gemini 1.5 Pro)
3. Test all interfaces

**Files**: `experiments/model_interfaces/anthropic_interface.py`, etc.

---

### Day 3-4: Evaluation Pipeline (8-12 hours)

**Tasks**:
1. Batch evaluation framework
2. Prompting system (direct + CoT)
3. Response caching
4. Progress tracking

**File**: `experiments/evaluation_pipeline.py`

---

### Day 5: Pilot Evaluation (4-6 hours)

**Tasks**:
1. Run pilot on 20-50 instances
2. Verify pipeline works
3. Estimate costs
4. Debug issues

---

## Important Context

### Expert-Only Policy (CRITICAL)

**All knowledge bases MUST be expert-curated**

See `KNOWLEDGE_BASE_POLICY.md` for full policy.

**Current expert sources**:
- YAGO 4.5 (Télécom Paris, SIGIR 2024)
- WordNet 3.0 (Princeton, Miller 1995)
- LKIF Core (U Amsterdam, ESTRELLA)
- MatOnto (MatPortal, materials community)

**Never**: Hand-craft knowledge or instances

---

### Development Strategy

**Local Development** (Weeks 1-12):
- Use KB subsets (16-201 rules) for fast iteration
- 374 development instances sufficient
- Local generation in minutes

**HPC Production** (Weeks 13-14):
- Full expert KBs (2,318 rules)
- Generate millions of instances
- CURC Alpine deployment ready (`hpc/` folder)

**Current**: Use local instances for all development

---

### Testing Best Practices

**After any changes**:
```bash
# Run tests
python -m pytest tests/ --tb=short

# Check coverage
python -m pytest tests/ --cov=src/blanc --cov-report=term

# Expected: 310+ passing, 77-80% coverage
```

**Before committing**:
- All tests must pass
- No import errors
- Coverage maintained or improved

---

## Known Issues and Workarounds

### Issue 1: M1+D3 Validation at 0%

**Context**: M1 (narrative) → D3 (semantic parser) is challenging  
**Status**: Expected difficulty (M1 is hardest modality)  
**Workaround**: M1+D2 (template) works better  
**Impact**: Not blocking (3 of 4 modalities perfect)

**Resolution**: Accept as limitation or improve D3 NLP (complex, low priority)

---

### Issue 2: Coverage at 77% vs 90% Target

**Context**: Target was 90%, achieved 77%  
**Status**: High quality coverage on critical paths (87-99%)  
**Impact**: None - coverage is good where it matters

**Resolution**: Can add more tests if needed, but 77% is acceptable

---

### Issue 3: Level 3 Instances

**Context**: Only Level 2 instances generated  
**Status**: Level 3 requires manual defeater authoring  
**Impact**: Section 4.3.3 deferred, Level 3 evaluation deferred

**Resolution**: Can add Level 3 later or proceed without for initial submission

---

## Git Workflow

### Standard Development Cycle

```bash
# 1. Make changes
# 2. Test
python -m pytest tests/ --tb=short

# 3. Check coverage if major changes
python -m pytest tests/ --cov=src/blanc

# 4. Stage and commit
git add <files>
git commit -m "Brief description of changes"

# 5. Push to GitHub
git push origin main

# 6. Verify
git status
```

### Commit Message Format

**Good examples from this project**:
- "Week X: Feature implemented - brief description"
- "Fix issue: Specific problem solved"
- "Add tests: Coverage improvement"

**Include**:
- What was done
- Why (if not obvious)
- Impact on coverage/tests

---

## Troubleshooting

### If Tests Fail

1. **Check specific failure**:
   ```bash
   python -m pytest tests/path/to/test.py -v
   ```

2. **Check imports**:
   ```bash
   python -c "from blanc.codec import encode_m2; print('OK')"
   ```

3. **Verify environment**:
   ```bash
   pip list | grep -E "numpy|scipy|lark|Levenshtein|pytest"
   ```

### If Coverage Drops

**Common causes**:
- Added new untested code (expected)
- Test collection issues

**Fix**: Add tests for new code

### If Git Issues

**Large file error**:
- data/ is in .gitignore (correct)
- Don't commit raw expert KBs
- Only commit extracted KBs (examples/)

---

## Development Priorities

### Must Have (Critical Path)

1. ✅ Expert KBs (DONE)
2. ✅ Development instances (DONE)
3. ✅ Complete codec (DONE)
4. ⏳ LLM evaluation (Week 8-10)
5. ⏳ Results analysis (Week 10)
6. ⏳ Paper integration (Week 13-14)

### Should Have (Important)

- Advanced analyses (Weeks 11-12)
- HPC production scale (Weeks 13-14)
- 85-90% coverage (nice-to-have)

### Could Have (Optional)

- Level 3 instances
- Additional model evaluations
- Perfect round-trip for all modalities

---

## Resources and References

### Documentation
- `README.md` - Project overview
- `STATUS.md` - Current status
- `NEURIPS_FULL_ROADMAP.md` - Full 14-week plan
- `docs/completed_weeks/` - Weekly completion reports

### Code Organization
- `src/blanc/reasoning/` - Defeasible logic (91-99% coverage)
- `src/blanc/codec/` - All encoders/decoders
- `src/blanc/author/` - Instance generation
- `src/blanc/core/` - Data structures

### Expert KBs
- `examples/knowledge_bases/biology_kb.py` - Full (927 rules)
- `examples/knowledge_bases/biology_kb_subset.py` - Dev (16 rules)
- Similar for legal and materials

### Scripts
- `scripts/generate_dev_instances.py` - Generate instances locally
- `experiments/roundtrip_validation.py` - Validate codec
- `experiments/statistics.py` - Statistical analysis

---

## Week 8 Specific Guidance

### Goal

Build LLM evaluation infrastructure

### Prerequisites

**API Keys needed**:
- OpenAI API key (GPT-4o)
- Anthropic API key (Claude 3.5 Sonnet)
- Google API key (Gemini 1.5 Pro)

**Budget**: ~$450-700 for full evaluation

### Approach

**Start with one model** (GPT-4o):
1. Build interface
2. Test on 10 instances
3. Verify decoder works
4. Estimate costs
5. Scale up

**Then add other models**

---

## Success Criteria for Week 8

- [ ] All 5 model interfaces working
- [ ] Can run evaluation on sample instances
- [ ] Response caching implemented
- [ ] Decoder pipeline integrated
- [ ] Cost estimation verified

---

## Key Reminders

### Critical Policies

1. **Expert-only KB policy** (MANDATORY)
   - No hand-crafted knowledge
   - All from peer-reviewed sources
   - See KNOWLEDGE_BASE_POLICY.md

2. **Test-driven development**
   - Test as you build
   - Maintain coverage
   - All tests must pass

3. **Local dev, HPC production**
   - Develop with 374 instances locally
   - Scale to millions with HPC later (Weeks 13-14)

---

## Quick Reference Commands

### Development
```bash
# Run all tests
python -m pytest tests/ --tb=short

# Check coverage
python -m pytest tests/ --cov=src/blanc --cov-report=term

# Run specific test
python -m pytest tests/codec/test_m3_encoder.py -v

# Generate instances
python scripts/generate_dev_instances.py

# Run validation
python experiments/roundtrip_validation.py
```

### Git
```bash
# Status
git status

# Commit workflow
git add <files>
git commit -m "Description"
git push origin main

# Review history
git log --oneline -20
```

### Verification
```bash
# Load expert KB
python -c "from examples.knowledge_bases.biology_kb_subset import create_biology_subset; kb = create_biology_subset(); print(f'{len(kb.rules)} rules')"

# Test codec
python -c "from blanc.codec import encode_m2, decode_d2; from blanc.core.theory import Rule, RuleType; r = Rule('flies(X)', ('bird(X)',), RuleType.DEFEASIBLE, 'r1'); print(encode_m2(r))"
```

---

## Project Structure Quick Reference

```
blanc/
├── STATUS.md                      # Current status (READ FIRST)
├── CONTINUE_DEVELOPMENT.md        # This document
├── NEURIPS_FULL_ROADMAP.md        # 14-week plan
│
├── src/blanc/                     # Production code
│   ├── reasoning/                 # Logic engine (91-99% coverage)
│   ├── codec/                     # Encoders/decoders (53-92%)
│   ├── author/                    # Instance generation (65-100%)
│   ├── core/                      # Data structures (80-100%)
│   └── generation/                # Utilities (92-93%)
│
├── tests/                         # 310+ tests
├── examples/knowledge_bases/      # Expert KBs + subsets
├── instances/                     # 374 development instances
├── experiments/                   # Analysis scripts
├── results/                       # Analysis results
├── scripts/                       # Utilities
├── hpc/                          # HPC infrastructure (Weeks 13-14)
└── docs/                         # Historical documentation
```

---

## Weeks 8-14 Roadmap Summary

**Week 8**: LLM interfaces + evaluation pipeline  
**Week 9**: Run evaluations (~46K calls)  
**Week 10**: Error analysis + metrics  
**Week 11**: Scaling analysis  
**Week 12**: Advanced analyses  
**Week 13**: HPC production (1M+ instances)  
**Week 14**: Paper integration + submission

---

## Contact and Resources

**Repository**: https://github.com/PatrickAllenCooper/blanc  
**Branch**: main  
**Python**: 3.11+ required  
**Key Package**: Lark (for D3 decoder)

---

## Final Checks Before Starting Week 8

### Verification Checklist

- [ ] Git repo cloned and up to date
- [ ] All tests pass (`python -m pytest tests/`)
- [ ] Coverage at 77-80%
- [ ] Expert KBs load successfully
- [ ] Can generate instances locally
- [ ] Validation script runs
- [ ] All documentation read

### API Setup for Week 8

- [ ] OpenAI API key obtained
- [ ] Anthropic API key obtained
- [ ] Google API key obtained
- [ ] Budget approved (~$500-700)
- [ ] Rate limits understood

---

## Summary

**Current State**: Infrastructure phase (Weeks 1-7) COMPLETE  
**Next Goal**: LLM evaluation infrastructure (Week 8)  
**Timeline**: 50% done, 50% remaining  
**Confidence**: HIGH - strong foundation

**Everything needed for Weeks 8-14 is ready** ✅

---

## Questions? Check These First

1. **What's the current status?** → STATUS.md
2. **What was done in Week X?** → docs/completed_weeks/
3. **How do I run X?** → This document or QUICK_START.md
4. **What's the plan?** → NEURIPS_FULL_ROADMAP.md
5. **Why this architecture?** → docs/ARCHITECTURE_AUDIT.md

---

**Ready to continue development anytime** ✅

---

**Author**: Patrick Cooper  
**Last Updated**: 2026-02-12  
**Session End**: Infrastructure phase complete  
**Next Session**: Week 8 - LLM evaluation
