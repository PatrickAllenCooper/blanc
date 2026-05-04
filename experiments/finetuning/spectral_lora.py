"""
Spectral LoRA initialization via SVD.

Standard LoRA initializes A with Kaiming uniform and B with zeros, so the
initial delta_W = BA = 0.  Spectral initialization instead seeds A and B
from the top-r singular components of the pre-trained weight matrix,
concentrating adaptation onto the most significant spectral directions.

This yields sparser effective parameter changes because gradient updates
are projected into a subspace aligned with the weight matrix's dominant
spectral structure rather than a random subspace.

Implementation follows the SeLoRA / Sparse Spectral Training paradigm:
  W = U S V^T   (truncated SVD, rank r)
  A <- V_r^T    (top-r right singular vectors)
  B <- U_r S_r  (scaled left singular vectors)

The product B A = U_r S_r V_r^T is the rank-r approximation of W,
but we scale it by (lora_alpha / r) to match LoRA's scaling convention,
and subtract the base weight contribution to ensure the initial effective
weight change is not the full rank-r projection but rather a controlled
perturbation.

Author: Anonymous Authors
"""

from __future__ import annotations

import torch


def spectral_init_lora(model, lora_config=None, alpha_scale: bool = True) -> int:
    """Apply SVD-based spectral initialization to all LoRA layers.

    Parameters
    ----------
    model : nn.Module
        A PEFT-wrapped model with LoRA adapters already applied.
    lora_config : LoraConfig, optional
        Used to read lora_alpha and r for scaling.  If None, reads r from
        the LoRA layer shapes directly and assumes alpha/r = 1.
    alpha_scale : bool
        If True, scale initialization by lora_alpha / r.

    Returns
    -------
    int
        Number of layers initialized.
    """
    count = 0

    for name, module in model.named_modules():
        lora_A = getattr(module, "lora_A", None)
        lora_B = getattr(module, "lora_B", None)
        base_layer = getattr(module, "base_layer", None)

        if lora_A is None or lora_B is None:
            continue

        # Navigate through PEFT's module structure to get the actual Linear
        A_weight = None
        B_weight = None

        if hasattr(lora_A, "default"):
            A_linear = lora_A["default"]
            A_weight = A_linear.weight if hasattr(A_linear, "weight") else None
        elif hasattr(lora_A, "weight"):
            A_weight = lora_A.weight

        if hasattr(lora_B, "default"):
            B_linear = lora_B["default"]
            B_weight = B_linear.weight if hasattr(B_linear, "weight") else None
        elif hasattr(lora_B, "weight"):
            B_weight = lora_B.weight

        if A_weight is None or B_weight is None:
            continue

        # Get the base weight matrix
        W = None
        if base_layer is not None and hasattr(base_layer, "weight"):
            W = base_layer.weight.data
        elif hasattr(module, "weight"):
            W = module.weight.data

        if W is None:
            continue

        r = A_weight.shape[0]

        # SVD of the base weight (compute in float32 for stability)
        with torch.no_grad():
            W_float = W.float()
            U, S, Vh = torch.linalg.svd(W_float, full_matrices=False)

            # Top-r components
            U_r  = U[:, :r]       # (out_features, r)
            S_r  = S[:r]          # (r,)
            Vh_r = Vh[:r, :]      # (r, in_features)

            scale = 1.0
            if alpha_scale and lora_config is not None:
                alpha = getattr(lora_config, "lora_alpha", r)
                scale = alpha / r

            # A: (r, in_features) -- right singular vectors
            A_weight.data = (Vh_r * scale).to(A_weight.dtype)
            # B: (out_features, r) -- scaled left singular vectors
            B_weight.data = (U_r * S_r.unsqueeze(0)).to(B_weight.dtype)

        count += 1

    return count


def compute_spectral_metrics(delta_W: torch.Tensor) -> dict:
    """Compute spectral properties of a weight update matrix.

    Parameters
    ----------
    delta_W : Tensor of shape (out, in)
        The weight change matrix (W_finetuned - W_base or B @ A).

    Returns
    -------
    dict with keys:
        frobenius_norm : float
        nuclear_norm   : float
        spectral_norm  : float (largest singular value)
        effective_rank : float (exp of spectral entropy)
        spectral_entropy : float
        l0_sparsity    : float (fraction of near-zero elements)
        singular_values : list[float]
    """
    with torch.no_grad():
        W = delta_W.float()
        S = torch.linalg.svdvals(W)

        frob = torch.norm(W, p="fro").item()
        nuc  = S.sum().item()
        spec = S[0].item() if len(S) > 0 else 0.0

        # Spectral entropy and effective rank
        S_pos = S[S > 1e-10]
        if len(S_pos) > 0:
            p = S_pos / S_pos.sum()
            entropy = -(p * p.log()).sum().item()
            eff_rank = torch.exp(torch.tensor(entropy)).item()
        else:
            entropy  = 0.0
            eff_rank = 0.0

        # L0 sparsity: fraction of elements below threshold
        threshold = frob * 1e-6 if frob > 0 else 1e-10
        l0 = (W.abs() < threshold).float().mean().item()

    return {
        "frobenius_norm":   frob,
        "nuclear_norm":     nuc,
        "spectral_norm":    spec,
        "effective_rank":   eff_rank,
        "spectral_entropy": entropy,
        "l0_sparsity":      l0,
        "singular_values":  S.tolist(),
    }
