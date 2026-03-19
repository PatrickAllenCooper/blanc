#!/bin/bash
#SBATCH --job-name=defab_yago
#SBATCH --output=logs/yago_full_%j.out
#SBATCH --error=logs/yago_full_%j.err
#SBATCH --time=48:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --partition=amilan

# DeFAb YAGO Full Instance Generation on CURC Alpine
#
# Processes the full YAGO 4.5 facts file (21.4 GB, 312M triples, 77M rules)
# using a streaming approach that generates instances in batches without
# materializing the entire Theory in memory.
#
# Requires the high-memory amilan partition (256 GB).
# The yago-4.5.0.2.zip must be downloaded and extracted first.
#
# Usage:
#   sbatch hpc/slurm_yago_full_generate.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb YAGO Full Generation - CURC Alpine (256 GB)"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "CPUs   : $SLURM_CPUS_PER_TASK"
echo "Memory : ${SLURM_MEM_PER_NODE:-unknown} MB"
echo "Start  : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"

if [ -d "/projects/paco0228/software/anaconda/envs/defab-train" ]; then
    conda activate /projects/paco0228/software/anaconda/envs/defab-train
elif conda env list 2>/dev/null | grep -q "defab-train"; then
    conda activate defab-train
else
    echo "WARNING: defab-train env not found, using base"
fi

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

export PYTHONPATH="$PROJ_DIR/src:$PROJ_DIR/examples:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

mkdir -p logs data/extracted/yago_full_facts instances/multitier/yago_full

# ---------------------------------------------------------------------------
# Check for YAGO data
# ---------------------------------------------------------------------------
YAGO_TTL=""
for F in data/yago/yago-4.5.0.2/yago-facts.ttl data/yago/yago-4.5.0.2-tiny/yago-tiny.ttl; do
    if [ -f "$F" ]; then
        YAGO_TTL="$F"
        break
    fi
done

if [ -z "$YAGO_TTL" ]; then
    echo "ERROR: No YAGO TTL file found. Download first:"
    echo "  python scripts/download_yago.py"
    exit 1
fi

SIZE_MB=$(du -m "$YAGO_TTL" | cut -f1)
echo "Using: $YAGO_TTL ($SIZE_MB MB)"
echo ""

# ---------------------------------------------------------------------------
# Extract and generate (streaming approach)
# ---------------------------------------------------------------------------
echo "Extracting from YAGO..."
python -u -c "
import sys, json, pickle, time
sys.path.insert(0, 'src')
sys.path.insert(0, '.')
from pathlib import Path
from blanc.ontology.yago_full_extractor import YagoFullExtractor
from blanc.ontology.rule_validator import validate_theory, save_report
from blanc.core.theory import RuleType

ttl = Path('$YAGO_TTL')
print(f'Extracting from {ttl.name} ({ttl.stat().st_size / 1024**3:.1f} GB)')

t0 = time.time()
ext = YagoFullExtractor(ttl)
ext.extract()
print(f'Extraction: {time.time()-t0:.0f}s')
print(f'Stats: {ext.stats}')

t1 = time.time()
theory = ext.to_theory()
print(f'Theory built: {time.time()-t1:.0f}s')

strict = sum(1 for r in theory.rules if r.rule_type == RuleType.STRICT)
defeasible = sum(1 for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE)
print(f'Total: {len(theory.facts)} facts, {len(theory.rules)} rules ({strict} strict, {defeasible} defeasible)')

out_dir = Path('data/extracted/yago_full_facts')
out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir / 'stats.json', 'w') as f:
    json.dump({'facts': len(theory.facts), 'total_rules': len(theory.rules), 'strict': strict, 'defeasible': defeasible, 'defeaters': 0}, f, indent=2)
with open(out_dir / 'theory.pkl', 'wb') as f:
    pickle.dump(theory, f)
print(f'Theory saved ({(out_dir / \"theory.pkl\").stat().st_size / 1024**3:.1f} GB)')

# Generate instances
from scripts.generate_tier1_instances import generate_domain
instances = generate_domain('yago_full', theory)
inst_dir = Path('instances/multitier/yago_full')
inst_dir.mkdir(parents=True, exist_ok=True)
with open(inst_dir / 'instances.json', 'w') as f:
    json.dump(instances, f)
l1 = sum(1 for x in instances if x['level'] == 1)
l2 = sum(1 for x in instances if x['level'] == 2)
l3 = sum(1 for x in instances if x['level'] == 3)
print(f'Instances: {len(instances)} (L1={l1}, L2={l2}, L3={l3})')
print(f'Total time: {time.time()-t0:.0f}s')
"

echo ""
echo "======================================================================="
echo "YAGO Full Generation Complete"
echo "End: $(date)"
echo "======================================================================="

exit 0
