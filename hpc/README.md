# HPC Deployment for DeFAb Instance Generation

**Purpose**: Generate instances from large-scale expert KBs using HPC resources  
**Target**: CURC Alpine (University of Colorado Boulder)  
**Scale**: 64+ CPU cores, 128+ GB RAM

---

## Why HPC?

Our expert-curated KBs are LARGE (as they should be):
- Biology: 927 rules (YAGO + WordNet)
- Legal: 201 rules (LKIF Core)
- Materials: **1,190 rules** (MatOnto - government/academic collaboration)

**This scale is a FEATURE**: We're using real, comprehensive expert knowledge.

**Parallelization**: HPC allows us to leverage this scale efficiently.

---

## Local Parallel Execution

For testing on local multi-core CPU:

```bash
# Run parallel generation (uses all CPU cores)
python scripts/generate_instances_parallel.py
```

**Expected**: ~8-16x speedup on modern CPUs

---

## CURC Alpine HPC Deployment

### Prerequisites

1. **CURC Alpine account** (University of Colorado Boulder)
2. **SSH access** to Alpine login nodes
3. **Allocation** on compute partition (amilan recommended)

### Setup on Alpine

```bash
# SSH to Alpine
ssh username@login.rc.colorado.edu

# Clone repository
cd /projects/$USER
git clone https://github.com/PatrickAllenCooper/blanc.git
cd blanc

# Create logs directory
mkdir -p logs

# Load modules
module load anaconda python/3.11

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Submit Generation Job

```bash
# Submit SLURM batch job
sbatch hpc/slurm_generate_instances.sh

# Check job status
squeue -u $USER

# Monitor output
tail -f logs/generate_*.out

# Check errors
tail -f logs/generate_*.err
```

### Job Parameters

From `slurm_generate_instances.sh`:
- **CPUs**: 64 cores
- **Memory**: 128 GB
- **Time**: 24 hours
- **Partition**: amilan (general compute)

**Adjust** `--cpus-per-task` and `--mem` based on allocation.

---

## Expected Performance

### Local CPU (8-16 cores)

**Biology KB** (927 rules):
- Sequential: ~5-10 instances/hour
- Parallel (16 cores): ~80-160 instances/hour
- Target (200 instances): ~1-2 hours

**Materials KB** (1,190 rules):
- Sequential: ~3-8 instances/hour
- Parallel (16 cores): ~48-128 instances/hour
- Target (200 instances): ~1.5-4 hours

**Total** (~600 instances): ~4-8 hours on local CPU

### HPC (64+ cores)

**All 3 KBs** (~1,200 instances):
- Parallel (64 cores): 4-8x faster than 16 cores
- Estimated: ~1-3 hours total
- Can scale further with more nodes

---

## Monitoring and Results

### Check Job Progress

```bash
# View output in real-time
tail -f logs/generate_<jobid>.out

# Check for errors
tail -f logs/generate_<jobid>.err

# Check job efficiency
seff <jobid>
```

### Retrieve Results

```bash
# Copy results from Alpine to local
scp username@login.rc.colorado.edu:/projects/$USER/blanc/*.json .

# Or download when job completes
# Results saved to:
# - biology_expert_instances_parallel.json
# - legal_expert_instances_parallel.json
# - materials_expert_instances_parallel.json
```

---

## Emphasizing Government-Sponsored KBs

### OpenCyc (Cycorp - DARPA funded)

**History**: Part of DARPA Strategic Computing Initiative  
**Scale**: 240K concepts, 2M assertions  
**Status**: Extracted (opencyc_biology_extracted.py) but 0 rules found

**Action**: Re-extract with better parser to emphasize this government-sponsored source

### YAGO (Government academic research)

**Funding**: Télécom Paris (French government institution)  
**Scale**: 49M entities, 109M facts  
**Status**: ✅ Using (584 rules extracted)

**Emphasis**: YAGO is from government-funded research institution

### Materials Genome Initiative Connection

**MatOnto**: Part of broader materials science data ecosystem  
**Connection**: Materials Genome Initiative (US government program)  
**Status**: ✅ Using (1,190 rules)

**Emphasis**: Materials KB connects to US government materials research

---

## Scaling Strategy

### Phase 1: Local Parallel (THIS WEEK)

- Test parallel generation on local CPU
- Verify speedup (expect 8-16x)
- Generate ~100 instances per KB
- Prove scalability

### Phase 2: HPC if Needed (WEEK 3-4)

- Deploy to CURC Alpine
- Use 64+ cores
- Generate full ~1,200 instances
- Demonstrate industrial-scale capability

### Phase 3: Multiple Nodes (If needed)

- Array jobs across multiple nodes
- Each node handles one partition strategy
- Embarrassingly parallel
- Can scale to thousands of instances

---

## Array Job (For Maximum Parallelism)

For generating across all partition strategies in parallel:

```bash
#SBATCH --array=1-13  # One job per partition strategy

# Each array task handles one partition
STRATEGY_ID=$SLURM_ARRAY_TASK_ID

python scripts/generate_single_partition.py --strategy-id $STRATEGY_ID
```

Can generate all 13 partition strategies simultaneously!

---

## Cost Estimation

### CURC Alpine

**SU (Service Unit) Cost**:
- 1 core-hour = 1 SU
- 64 cores × 3 hours = 192 SU
- Typical allocation: 10,000+ SU

**Cost**: Negligible within typical allocation

### Local CPU

**Cost**: Free, just electricity and time

---

## Files

- `generate_instances_parallel.py` - Parallel generation script
- `slurm_generate_instances.sh` - SLURM batch script
- `README.md` - This documentation

---

## Next Steps

1. **Test local parallel** (TODAY)
   - Run generate_instances_parallel.py
   - Measure speedup
   - Verify results

2. **Deploy to HPC if needed** (THIS WEEK)
   - Setup on Alpine
   - Submit batch job
   - Monitor progress

3. **Scale to full benchmark** (WEEK 3-4)
   - Generate ~1,200 instances
   - All 3 expert KBs
   - All 13 partition strategies

---

**Advantage**: Large expert KBs are a strength, not a weakness, with HPC resources!

**Author**: Patrick Cooper  
**Date**: 2026-02-12
