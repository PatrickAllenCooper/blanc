# Azure Dual-A100 Fine-Tuning Guide

This guide covers running the full DeFAb fine-tuning pipeline on an Azure NC_A100_v4 instance (2x A100 80 GB) or equivalent dual-A100 machine.

Two scripts are provided:

| Script | Use case |
|--------|----------|
| `scripts/azure_finetune.sh` | Manual runs on a persistent VM, no auto-resume |
| `scripts/azure_finetune_spot.sh` | Spot VM with automatic resume across deallocations |

---

## Spot VM Setup (Recommended -- Cheapest)

Azure Spot VMs can be deallocated at any time but cost 60--90% less. The `azure_finetune_spot.sh` script handles this with a defense-in-depth hardening stack:

1. **Atomic state file** (`/data/defab_results/.finetune_state.json`) with `flock` + `tmp+rename+fsync`: the record of completed steps survives crashes mid-write.
2. **Artifact-verified completion**: a step is marked done only after its declared output (a `final/` adapter or a non-empty `summary.json`) is present on disk. Silent exits no longer create phantom completions.
3. **Boot-time state reconciliation** (`scripts/verify_and_repair_state.py`): every boot begins by walking the state file, dropping any entry whose artifact is missing, and then resuming from the first truly incomplete step.
4. **Frequent checkpoints** (`save_steps=10`, `save_total_limit=3`): with the observed dual-A100 step times (Qwen-72B QLoRA ~58 s/step for DPO, Qwen-32B QLoRA ~25 s/step for SFT) this bounds the work lost to a single Spot eviction at ~10 minutes. LoRA adapter + Adam state checkpoints are ~5 GB each, written to NVMe in ~2 seconds; disk pressure is bounded by `save_total_limit`. The first deployment used `save_steps=25` and lost a full 24 minutes of DPO progress on the first real Spot preemption (Apr 20, step 24 of 240, no checkpoint had been written yet).
5. **`warmup_ratio` instead of fixed `warmup_steps`**: short runs (~54 steps) no longer spend their entire budget in warmup.
6. **Azure IMDS ScheduledEvents poller** (`scripts/azure_spot_preemption_poller.sh`): a background child polls `http://169.254.169.254/metadata/scheduledevents` every 5 seconds and signals the orchestrator *before* the OS SIGTERM arrives.
7. **Signal propagation**: SIGTERM is fanned out to every tracked child (`torchrun` ranks, vLLM server, data-prep subprocesses) via `spawn_to`, which uses process substitution instead of a pipeline so the real child PID remains visible to the trap. systemd's `KillMode=mixed` covers anything we forget.
8. **Pre-download step**: model shards (Qwen 32B ~65 GB, Qwen 72B ~145 GB, DeepSeek ~140 GB) are fetched with `huggingface_hub.snapshot_download(resume_download=True)` into the persistent `/data/hf_cache` *before* training begins. Eviction mid-download no longer wastes hours.
9. **Pre-flight checks**: before each GPU-bound step we confirm at least 50 GB free under `$RESULTS_BASE` and log stale CUDA processes. Before each `predownload_*` step we additionally check that `$HF_HOME` has enough room to finish the remaining shard bytes (Qwen 72B ~170 GB, Qwen 32B ~80 GB padded), and emit a clear error with remediation hints if not. Size floors are configurable via `MIN_FREE_GB`, `PREDOWNLOAD_SIZE_GB_qwen72`, and `PREDOWNLOAD_SIZE_GB_qwen32` env vars.
10. **Stall watchdog** (`defab_watchdog.service`): if no `train.log` under `$RESULTS_BASE` is modified for 15 minutes while the main service is active, the watchdog restarts the service to break silent hangs (tokenizer download stalls, deadlocked NCCL collectives, etc.). Capped at six restarts per boot so a deterministic failure is not looped on forever.

### One-Time Setup on a Fresh Azure VM

```bash
git clone https://github.com/anonymous-authors/defab.git /home/azureuser/blanc
cd /home/azureuser/blanc

sudo mkdir -p /data/hf_cache /data/defab_results
sudo chown -R azureuser:azureuser /data

sudo mkdir -p /etc/defab && sudo chmod 700 /etc/defab
echo 'HF_TOKEN=hf_...' | sudo tee /etc/defab/secrets >/dev/null
sudo chmod 600 /etc/defab/secrets

sudo install -m 755 scripts/azure_finetune_spot.sh        /usr/local/bin/defab_finetune
sudo install -m 755 scripts/azure_spot_preemption_poller.sh /usr/local/bin/defab_preempt_poller
sudo install -m 755 scripts/defab_watchdog.sh             /usr/local/bin/defab_watchdog

sudo cp scripts/defab_finetune.service /etc/systemd/system/
sudo cp scripts/defab_watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now defab_finetune defab_watchdog
```

