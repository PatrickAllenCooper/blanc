"""
Phase B6: Reward Model Fidelity Analysis (Section 6.8).

Measures the Spearman rank correlation between the Bradley-Terry reward model
R_phi and the exact DeFAb verifier score S_defab on held-out (prompt, response)
pairs.

High correlation (rho >= 0.8) indicates that the learned reward model is a
faithful proxy for the formal verifier, justifying its use in standard RLHF.
Low correlation indicates reward model approximation error that VITL avoids.

The analysis uses the preference data JSONL (from prepare_preference_data.py),
which contains both the model responses and their verifier scores (score_chosen
and score_rejected fields).

Usage:
  python experiments/finetuning/analyze_reward_fidelity.py \\
      --reward-model experiments/finetuning/checkpoints/rlhf_reward-model_joint_Qwen_Qwen2.5-72B-Instruct-AWQ/reward_model_final \\
      --preference-data experiments/finetuning/data/preferences_Qwen_Qwen2.5-72B-Instruct-AWQ.jsonl \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def _load_preference_pairs(jsonl_path: Path) -> list[dict]:
    """Load preference JSONL and return all records with verifier scores."""
    records = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            # Only keep records with individual scores (from prepare_preference_data.py)
            if "score_chosen" in rec and "score_rejected" in rec:
                records.append(rec)
    return records


def _score_with_reward_model(
    reward_model_path: str,
    prompts: list[str],
    responses: list[str],
    batch_size: int = 8,
) -> list[float]:
    """Score (prompt, response) pairs using the reward model."""
    import torch
    from transformers import pipeline

    print(f"  Loading reward model from {reward_model_path}...")
    device = 0 if __import__("torch").cuda.is_available() else -1
    pipe = pipeline(
        "text-classification",
        model=reward_model_path,
        device=device,
        truncation=True,
        max_length=1024,
    )

    scores = []
    for i in range(0, len(prompts), batch_size):
        batch_prompts   = prompts[i : i + batch_size]
        batch_responses = responses[i : i + batch_size]
        inputs = [f"{p}\n{r}" for p, r in zip(batch_prompts, batch_responses)]
        results = pipe(inputs, batch_size=batch_size)
        scores.extend(float(r["score"]) for r in results)
        if (i // batch_size) % 10 == 0:
            pct = 100 * i / len(prompts)
            print(f"  Scored {i}/{len(prompts)} ({pct:.0f}%)")

    return scores


def _spearman_rho(x: list[float], y: list[float]) -> tuple[float, float]:
    """Spearman rank correlation and p-value."""
    try:
        from scipy.stats import spearmanr
        rho, p = spearmanr(x, y)
        return float(rho), float(p)
    except ImportError:
        # Manual rank correlation
        n = len(x)
        rank_x = sorted(range(n), key=lambda i: x[i])
        rank_y = sorted(range(n), key=lambda i: y[i])
        rx = [0.0] * n
        ry = [0.0] * n
        for rank, idx in enumerate(rank_x):
            rx[idx] = rank
        for rank, idx in enumerate(rank_y):
            ry[idx] = rank
        mean_rx = sum(rx) / n
        mean_ry = sum(ry) / n
        num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
        den = (sum((rx[i] - mean_rx)**2 for i in range(n)) *
               sum((ry[i] - mean_ry)**2 for i in range(n))) ** 0.5
        rho = num / den if den > 0 else float("nan")
        return rho, float("nan")


def main() -> int:
    p = argparse.ArgumentParser(description="Reward model fidelity (Spearman rho, Section 6.8).")
    p.add_argument("--reward-model",     required=True,
                   help="Path to the trained reward model checkpoint.")
    p.add_argument("--preference-data",  required=True,
                   help="Path to preferences_*.jsonl from prepare_preference_data.py.")
    p.add_argument("--base-model",       default=None,
                   help="Base model HF ID (for tokenizer, if needed).")
    p.add_argument("--sample",           type=int, default=500,
                   help="Max number of (prompt, response) pairs to score (default 500).")
    p.add_argument("--batch-size",       type=int, default=8)
    args = p.parse_args()

    reward_model_path = args.reward_model
    preference_path   = Path(args.preference_data)

    if not Path(reward_model_path).exists():
        print(f"ERROR: Reward model not found: {reward_model_path}")
        print("Train a reward model first:")
        print("  sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-72B-Instruct-AWQ',"
              "RLHF_MODE=reward-model hpc/slurm_train_rlhf.sh")
        return 1

    if not preference_path.exists():
        print(f"ERROR: Preference data not found: {preference_path}")
        print("Run prepare_preference_data.py first.")
        return 1

    # Load pairs with verifier scores
    print(f"Loading preference pairs from {preference_path}...")
    records = _load_preference_pairs(preference_path)
    if not records:
        print("No records with individual verifier scores found.")
        print("Ensure prepare_preference_data.py wrote score_chosen/score_rejected fields.")
        return 1

    print(f"Loaded {len(records)} preference pairs with verifier scores.")

    # Deduplicate to unique (prompt, response, score) triples
    seen: set = set()
    prompts_all: list[str]  = []
    responses_all: list[str] = []
    verifier_scores: list[float] = []

    for rec in records:
        for response_key, score_key in [("chosen", "score_chosen"), ("rejected", "score_rejected")]:
            key = (rec["prompt"][:100], rec[response_key][:100])
            if key not in seen:
                seen.add(key)
                prompts_all.append(rec["prompt"])
                responses_all.append(rec[response_key])
                verifier_scores.append(float(rec[score_key]))

    # Sample if needed
    import random
    if len(prompts_all) > args.sample:
        rng     = random.Random(42)
        indices = rng.sample(range(len(prompts_all)), args.sample)
        prompts_all      = [prompts_all[i]      for i in indices]
        responses_all    = [responses_all[i]    for i in indices]
        verifier_scores  = [verifier_scores[i]  for i in indices]
        print(f"Sampled {args.sample} pairs for scoring.")

    print(f"\nScoring {len(prompts_all)} responses with reward model...")
    rm_scores = _score_with_reward_model(
        reward_model_path,
        prompts_all,
        responses_all,
        batch_size=args.batch_size,
    )

    # Compute Spearman rho
    rho, p_val = _spearman_rho(verifier_scores, rm_scores)
    p_str = f"{p_val:.4f}" if p_val == p_val else "---"

    print("\n" + "=" * 72)
    print("Reward Model Fidelity (Section 6.8)")
    print("=" * 72)
    print(f"  Spearman rho(R_phi, S_defab) = {rho:.4f}  (p = {p_str})")
    print(f"  n = {len(verifier_scores)}")

    # Score distribution comparison
    v_mean = sum(verifier_scores) / len(verifier_scores)
    r_mean = sum(rm_scores) / len(rm_scores)
    print(f"\n  Verifier scores: mean={v_mean:.3f}, "
          f"min={min(verifier_scores):.3f}, max={max(verifier_scores):.3f}")
    print(f"  Reward model:   mean={r_mean:.3f}, "
          f"min={min(rm_scores):.3f}, max={max(rm_scores):.3f}")

    # Interpretation
    if rho >= 0.8:
        interp = "HIGH -- reward model is a faithful proxy for the verifier."
    elif rho >= 0.6:
        interp = "MODERATE -- acceptable proxy; some approximation error present."
    elif rho >= 0.4:
        interp = "LOW -- significant reward model approximation error; prefer VITL."
    else:
        interp = "VERY LOW -- reward model does not track verifier; VITL strongly preferred."
    print(f"\n  Interpretation: {interp}")

    # Save results
    out_path = Path(reward_model_path) / "fidelity_analysis.json"
    with open(out_path, "w") as f:
        json.dump({"spearman_rho": rho, "p_value": p_val, "n": len(verifier_scores),
                   "verifier_mean": v_mean, "rm_mean": r_mean}, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
