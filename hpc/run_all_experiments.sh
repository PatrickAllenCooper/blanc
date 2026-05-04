#!/usr/bin/env bash
#
# DeFAb Comprehensive Experiment Runner
#
# Submits ALL experiments described in the paper using SLURM dependency chains
# on CURC Alpine. Covers the full pipeline from instance generation through
# base evaluation, fine-tuning, debate, and analysis.
#
# Phases:
#   A0  Instance generation (expert KBs -> 374 L2 + 35 L3 instances)
#   A1  Symbolic baseline (clingo ceiling: L2=100%, L3=100%)
#   A2  Foundry evaluation (4 models: GPT-5.2, Kimi, Claude, DeepSeek-R1)
#   A3  CURC open-source base evaluation (3 models via vLLM)
#   A4  Phase A analysis (Tables 1-3, error taxonomy, novelty, scaling)
#   B0  SFT data preparation
#   B1  Response sampling (3 models x 16 responses/instance)
#   B2  DPO training (12 standard + 3 sequential + 1 l12_only + 3 gamma = 19)
#   B3  RLHF/VITL training (3 VITL + 1 standard RM = 4)
#   BS  SFT training (3 models)
#   BG  GRPO/RLVR training (3 models)
#   B5  Evaluate all fine-tuned checkpoints
#   B6  Fine-tuning analysis (Tables 4-6, Conjectures 1-6)
#   C   Adversarial defeasible debate (Tables 7-9)
#
# Total: ~65 SLURM jobs, ~158 GPU-days (free on CURC)
#
# Flags:
#   --dry-run           Print commands without submitting
#   --phase PHASE       Run only one phase (A, B, C)
#   --skip-instances    Skip A0 (instances already exist)
#   --skip-foundry      Skip A2 (Foundry eval already done)
#   --skip-curc-base    Skip A3 (optional scaling analysis)
#   --skip-debate       Skip C (debate already done)
#   --resume-from PHASE Resume from a specific phase (A1, A2, B0, B1, etc.)
#
# Prerequisites:
#   - CURC account with aa100 partition access
#   - defab-train and vllm-env conda environments (run setup_curc_env.sh)
#   - FOUNDRY_API_KEY set in environment or ~/.bashrc
#
# Usage:
#   cd /projects/paco0228/blanc
#   bash hpc/run_all_experiments.sh
#   bash hpc/run_all_experiments.sh --dry-run
#   bash hpc/run_all_experiments.sh --phase B
#   bash hpc/run_all_experiments.sh --skip-foundry --skip-instances
#   bash hpc/run_all_experiments.sh --resume-from B1
#
# Author: Anonymous Authors

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJ_DIR"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
DRY_RUN=false
PHASE_FILTER=""
SKIP_INSTANCES=false
SKIP_FOUNDRY=false
SKIP_CURC_BASE=false
SKIP_DEBATE=false
RESUME_FROM=""

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)        DRY_RUN=true ;;
        --phase)          PHASE_FILTER="$2"; shift ;;
        --skip-instances) SKIP_INSTANCES=true ;;
        --skip-foundry)   SKIP_FOUNDRY=true ;;
        --skip-curc-base) SKIP_CURC_BASE=true ;;
        --skip-debate)    SKIP_DEBATE=true ;;
        --resume-from)    RESUME_FROM="$2"; shift ;;
        *)                echo "Unknown flag: $1"; exit 1 ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Phase ordering for --resume-from
