# Development Strategy: Local Development + HPC Production

**Date**: 2026-02-12  
**Philosophy**: Fast local iteration, massive HPC production  
**Key Insight**: Don't slow development with HPC overhead

---

## Revised Strategy

### Development Phase (Weeks 1-12): LOCAL

**Approach**: Work with manageable subsets
- Use 50-200 rule KB subsets for fast iteration
- Develop and test on local CPU (seconds, not hours)
- Iterate quickly on algorithms and approaches
- Verify correctness on small scale

**Advantages**:
- ✅ Fast feedback loop (seconds to minutes)
- ✅ Easy debugging
- ✅ Rapid iteration
- ✅ No HPC queue delays
- ✅ No batch script overhead

### Production Phase (Weeks 13-14): HPC

**Approach**: Scale to millions of instances
- Deploy to CURC Alpine with SLURM
- Use full expert KBs (2,318 rules)
- Generate millions of instances
- Run overnight/multi-day batch jobs
- Final production benchmark

**Advantages**:
- ✅ Can generate millions of instances
- ✅ Leverage 64+ CPU cores
- ✅ Production-quality scale
- ✅ HPC-ready infrastructure proves industrial capability

---

## Immediate Plan (Weeks 3-12): Local Development

### Week 3: Instance Generation (Local)

**Approach**: Create 100-200 rule expert KB subsets

**Biology Subset** (100 rules):
- Select vertebrate taxonomy from YAGO
- Keep behavioral rules (9 defeasible)
- Fast local generation (~10-30 instances/min)
- Generate 100-200 instances

**Legal Subset** (100 rules):
- Use LKIF Core as-is (201 rules, manageable)
- Or select subset if needed
- Generate 100-200 instances

**Materials Subset** (150 rules):
- Select metals/alloys from MatOnto
- Focus on structure-property rules
- Generate 100-200 instances

**Target**: 300-600 instances for development/testing

**Timeline**: Week 3 (THIS WEEK)

### Weeks 4-12: Development with Local Instances

**Use local instances** (300-600) for:
- Statistical analysis development (Week 4)
- Codec development (Weeks 5-7)
- Evaluation pipeline development (Weeks 8-10)
- Analysis development (Weeks 11-12)

**Iterate fast**: No HPC delays, immediate feedback

---

## Final Production (Weeks 13-14): HPC Scale

### Deploy to CURC Alpine

**Generate millions** of instances:
- Full expert KBs (2,318 rules)
- All 13 partition strategies
- All 3 domains
- Multiple distractor strategies
- Target: 1M+ instances

**Use HPC batch jobs**:
- Submit overnight
- 64+ CPU cores
- Array jobs (parallel partition strategies)
- Multi-day runs acceptable

**Purpose**: Final production benchmark for paper

---

## Revised Roadmap

### Weeks 1-2: ✅ COMPLETE

- Expert KB foundation
- 2,318 expert rules from 4 institutions
- Infrastructure ready

### Week 3: LOCAL - KB Subsets + Instance Generation

**Create local development subsets**:
- Biology: 100 rule subset (vertebrates)
- Legal: Use full 201 rules (manageable)
- Materials: 150 rule subset (metals/alloys)

**Generate development instances**:
- 100-200 per KB
- Total: 300-600 instances
- Fast local generation
- Sufficient for development

### Weeks 4-12: LOCAL - Development

**Use local instances throughout**:
- Week 4: Statistical analysis (develop on 300-600 instances)
- Weeks 5-7: Codec (test on local instances)
- Weeks 8-10: Evaluation (pilot on local instances)
- Weeks 11-12: Advanced analysis (develop on local instances)

**Iterate quickly without HPC overhead**

### Weeks 13-14: HPC - Production Scale

**Deploy to CURC Alpine**:
- Full expert KBs (2,318 rules)
- Generate 1M+ instances
- Final production benchmark
- Multi-day HPC batch jobs acceptable

**Use for paper**:
- Final statistics on millions of instances
- Final model evaluations
- Production-quality results

---

## Technical Approach

### Local Development Subsets

**Create KB slicing function**:
```python
def create_biology_subset(domain='vertebrates', max_rules=100):
    """Create manageable subset for local development."""
    # Select specific taxonomic domain
    # Keep essential rules
    # Fast for iteration
```

**Benefits**:
- Fast generation (seconds to minutes)
- Full verification of pipeline
- Rapid debugging
- Quick iteration

### HPC Production Scripts

**Keep SLURM scripts for final production**:
- `hpc/slurm_generate_instances.sh`
- `hpc/slurm_array_job.sh` (for parallel strategies)
- `hpc/slurm_scale_to_millions.sh` (final production)

**Use only in Week 13-14**

---

## Why This Works

### Development Needs Speed

**Requirements**:
- Fast feedback (seconds to minutes)
- Easy debugging
- Rapid iteration
- No queue delays

**Solution**: Local subsets (100-200 rules)

### Production Needs Scale

**Requirements**:
- Millions of instances
- Full expert KBs
- Industrial-scale demonstration
- Publication-quality

**Solution**: HPC batch jobs (Weeks 13-14)

---

## Advantages

### Fast Development ✅

- No HPC overhead during development
- Immediate feedback
- Quick iteration on algorithms
- Can change approach easily

### Impressive Production ✅

- Final benchmark: Millions of instances
- Full expert KBs: 2,318 rules
- HPC-generated: Shows industrial capability
- Government KBs: Emphasizes scale and quality

### Best of Both ✅

- Develop fast (local)
- Produce massive (HPC)
- Iterate without delays
- Scale when needed

---

## Updated Week 3 Plan

### Day 1-2: Create Local KB Subsets

**Biology subset** (100 rules):
- Select vertebrate taxonomy
- Keep behavioral rules
- Fast local generation

**Legal subset** (use full 201 - manageable)

**Materials subset** (150 rules):
- Select metals/alloys domain
- Keep property rules

### Day 3-4: Generate Local Instances

**Target**: 100-200 per KB
- Total: 300-600 instances
- Fast local generation
- Verify pipeline works

### Day 5: Verify Pipeline

**Prove**:
- Generation works on expert KBs
- Can scale to full size (HPC ready)
- Sufficient for development

---

## HPC Deferred to Week 13-14

**Keep infrastructure** (already built):
- Parallel scripts ready
- SLURM batch scripts ready
- Can deploy when needed

**Use when**: Final production runs
- Week 13: Generate millions
- Week 14: Final benchmark for paper

**Don't use for**: Development (Weeks 3-12)

---

## Advantages for Paper

### Development Story

"We developed the pipeline using manageable expert KB subsets, enabling rapid iteration and algorithm refinement."

### Production Story

"For final production, we deployed to CURC Alpine HPC with 64 CPU cores, generating millions of instances from the full expert KBs (2,318 rules from government-sponsored sources)."

**Shows**: Both engineering rigor AND industrial scale

---

## Conclusion

**Strategy**: 
- Develop LOCAL with subsets (fast)
- Produce at SCALE with HPC (impressive)

**Timeline**:
- Weeks 3-12: Local development (300-600 instances)
- Weeks 13-14: HPC production (millions of instances)

**Benefits**:
- Fast iteration during development
- Massive scale for final paper
- Best of both worlds

**Next**: Create local KB subsets for Week 3 development

---

**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Strategy revised for fast local development
