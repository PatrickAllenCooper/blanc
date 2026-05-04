"""
Phase B6: Reward Overoptimization Diagnostic (Section 6.8).

Measures the gap between the reward model's mean score R_phi and the DeFAb
verifier's mean score S_defab at the final PPO checkpoint.

A large positive gap (R_phi >> S_defab) indicates reward hacking: the policy
has learned to produce responses that exploit the reward model's weaknesses
without actually improving formal defeasible reasoning quality.

This diagnostic motivates VITL: using the exact verifier as the reward signal
eliminates the gap by construction.

Two sources of data are supported:
  1. Evaluation results from evaluate_finetuned.py (provides verifier scores).
  2. Reward model scored responses (optional, from analyze_reward_fidelity.py).
  3. Training log stats from train_rlhf_vitl.py output dir (reward_stats.json).

Usage:
  python experiments/finetuning/analyze_reward_overoptimization.py \\
      --rlhf-checkpoint experiments/finetuning/checkpoints/rlhf_reward-model_joint_Qwen_Qwen2.5-72B-Instruct-AWQ \\
      --reward-model   experiments/finetuning/checkpoints/rlhf_reward-model_joint_Qwen_Qwen2.5-72B-Instruct-AWQ/reward_model_final \\
      --results-dir    experiments/results/ \\
      --instances-dir  instances/

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def _load_result_file(path: Path) -> tuple[list[dict], dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    return data.get("evaluations", []), data.get("metadata", {})


def _load_all_results(results_dir: Path) -> list[tuple[list[dict], dict]]:
    results = []
    for path in sorted(results_dir.rglob("*.json")):
        try:
            evals, meta = _load_result_file(path)
            if evals:
                results.append((evals, meta))
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def _is_finetuned(meta: dict) -> bool:
    return "checkpoint" in meta


def _is_rlhf_checkpoint(checkpoint: str, rlhf_dir: str) -> bool:
    return Path(rlhf_dir) in Path(checkpoint).parents or str(rlhf_dir) in checkpoint


def _score_with_reward_model(
    reward_model_path: str,
    prompts: list[str],
    responses: list[str],
    batch_size: int = 8,
) -> list[float]:
    """Score (prompt, response) pairs with the reward model."""
    import torch
    from transformers import pipeline

    device = 0 if torch.cuda.is_available() else -1
    pipe = pipeline(
        "text-classification",
        model=reward_model_path,
        device=device,
        truncation=True,
        max_length=1024,
    )
    scores = []
    for i in range(0, len(prompts), batch_size):
        bp = prompts[i : i + batch_size]
        br = responses[i : i + batch_size]
        inputs  = [f"{p}\n{r}" for p, r in zip(bp, br)]
        results = pipe(inputs, batch_size=batch_size)
        scores.extend(float(r["score"]) for r in results)
    return scores


def main() -> int:
    p = argparse.ArgumentParser(
        description="Reward overoptimization diagnostic (Section 6.8)."
    )
    p.add_argument("--rlhf-checkpoint", required=True,
                   help="RLHF training output directory (containing training_config.json).")
    p.add_argument("--reward-model",    default=None,
                   help="Reward model checkpoint for live scoring. "
                        "If omitted, uses training stats if available.")
    p.add_argument("--results-dir",     default="experiments/results",
                   help="Fine-tuned evaluation results directory.")
    p.add_argument("--instances-dir",   default="instances")
    p.add_argument("--sample",          type=int, default=200)
    p.add_argument("--batch-size",      type=int, default=8)
    args = p.parse_args()

    rlhf_dir = Path(args.rlhf_checkpoint)

    print("=" * 72)
    print("Reward Overoptimization Diagnostic (Section 6.8)")
    print("=" * 72)

    # --- Method 1: Use training stats saved during PPO ---
    stats_path = rlhf_dir / "reward_stats.json"
    if stats_path.exists():
        print(f"\nLoading PPO reward stats from {stats_path}...")
        with open(stats_path) as f:
            stats = json.load(f)
        # Expected format: list of {"step": int, "mean_rm_score": float, "mean_verifier_score": float}
        if stats:
            final_step = max(stats, key=lambda s: s.get("step", 0))
            rm_mean = final_step.get("mean_rm_score", float("nan"))
            vf_mean = final_step.get("mean_verifier_score", float("nan"))
            gap     = rm_mean - vf_mean if (rm_mean == rm_mean and vf_mean == vf_mean) else float("nan")
            print(f"  At final step {final_step.get('step', '?')}:")
            print(f"    Mean R_phi   : {rm_mean:.4f}")
            print(f"    Mean S_defab : {vf_mean:.4f}")
            print(f"    Gap (R_phi - S_defab): {gap:+.4f}")
            if gap == gap:
                if gap > 0.15:
                    print("  WARNING: Large positive gap indicates potential reward hacking.")
                elif gap > 0.05:
                    print("  MODERATE: Small positive gap -- monitor for overoptimization.")
                else:
                    print("  HEALTHY: Minimal gap -- reward model tracks verifier well.")
            # Plot over training if multiple steps
            if len(stats) > 1:
                print(f"\n  Training curve ({len(stats)} checkpoints):")
                print(f"  {'Step':>8} {'R_phi':>10} {'S_defab':>10} {'Gap':>10}")
                for s in stats[::max(1, len(stats)//10)]:  # sample up to 10 points
                    rm  = s.get("mean_rm_score", float("nan"))
                    vf  = s.get("mean_verifier_score", float("nan"))
                    gap_s = rm - vf if rm == rm and vf == vf else float("nan")
                    print(f"  {s.get('step', '?'):>8} {rm:>10.4f} {vf:>10.4f} "
                          f"{gap_s:>+10.4f}")
            return 0

    # --- Method 2: Live scoring with reward model on eval results ---
    if args.reward_model is None:
        print("\nNo training stats found and no --reward-model provided.")
        print("To generate reward_stats.json, modify train_rlhf_vitl.py to log")
        print("both R_phi and S_defab at each PPO step, or provide --reward-model.")
        print("\nAlternatively, run analyze_reward_fidelity.py for static correlation.")
        return 1

    if not Path(args.reward_model).exists():
        print(f"ERROR: Reward model not found: {args.reward_model}")
        return 1

    # Load eval results for the RLHF checkpoint
    results_dir = ROOT / args.results_dir
    all_results = _load_all_results(results_dir)
    rlhf_results = [
        (e, m) for e, m in all_results
        if _is_finetuned(m) and "rlhf" in str(m.get("checkpoint", "")).lower()
    ]

    if not rlhf_results:
        print("No RLHF evaluation results found. Run evaluate_finetuned.py first:")
        print("  sbatch --export=ALL,CHECKPOINT=<rlhf_checkpoint>/final,"
              "BASE_MODEL=<model> hpc/slurm_eval_finetuned.sh")
        return 1

    # Collect prompts and responses from eval results
    prompts: list[str]   = []
    responses: list[str] = []
    verifier_scores: list[float] = []

    from blanc.author.loaders import load_instances_from_json
    from prompting import render_prompt

    instances_dir = ROOT / args.instances_dir
    instances = load_instances_from_json(instances_dir, include_level3=True)
    inst_by_id = {inst.id: inst for inst in instances}

    for evals, meta in rlhf_results[:1]:  # use first RLHF result set
        for ev in evals[:args.sample]:
            iid      = ev.get("instance_id", "")
            response = ev.get("response_text", ev.get("metrics", {}).get("response", ""))
            modality = ev.get("modality", "M4")
            strategy = ev.get("strategy", "direct")
            correct  = float(ev.get("metrics", {}).get("correct", False))
            graded   = ev.get("metrics", {}).get("graded_score", correct)

            if not response or iid not in inst_by_id:
                continue

            inst   = inst_by_id[iid]
            prompt = render_prompt(inst, modality, strategy).prompt
            prompts.append(prompt)
            responses.append(response)
            verifier_scores.append(float(graded))

    if not prompts:
        print("No valid (prompt, response) pairs extracted from eval results.")
        return 1

    print(f"\nScoring {len(prompts)} responses with reward model...")
    rm_scores = _score_with_reward_model(
        args.reward_model, prompts, responses, batch_size=args.batch_size
    )

    rm_mean = sum(rm_scores) / len(rm_scores)
    vf_mean = sum(verifier_scores) / len(verifier_scores)
    gap     = rm_mean - vf_mean

    print(f"\n  Mean R_phi   : {rm_mean:.4f}")
    print(f"  Mean S_defab : {vf_mean:.4f}")
    print(f"  Gap (R_phi - S_defab): {gap:+.4f}")

    if gap > 0.15:
        print("\n  WARNING: Large gap -- reward model overoptimization detected.")
        print("  The policy exploits the reward model at the expense of formal correctness.")
        print("  VITL eliminates this gap by construction.")
    elif gap > 0.05:
        print("\n  MODERATE gap -- monitor, but likely acceptable.")
    else:
        print("\n  HEALTHY: Reward model and verifier are well-aligned.")

    # Save
    out_path = rlhf_dir / "overoptimization_analysis.json"
    with open(out_path, "w") as f:
        json.dump({"rm_mean": rm_mean, "verifier_mean": vf_mean,
                   "gap": gap, "n": len(prompts)}, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
