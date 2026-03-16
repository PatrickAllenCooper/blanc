"""
Phase B6: Parameter Sparsity Analysis across Post-Training Methods.

Compares the effective sparsity of parameter updates produced by DPO,
GRPO, SFT, and RLHF.  For each method's LoRA checkpoint, computes:

  - Frobenius norm of the LoRA delta (||B A||_F)
  - Effective rank (exp of spectral entropy of singular values)
  - L0 sparsity (fraction of near-zero elements in B A)
  - Spectral entropy (information-theoretic measure of rank concentration)
  - Nuclear norm (sum of singular values -- convex proxy for rank)

Tests Conjecture 5: GRPO produces sparser parameter updates than DPO,
with sparsity concentrated in layers relevant to conservativity reasoning.

Usage:
  python experiments/finetuning/analyze_parameter_sparsity.py \\
      --checkpoints-dir experiments/finetuning/checkpoints/ \\
      --output-dir experiments/finetuning/analysis/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import torch
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "finetuning"))

from spectral_lora import compute_spectral_metrics


# ---------------------------------------------------------------------------
# LoRA delta extraction
# ---------------------------------------------------------------------------

def extract_lora_deltas(checkpoint_dir: Path) -> dict[str, torch.Tensor]:
    """Extract the effective weight deltas (B @ A) from a LoRA checkpoint.

    Returns a dict mapping layer name -> delta_W tensor.
    """
    adapter_path = checkpoint_dir / "adapter_model.safetensors"
    if not adapter_path.exists():
        adapter_path = checkpoint_dir / "adapter_model.bin"
    if not adapter_path.exists():
        return {}

    if adapter_path.suffix == ".safetensors":
        from safetensors.torch import load_file
        state_dict = load_file(str(adapter_path))
    else:
        state_dict = torch.load(str(adapter_path), map_location="cpu")

    # Group A and B matrices by layer
    layers: dict[str, dict] = {}
    for key, tensor in state_dict.items():
        if "lora_A" in key:
            base_name = key.replace(".lora_A.weight", "").replace(".lora_A.default.weight", "")
            layers.setdefault(base_name, {})["A"] = tensor
        elif "lora_B" in key:
            base_name = key.replace(".lora_B.weight", "").replace(".lora_B.default.weight", "")
            layers.setdefault(base_name, {})["B"] = tensor

    deltas = {}
    for name, ab in layers.items():
        if "A" in ab and "B" in ab:
            A = ab["A"].float()  # (r, in_features)
            B = ab["B"].float()  # (out_features, r)
            deltas[name] = B @ A  # (out_features, in_features)

    return deltas


def analyze_checkpoint(checkpoint_dir: Path) -> dict:
    """Analyze a single checkpoint's parameter sparsity."""
    deltas = extract_lora_deltas(checkpoint_dir)
    if not deltas:
        return {"error": f"No LoRA weights found in {checkpoint_dir}"}

    per_layer = {}
    all_frob   = []
    all_erank  = []
    all_l0     = []
    all_entropy = []

    for name, delta_W in deltas.items():
        metrics = compute_spectral_metrics(delta_W)
        per_layer[name] = metrics
        all_frob.append(metrics["frobenius_norm"])
        all_erank.append(metrics["effective_rank"])
        all_l0.append(metrics["l0_sparsity"])
        all_entropy.append(metrics["spectral_entropy"])

    return {
        "num_layers":          len(deltas),
        "mean_frobenius_norm": float(np.mean(all_frob)),
        "mean_effective_rank": float(np.mean(all_erank)),
        "mean_l0_sparsity":   float(np.mean(all_l0)),
        "mean_spectral_entropy": float(np.mean(all_entropy)),
        "std_effective_rank":  float(np.std(all_erank)),
        "per_layer":           per_layer,
    }


# ---------------------------------------------------------------------------
# Multi-checkpoint comparison
# ---------------------------------------------------------------------------

def find_checkpoints(
    checkpoints_dir: Path,
    methods: Optional[list[str]] = None,
) -> dict[str, Path]:
    """Discover checkpoint directories, grouped by method name."""
    results = {}
    if not checkpoints_dir.exists():
        return results

    for d in sorted(checkpoints_dir.iterdir()):
        if not d.is_dir():
            continue
        final = d / "final"
        if final.exists():
            method_name = d.name
            if methods and not any(m in method_name for m in methods):
                continue
            results[method_name] = final

    return results