# ---------------------------------------------------------------------------
PHASE_ORDER="A0 A1 A2 A3 A4 B0 B1 BS B2 B3 BG B5 B6 C"
should_run_phase() {
    local PHASE="$1"
    if [ -n "$PHASE_FILTER" ]; then
        [[ "$PHASE" == "$PHASE_FILTER"* ]] && return 0 || return 1
    fi
    if [ -n "$RESUME_FROM" ]; then
        local found=false
        for p in $PHASE_ORDER; do
            if [ "$p" = "$RESUME_FROM" ]; then found=true; fi
            if [ "$found" = "true" ] && [ "$p" = "$PHASE" ]; then return 0; fi
        done
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TOTAL_SUBMITTED=0
TOTAL_SKIPPED=0

submit() {
    local DESC="$1"
    shift
    if [ "$DRY_RUN" = "true" ]; then
        echo "  [DRY RUN] $*"
        echo "DRY_${TOTAL_SUBMITTED}"
        (( TOTAL_SKIPPED++ )) || true
    else
        local JID
        JID=$(sbatch --parsable "$@")
        echo "  Submitted: $DESC (job $JID)"
        (( TOTAL_SUBMITTED++ )) || true
        echo "$JID"
    fi
}

dep_flag() {
    local JIDS="$1"
    if [ "$DRY_RUN" = "true" ] || [ -z "$JIDS" ]; then
        echo ""
    else
        echo "--dependency=afterok:${JIDS}"
    fi
}

multi_dep_flag() {
    local COMBINED=""
    for JID in "$@"; do
        if [ -n "$JID" ] && [ "$DRY_RUN" != "true" ]; then
            if [ -n "$COMBINED" ]; then
                COMBINED="${COMBINED}:${JID}"
            else
                COMBINED="$JID"
            fi
        fi
    done
    if [ -n "$COMBINED" ]; then
        echo "--dependency=afterok:${COMBINED}"
    else
        echo ""
    fi
}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
MODEL_DS="casperhansen/deepseek-r1-distill-llama-70b-awq"
MODEL_Q72="Qwen/Qwen2.5-72B-Instruct-AWQ"
MODEL_Q32="Qwen/Qwen2.5-32B-Instruct-AWQ"
declare -a MODELS=("$MODEL_Q72" "$MODEL_Q32" "$MODEL_DS")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INSTANCE_LIMIT="${INSTANCE_LIMIT:-120}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-35}"
MODALITIES="${MODALITIES:-M4 M2 M1 M3}"
STRATEGIES="${STRATEGIES:-direct cot}"

echo "======================================================================="
echo "DeFAb Comprehensive Experiment Runner"
echo "======================================================================="
echo "Project dir    : $PROJ_DIR"
echo "Dry run        : $DRY_RUN"
echo "Phase filter   : ${PHASE_FILTER:-all}"
echo "Resume from    : ${RESUME_FROM:-beginning}"
echo "Skip instances : $SKIP_INSTANCES"
echo "Skip Foundry   : $SKIP_FOUNDRY"
echo "Skip CURC base : $SKIP_CURC_BASE"
echo "Skip debate    : $SKIP_DEBATE"
echo "Instance limit : $INSTANCE_LIMIT"
echo "Level 3 limit  : $LEVEL3_LIMIT"
echo "Modalities     : $MODALITIES"
echo "Strategies     : $STRATEGIES"
echo "Start          : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Phase 0: Preflight checks
# ---------------------------------------------------------------------------
echo "=== Phase 0: Preflight ==="

if [ ! -d "/scratch/alpine" ]; then
    echo "ERROR: This script must be run on CURC Alpine."
    echo "SSH in: ssh paco0228@login.rc.colorado.edu"
    exit 1
fi

echo "Current commit: $(git log --oneline -1)"

if [ "$SKIP_FOUNDRY" != "true" ]; then
    if [ -z "${FOUNDRY_API_KEY:-}" ]; then
        echo "WARNING: FOUNDRY_API_KEY not set. Foundry evaluation will fail."
        echo "Set it in ~/.bashrc or export before running."
    fi
fi

mkdir -p logs experiments/results experiments/finetuning/data \
         experiments/finetuning/checkpoints paper/tables

echo "Preflight OK."
echo ""

# Track job IDs for dependency chains
JOB_GEN=""
JOB_FOUNDRY=""
JOB_CURC_DS=""
JOB_CURC_Q72=""
JOB_CURC_Q32=""
JOB_ANALYSIS_A=""
JOB_B1_DS=""
JOB_B1_Q72=""
JOB_B1_Q32=""
JOB_SFT_DATA=""
JOB_DEBATE=""
declare -a JOB_TRAIN_ALL=()
declare -a JOB_EVAL_ALL=()

# =========================================================================
# PHASE A: BASE EVALUATION
# =========================================================================

# ---------------------------------------------------------------------------
# A0: Instance Generation
# ---------------------------------------------------------------------------
if should_run_phase "A0" && [ "$SKIP_INSTANCES" != "true" ]; then
    echo "=== Phase A0: Instance Generation ==="
    JOB_GEN=$(submit "Instance Generation" \
        hpc/slurm_generate_instances.sh)
    echo ""
fi

# Dependency for downstream phases
GEN_DEP=$(dep_flag "$JOB_GEN")

# ---------------------------------------------------------------------------
# A1: Symbolic Baseline
# ---------------------------------------------------------------------------
if should_run_phase "A1"; then
    echo "=== Phase A1: Symbolic Baseline ==="
    JOB_SYM=$(submit "Symbolic Baseline" \
        ${GEN_DEP:+$GEN_DEP} \
        --job-name="defab_symbolic" \
        --export=ALL,SKIP_DECODER=true,RESULTS_DIR=experiments/results \
        hpc/slurm_analysis.sh)
    echo ""
fi

# ---------------------------------------------------------------------------
# A2: Foundry Evaluation (4 closed-source models)
# ---------------------------------------------------------------------------
if should_run_phase "A2" && [ "$SKIP_FOUNDRY" != "true" ]; then
    echo "=== Phase A2: Foundry Evaluation ==="
    JOB_FOUNDRY=$(submit "Foundry Eval (GPT-5.2, Kimi, Claude, DeepSeek-R1)" \
        ${GEN_DEP:+$GEN_DEP} \
        --export=ALL,INSTANCE_LIMIT=${INSTANCE_LIMIT},LEVEL3_LIMIT=${LEVEL3_LIMIT},MODALITIES="${MODALITIES}",STRATEGIES="${STRATEGIES}" \
        hpc/slurm_evaluate_foundry.sh)
    echo ""
elif should_run_phase "A2"; then
    echo "=== Phase A2: Foundry Evaluation (SKIPPED) ==="
    echo ""
fi

# ---------------------------------------------------------------------------
# A3: CURC Open-Source Base Evaluation (3 models via vLLM)
# ---------------------------------------------------------------------------
if should_run_phase "A3" && [ "$SKIP_CURC_BASE" != "true" ]; then
    echo "=== Phase A3: CURC Open-Source Base Evaluation ==="

    JOB_CURC_DS=$(submit "CURC Eval: DeepSeek-R1-70B" \
        ${GEN_DEP:+$GEN_DEP} \
        --export=ALL,VLLM_MODEL=${MODEL_DS},INSTANCE_LIMIT=${INSTANCE_LIMIT},LEVEL3_LIMIT=${LEVEL3_LIMIT},MODALITIES="${MODALITIES}",STRATEGIES="${STRATEGIES}" \
        hpc/slurm_evaluate_curc_vllm.sh)

    JOB_CURC_Q72=$(submit "CURC Eval: Qwen 72B" \
        ${GEN_DEP:+$GEN_DEP} \
        --export=ALL,VLLM_MODEL=${MODEL_Q72},INSTANCE_LIMIT=${INSTANCE_LIMIT},LEVEL3_LIMIT=${LEVEL3_LIMIT},MODALITIES="${MODALITIES}",STRATEGIES="${STRATEGIES}" \
        hpc/slurm_evaluate_curc_vllm.sh)

    JOB_CURC_Q32=$(submit "CURC Eval: Qwen 32B" \
        ${GEN_DEP:+$GEN_DEP} \
        --export=ALL,VLLM_MODEL=${MODEL_Q32},INSTANCE_LIMIT=${INSTANCE_LIMIT},LEVEL3_LIMIT=${LEVEL3_LIMIT},MODALITIES="${MODALITIES}",STRATEGIES="${STRATEGIES}" \
        hpc/slurm_evaluate_curc_vllm.sh)

    echo ""
elif should_run_phase "A3"; then
    echo "=== Phase A3: CURC Base Evaluation (SKIPPED) ==="
    echo ""
fi

# ---------------------------------------------------------------------------
# A4: Analysis Pipeline (depends on A2 + A3)
# ---------------------------------------------------------------------------
if should_run_phase "A4"; then
    echo "=== Phase A4: Phase A Analysis Pipeline ==="
    A4_DEP=$(multi_dep_flag "$JOB_FOUNDRY" "$JOB_CURC_DS" "$JOB_CURC_Q72" "$JOB_CURC_Q32")
    JOB_ANALYSIS_A=$(submit "Phase A Analysis (Tables 1-3)" \
        ${A4_DEP:+$A4_DEP} \
        --export=ALL,RESULTS_DIR=experiments/results,OUTPUT_DIR=paper/tables \
        hpc/slurm_analysis.sh)
    echo ""
fi


# =========================================================================
# PHASE B: FINE-TUNING
# =========================================================================

# ---------------------------------------------------------------------------
# B0: SFT Data Preparation
# ---------------------------------------------------------------------------
if should_run_phase "B0"; then
    echo "=== Phase B0: SFT Data Preparation ==="
    JOB_SFT_DATA=$(submit "SFT Data Prep" \
        ${GEN_DEP:+$GEN_DEP} \
        --job-name="defab_sft_data" \
        --partition=amilan \
        --time=01:00:00 \
        --mem=16G \
        --cpus-per-task=4 \
        --output=logs/sft_data_%j.out \
        --error=logs/sft_data_%j.err \
        --wrap="cd $PROJ_DIR && module load python/3.11 && source venv/bin/activate && pip install -q -r requirements.txt && export PYTHONPATH=${PROJ_DIR}/src:${PROJ_DIR}/experiments:${PROJ_DIR}/examples:\${PYTHONPATH:-} && python experiments/finetuning/prepare_sft_data.py --modalities M4 --strategies direct --output-dir experiments/finetuning/data/")
    echo ""
fi

# ---------------------------------------------------------------------------
# B1: Response Sampling (3 models, prerequisite for DPO/RLHF)
# ---------------------------------------------------------------------------
if should_run_phase "B1"; then
    echo "=== Phase B1: Response Sampling ==="

    JOB_B1_Q32=$(submit "B1 Sample: Qwen-32B" \
        ${GEN_DEP:+$GEN_DEP} \
        --export=ALL,VLLM_MODEL="${MODEL_Q32}" \
        hpc/slurm_sample_responses.sh)

    JOB_B1_Q72=$(submit "B1 Sample: Qwen-72B (TP=2)" \
        ${GEN_DEP:+$GEN_DEP} \
        --gres=gpu:2 \
        --export=ALL,VLLM_MODEL="${MODEL_Q72}",TP_SIZE=2 \
        hpc/slurm_sample_responses.sh)

    JOB_B1_DS=$(submit "B1 Sample: DeepSeek-R1-70B (TP=2)" \
        ${GEN_DEP:+$GEN_DEP} \
        --gres=gpu:2 \
        --export=ALL,VLLM_MODEL="${MODEL_DS}",TP_SIZE=2 \
        hpc/slurm_sample_responses.sh)

    echo ""
fi

B1_DEP=$(multi_dep_flag "$JOB_B1_Q32" "$JOB_B1_Q72" "$JOB_B1_DS")
SFT_DATA_DEP=$(dep_flag "$JOB_SFT_DATA")

# ---------------------------------------------------------------------------
# BS: SFT Training (3 models x joint curriculum, depends on B0)
# ---------------------------------------------------------------------------
if should_run_phase "BS"; then
    echo "=== Phase BS: SFT Training ==="
    for MODEL in "${MODELS[@]}"; do
        MODEL_SLUG=$(echo "$MODEL" | tr '/' '_' | tr ':' '_')
        JID=$(submit "SFT: $MODEL_SLUG" \
            ${SFT_DATA_DEP:+$SFT_DATA_DEP} \
            --job-name="sft_joint_${MODEL_SLUG}" \
            --export=ALL,BASE_MODEL="$MODEL",CURRICULUM=joint \
            hpc/slurm_train_sft.sh)
        JOB_TRAIN_ALL+=("$JID")
    done
    echo ""
fi

# ---------------------------------------------------------------------------
# B2: DPO Training (depends on B1)
# ---------------------------------------------------------------------------
if should_run_phase "B2"; then
    echo "=== Phase B2: DPO Training ==="

    declare -a DPO_VARIANTS=("standard" "margin")
    declare -a DPO_CURRICULA=("joint" "weighted")

    # 12 standard DPO jobs: 3 models x 2 variants x 2 curricula
    for MODEL in "${MODELS[@]}"; do
        MODEL_SLUG=$(echo "$MODEL" | tr '/' '_' | tr ':' '_')
        for VARIANT in "${DPO_VARIANTS[@]}"; do
            for CURRICULUM in "${DPO_CURRICULA[@]}"; do
                JID=$(submit "DPO ${VARIANT} ${CURRICULUM}: ${MODEL_SLUG}" \
                    ${B1_DEP:+$B1_DEP} \
                    --job-name="dpo_${VARIANT}_${CURRICULUM}_${MODEL_SLUG}" \
                    --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT="$VARIANT",CURRICULUM="$CURRICULUM" \
                    hpc/slurm_train_dpo.sh)
                JOB_TRAIN_ALL+=("$JID")
            done
        done
    done

    # 3 sequential curriculum DPO jobs (margin variant)
    for MODEL in "${MODELS[@]}"; do
        MODEL_SLUG=$(echo "$MODEL" | tr '/' '_' | tr ':' '_')
        JID=$(submit "DPO margin sequential: ${MODEL_SLUG}" \
            ${B1_DEP:+$B1_DEP} \
            --job-name="dpo_margin_sequential_${MODEL_SLUG}" \
            --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=sequential \
            hpc/slurm_train_dpo.sh)
        JOB_TRAIN_ALL+=("$JID")
    done

    # 1 l12_only ablation (Qwen-72B, tests Conjecture 3)
    JID=$(submit "DPO margin l12_only: Qwen-72B" \
        ${B1_DEP:+$B1_DEP} \
        --job-name="dpo_margin_l12only_qwen72" \
        --export=ALL,BASE_MODEL="${MODEL_Q72}",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=l12_only \
        hpc/slurm_train_dpo.sh)
    JOB_TRAIN_ALL+=("$JID")

    # 3 gamma sweep (Qwen-72B only)
    for G in 0.5 1.0 4.0; do
        JID=$(submit "DPO margin gamma=${G}: Qwen-72B" \
            ${B1_DEP:+$B1_DEP} \
            --job-name="dpo_margin_g${G}_qwen72" \
            --export=ALL,BASE_MODEL="${MODEL_Q72}",DPO_VARIANT=margin,GAMMA=$G,CURRICULUM=joint \
            hpc/slurm_train_dpo.sh)
        JOB_TRAIN_ALL+=("$JID")
    done

    echo ""
fi

# ---------------------------------------------------------------------------
# B3: RLHF/VITL Training (depends on B1)
# ---------------------------------------------------------------------------
if should_run_phase "B3"; then
    echo "=== Phase B3: RLHF/VITL Training ==="

    # VITL for all 3 models
    for MODEL in "${MODELS[@]}"; do
        MODEL_SLUG=$(echo "$MODEL" | tr '/' '_' | tr ':' '_')
        JID=$(submit "RLHF VITL: ${MODEL_SLUG}" \
            ${B1_DEP:+$B1_DEP} \
            --job-name="rlhf_vitl_${MODEL_SLUG}" \
            --export=ALL,BASE_MODEL="$MODEL",RLHF_MODE=vitl,CURRICULUM=joint \
            hpc/slurm_train_rlhf.sh)
        JOB_TRAIN_ALL+=("$JID")
    done

    # Standard reward-model RLHF for Qwen-72B only (control)
    JID=$(submit "RLHF RM: Qwen-72B" \
        ${B1_DEP:+$B1_DEP} \
        --job-name="rlhf_rm_qwen72b" \
        --export=ALL,BASE_MODEL="${MODEL_Q72}",RLHF_MODE=reward-model,CURRICULUM=joint \
        hpc/slurm_train_rlhf.sh)
    JOB_TRAIN_ALL+=("$JID")

    echo ""
fi

# ---------------------------------------------------------------------------
# BG: GRPO/RLVR Training (3 models, depends on instances)
# ---------------------------------------------------------------------------
if should_run_phase "BG"; then
    echo "=== Phase BG: GRPO/RLVR Training ==="

    for MODEL in "${MODELS[@]}"; do
        MODEL_SLUG=$(echo "$MODEL" | tr '/' '_' | tr ':' '_')
        JID=$(submit "GRPO: ${MODEL_SLUG}" \
            ${GEN_DEP:+$GEN_DEP} \
            --job-name="grpo_joint_${MODEL_SLUG}" \
            --export=ALL,BASE_MODEL="$MODEL",CURRICULUM=joint \
            hpc/slurm_train_grpo.sh)
        JOB_TRAIN_ALL+=("$JID")
    done

    echo ""
fi

# ---------------------------------------------------------------------------
# B5: Evaluate All Fine-Tuned Checkpoints (depends on all training)
# ---------------------------------------------------------------------------
if should_run_phase "B5"; then
    echo "=== Phase B5: Evaluate Fine-Tuned Checkpoints ==="

    if [ ${#JOB_TRAIN_ALL[@]} -gt 0 ] && [ "$DRY_RUN" != "true" ]; then
        TRAIN_DEP=$(IFS=:; echo "${JOB_TRAIN_ALL[*]}")
        TRAIN_DEP_FLAG="--dependency=afterok:${TRAIN_DEP}"
    else
        TRAIN_DEP_FLAG=""
    fi

    # Submit a coordinator job that runs submit_eval_finetuned_all.sh
    # after all training completes
    JOB_B5=$(submit "B5 Checkpoint Eval Coordinator" \
        ${TRAIN_DEP_FLAG:+$TRAIN_DEP_FLAG} \
        --job-name="defab_eval_ft_coord" \
        --partition=amilan \
        --time=00:30:00 \
        --mem=4G \
        --cpus-per-task=1 \
        --output=logs/eval_ft_coord_%j.out \
        --error=logs/eval_ft_coord_%j.err \
        --wrap="cd $PROJ_DIR && bash hpc/submit_eval_finetuned_all.sh")

    echo ""
fi

# ---------------------------------------------------------------------------
# B6: Fine-Tuning Analysis (depends on B5 evals completing)
# ---------------------------------------------------------------------------
if should_run_phase "B6"; then
    echo "=== Phase B6: Fine-Tuning Analysis ==="
    echo "  NOTE: B6 analysis should be run manually after all B5 eval jobs finish."
    echo "  B5 spawns sub-jobs dynamically, so static SLURM dependencies are insufficient."
    echo ""
    echo "  When ready, run:"
    echo "    sbatch hpc/slurm_ft_analysis.sh"
    echo "  Or directly:"
    echo "    python experiments/finetuning/generate_ft_tables.py --results-dir experiments/results/"
    echo "    python experiments/finetuning/analyze_ft_lift.py --results-dir experiments/results/"
    echo ""
fi


# =========================================================================
# PHASE C: ADVERSARIAL DEBATE
# =========================================================================

if should_run_phase "C" && [ "$SKIP_DEBATE" != "true" ]; then
    echo "=== Phase C: Adversarial Defeasible Debate ==="
    JOB_DEBATE=$(submit "Debate Experiments" \
        ${GEN_DEP:+$GEN_DEP} \
        --export=ALL,DEBATE_KBS=all,DEBATE_ROUNDS=3,MCTS_ITERATIONS=200 \
        hpc/slurm_debate.sh)
    echo ""
elif should_run_phase "C"; then
    echo "=== Phase C: Debate (SKIPPED) ==="
    echo ""
fi


# =========================================================================
# SUMMARY
# =========================================================================

echo "======================================================================="
echo "DeFAb Comprehensive Experiment Runner -- Submission Complete"
echo "======================================================================="
echo "End      : $(date)"
echo "Jobs     : $TOTAL_SUBMITTED submitted, $TOTAL_SKIPPED skipped/dry-run"
echo ""
echo "Paper deliverables from this pipeline:"
echo ""
echo "  PHASE A (Base Evaluation):"
echo "    Table 1  main accuracy         <- generate_paper_tables.py"
echo "    Table 2  modality breakdown    <- generate_paper_tables.py"
echo "    Table 3  domain breakdown      <- generate_paper_tables.py"
echo ""
echo "  PHASE B (Fine-Tuning):"
echo "    Table 4  ft main results       <- generate_ft_tables.py"
echo "    Table 5  curriculum comparison  <- generate_ft_tables.py"
echo "    Table 6  error taxonomy shift   <- generate_ft_tables.py"
echo "    Conjectures 1-6                 <- analyze_*.py scripts"
echo ""
echo "  PHASE C (Debate):"
echo "    Table 7  debate robustness     <- analyze_debate.py"
echo "    Table 8  grounding+creativity  <- analyze_debate.py"
echo "    Table 9  winner distribution   <- analyze_debate.py"
echo ""
echo "Monitor all jobs:"
echo "  squeue -u \$USER"
echo ""
echo "After all Phase B5 eval jobs finish, run B6 analysis manually:"
echo "  sbatch hpc/slurm_ft_analysis.sh"
echo ""
echo "After all phases complete, verify all tables exist:"
echo "  ls paper/tables/table*.tex"
echo "======================================================================="