### Upgrading an Existing VM

If the VM already has an older version of the orchestrator running:

```bash
cd /home/azureuser/blanc
git pull

sudo systemctl stop defab_finetune
sudo install -m 755 scripts/azure_finetune_spot.sh        /usr/local/bin/defab_finetune
sudo install -m 755 scripts/azure_spot_preemption_poller.sh /usr/local/bin/defab_preempt_poller
sudo install -m 755 scripts/defab_watchdog.sh             /usr/local/bin/defab_watchdog
sudo cp scripts/defab_finetune.service /etc/systemd/system/
sudo cp scripts/defab_watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload

# Audit the state file before restarting so phantom completions are removed.
python3 scripts/verify_and_repair_state.py \
    --state /data/defab_results/.finetune_state.json \
    --results-base /data/defab_results \
    --repo-dir /home/azureuser/blanc \
    --report

# If the report looks right, apply the repair (drop --report) and restart.
python3 scripts/verify_and_repair_state.py \
    --state /data/defab_results/.finetune_state.json \
    --results-base /data/defab_results \
    --repo-dir /home/azureuser/blanc

sudo systemctl enable --now defab_finetune defab_watchdog
```

### Monitoring

```bash
# Live log stream
journalctl -u defab_finetune -f

# Check current state (what has been completed)
cat /data/defab_results/.finetune_state.json

# Check if still running
systemctl status defab_finetune
```

### What Happens on Deallocation and Restart

1. The IMDS poller sees a `Preempt` event and sends SIGTERM to the orchestrator (typically 5--30 seconds before the OS SIGTERM).
2. The orchestrator's trap fans SIGTERM out to every tracked child: `torchrun` ranks flush their in-flight checkpoint, the vLLM server shuts down cleanly, and `spawn_to`-launched subprocesses wind down.
3. The orchestrator exits with code 0; the state file is already flushed (atomic write on every `state_mark_done`).
4. Azure deallocates the VM. When it comes back, systemd starts `defab_finetune` via `multi-user.target`.
5. The orchestrator first runs `verify_and_repair_state.py`, which walks the state file and drops any entry whose artifact is absent. Then it resumes from the first truly incomplete step; if that step already has a `checkpoint-N/` directory, HuggingFace Trainer picks up from there.
6. The watchdog (`defab_watchdog.service`) runs alongside the main service on every boot and restarts it if training output stalls for longer than 15 minutes.

### Resetting State (Start Over)

```bash
rm /data/defab_results/.finetune_state.json
sudo systemctl restart defab_finetune
```

To reset only a specific step (e.g. re-run SFT for qwen32):
```bash
python3 -c "
import json
state = json.load(open('/data/defab_results/.finetune_state.json'))
state['completed'].remove('sft_qwen32')
json.dump(state, open('/data/defab_results/.finetune_state.json', 'w'), indent=2)
"
sudo systemctl restart defab_finetune
```

---

- Azure VM with 2x A100 80 GB GPUs (e.g. Standard_NC48ads_A100_v4)
- **At least 350 GB free on `/data`** (the mount holding `HF_HOME` and `RESULTS_BASE`). Sizing breakdown: Qwen 72B shards ~145 GB, Qwen 32B shards ~65 GB, LoRA checkpoints across five methods and two models ~45 GB, data prep + eval outputs + scratch ~20 GB, plus ~75 GB headroom for transient writes and future models. If `/data` is the OS disk only, attach an NVMe data disk and bind `HF_HOME` and `RESULTS_BASE` to it.
- Ubuntu 22.04, CUDA 12.x, Python 3.11+
- HuggingFace account with access to `PatrickAllenCooper/DeFAb`
- GitHub access to the blanc repository

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/anonymous-authors/defab.git
cd blanc

# Set your HuggingFace token (for the private DeFAb dataset)
export HF_TOKEN=<your-token>