def compare_methods(analyses: dict[str, dict]) -> str:
    """Generate a formatted comparison table."""
    lines = []
    lines.append(f"{'Method':<40} {'Layers':>6} {'||dW||_F':>10} "
                 f"{'EffRank':>8} {'L0 Spar':>8} {'S.Entr':>8}")
    lines.append("-" * 86)

    for name, a in sorted(analyses.items()):
        if "error" in a:
            lines.append(f"{name:<40} {a['error']}")
            continue
        lines.append(
            f"{name:<40} {a['num_layers']:>6} "
            f"{a['mean_frobenius_norm']:>10.4f} "
            f"{a['mean_effective_rank']:>8.2f} "
            f"{a['mean_l0_sparsity']:>8.4f} "
            f"{a['mean_spectral_entropy']:>8.4f}"
        )
    return "\n".join(lines)


def generate_latex_table(analyses: dict[str, dict]) -> str:
    """Generate a LaTeX table for the paper."""
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Parameter update sparsity across post-training methods. "
        r"Effective rank measures the spectral concentration of LoRA updates "
        r"(lower = sparser). L0 sparsity is the fraction of near-zero elements "
        r"in the effective weight delta $BA$.}",
        r"\label{tab:sparsity}",
        r"\small",
        r"\begin{tabular}{@{}lccccc@{}}",
        r"\toprule",
        r"Method & Layers & $\|BA\|_F$ & Eff.~Rank & L0 & Spectral Entropy \\",
        r"\midrule",
    ]

    for name, a in sorted(analyses.items()):
        if "error" in a:
            continue
        short = name.replace("_", r"\_")
        lines.append(
            f"{short} & {a['num_layers']} & "
            f"{a['mean_frobenius_norm']:.3f} & "
            f"{a['mean_effective_rank']:.1f} & "
            f"{a['mean_l0_sparsity']:.3f} & "
            f"{a['mean_spectral_entropy']:.3f} \\\\"
        )

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze parameter sparsity of LoRA checkpoints."
    )
    p.add_argument("--checkpoints-dir",
                   default="experiments/finetuning/checkpoints")
    p.add_argument("--checkpoint", default=None,
                   help="Analyze a single checkpoint directory.")
    p.add_argument("--methods", nargs="+", default=None,
                   help="Filter checkpoint names (substring match).")
    p.add_argument("--output-dir", default=None,
                   help="Write analysis JSON and LaTeX to this directory.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb Parameter Sparsity Analysis")
    print("=" * 70)

    if args.checkpoint:
        ckpt = Path(args.checkpoint)
        print(f"\nAnalyzing single checkpoint: {ckpt}")
        analysis = analyze_checkpoint(ckpt)
        if "error" in analysis:
            print(f"  ERROR: {analysis['error']}")
            return 1
        print(f"  Layers: {analysis['num_layers']}")
        print(f"  Mean ||dW||_F:       {analysis['mean_frobenius_norm']:.4f}")
        print(f"  Mean Effective Rank: {analysis['mean_effective_rank']:.2f}")
        print(f"  Mean L0 Sparsity:    {analysis['mean_l0_sparsity']:.4f}")
        print(f"  Mean Spectral Entr:  {analysis['mean_spectral_entropy']:.4f}")
        return 0

    ckpts_dir = ROOT / args.checkpoints_dir
    print(f"\nSearching for checkpoints in: {ckpts_dir}")

    checkpoints = find_checkpoints(ckpts_dir, args.methods)
    if not checkpoints:
        print("  No checkpoints found.")
        print("  (Run training first, or specify --checkpoint for a single dir)")
        return 0

    print(f"  Found {len(checkpoints)} checkpoints")

    analyses = {}
    for name, path in checkpoints.items():
        print(f"\n  Analyzing: {name}")
        analyses[name] = analyze_checkpoint(path)
        if "error" not in analyses[name]:
            a = analyses[name]
            print(f"    Layers={a['num_layers']}  "
                  f"||dW||_F={a['mean_frobenius_norm']:.4f}  "
                  f"EffRank={a['mean_effective_rank']:.2f}  "
                  f"L0={a['mean_l0_sparsity']:.4f}")

    print(f"\n{'='*86}")
    print(compare_methods(analyses))

    if args.output_dir:
        out = ROOT / args.output_dir
        out.mkdir(parents=True, exist_ok=True)

        with open(out / "sparsity_analysis.json", "w") as f:
            serializable = {}
            for name, a in analyses.items():
                sa = {k: v for k, v in a.items() if k != "per_layer"}
                serializable[name] = sa
            json.dump(serializable, f, indent=2)

        latex = generate_latex_table(analyses)
        with open(out / "sparsity_table.tex", "w") as f:
            f.write(latex)

        print(f"\nResults saved to {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