# Run everything: setup, data download, all 4 methods, all 3 models
bash scripts/azure_finetune.sh
```

Results are written to `results/finetune/`.

---

## What the Script Does

### Phase 0: Environment Setup

Installs all Python dependencies (torch, transformers, trl, peft, bitsandbytes, vllm, deepspeed) and the blanc package.

### Phase 1: Dataset Download

Downloads the DeFAb dataset from `PatrickAllenCooper/DeFAb` on HuggingFace into the `instances/` directory.

### Phase 2: Data Preparation (per model)

1. **SFT data** (`prepare_sft_data.py`): Creates gold demonstration pairs from DeFAb instances (modalities M4+M2, direct prompting). Output: `experiments/finetuning/data/sft_train.jsonl` and `sft_val.jsonl`.

2. **Preference data** (`prepare_preference_data.py`): Starts a vLLM server on GPU 0, samples 16 responses per instance at temperature 0.7, scores each response with the DeFAb verifier, and extracts preference pairs with margin >= 0.25. Output: `experiments/finetuning/data/preferences_{model}.jsonl`.

### Phase 3: Training (4 methods per model)

All training uses LoRA rank 64, alpha 128 on attention and MLP projections. 4-bit AWQ quantization for all models.

| Method | Key hyperparameters | GPU config |
|--------|---------------------|------------|
| SFT | LR 2e-5, 3 epochs, effective batch 32 | 2 GPUs + ZeRO-2 |
| DPO (standard) | beta=0.1, LR 5e-6, 3 epochs | 2 GPUs + ZeRO-2 |
| DPO (margin) | same + gamma=2.0 margin weighting | 2 GPUs + ZeRO-2 |
| GRPO | LR 5e-7, G=8, KL beta=0.04, verifier reward | 2 GPUs + vLLM |
| RLHF/VITL | PPO, KL=0.05, LR 1e-6, exact verifier reward | 1 GPU (PPO limitation) |

### Phase 4: Evaluation

Evaluates each checkpoint on the test split using the same 4-modality protocol as the base model evaluation. Reports fine-tuning lift (delta_FT) per method and model.

---

## Models

| Slug | Model ID | VRAM (4-bit) |
|------|----------|--------------|
| qwen72 | Qwen/Qwen2.5-72B-Instruct-AWQ | ~36 GB |
| qwen32 | Qwen/Qwen2.5-32B-Instruct-AWQ | ~16 GB |
| deepseek | casperhansen/deepseek-r1-distill-llama-70b-awq | ~35 GB |

All models fit on a single A100 80 GB in 4-bit. ZeRO-2 shards optimizer states across 2 GPUs to reduce per-GPU memory for gradient updates.

---

## Partial Runs

Run a single model:
```bash
bash scripts/azure_finetune.sh --model qwen32
```

Run a single method on a single model:
```bash
bash scripts/azure_finetune.sh --model qwen32 --method sft
```

Skip environment setup if already installed:
```bash
bash scripts/azure_finetune.sh --skip-setup
```

Skip data preparation if already done:
```bash
bash scripts/azure_finetune.sh --skip-data
```

---

## Output Structure

```
results/finetune/
  sft/{model}/            # SFT checkpoints
  dpo_standard/{model}/   # DPO standard checkpoints
  dpo_margin/{model}/     # DPO margin-weighted checkpoints
  grpo/{model}/           # GRPO checkpoints
  rlhf_vitl/{model}/      # RLHF/VITL checkpoints
  eval/{model}/           # Evaluation results per method

experiments/finetuning/data/
  sft_train.jsonl         # Gold SFT training examples
  sft_val.jsonl           # Gold SFT validation examples
  preferences_{model}.jsonl  # Preference pairs per model
  splits.json             # Train/val/test instance splits
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| HF_TOKEN | (none) | HuggingFace token for private dataset access |
| HF_HOME | /tmp/hf_cache | HuggingFace model/dataset cache directory |
| VLLM_PORT | 8200 | Port for vLLM server during preference sampling |
| REPO_DIR | (auto-detected) | Root of the blanc repository |

---

## Time Estimates on 2x A100 80 GB

| Step | Approximate time |
|------|-----------------|
| Environment setup | 10--15 min |
| Dataset download | 5--10 min |
| Preference sampling (per model, 409 instances x 16 samples) | 2--4 hours |
| SFT training (per model) | 1--2 hours |
| DPO training x 2 variants (per model) | 2--4 hours |
| GRPO training (per model) | 3--6 hours |
| RLHF/VITL training (per model, 1 GPU) | 2--4 hours |
| Evaluation (per model) | 30--60 min |
| **Total (3 models, all methods)** | **~48--72 hours** |

Use `--model qwen32 --skip-setup` for a faster first run (~12 hours for the smallest model).
