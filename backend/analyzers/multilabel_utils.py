"""Multi-label style training helpers (pos_weight, weighted sampling)."""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

import torch
from torch.utils.data import Sampler, WeightedRandomSampler

from .labels import STYLE_LABELS

# BCE target order for style head
STYLE_TARGET_ORDER: List[str] = list(STYLE_LABELS)

COZY_INDEX = STYLE_TARGET_ORDER.index("cozy")
ROMANTIC_INDEX = STYLE_TARGET_ORDER.index("romantic")
CALM_INDEX = STYLE_TARGET_ORDER.index("calm")

POS_WEIGHT_MAX = 10.0


def style_vector_from_multihot(blob: Mapping[str, float]) -> List[float]:
    return [float(blob.get(label, 0.0)) for label in STYLE_TARGET_ORDER]


def style_vector_from_list(values: Sequence[float]) -> List[float]:
    return [float(v) for v in values[: len(STYLE_TARGET_ORDER)]]


def compute_pos_weight(
    y_style: torch.Tensor,
    *,
    max_weight: float = POS_WEIGHT_MAX,
    eps: float = 1e-6,
) -> torch.Tensor:
    """
    Per-label pos_weight = (N - pos) / (pos + eps), clamped to ``max_weight``.

    ``y_style`` shape: (N, num_style_labels), values in {0, 1}.
    """
    if y_style.numel() == 0:
        return torch.ones(y_style.shape[1] if y_style.ndim == 2 else len(STYLE_TARGET_ORDER))
    n = float(y_style.shape[0])
    pos = y_style.sum(dim=0).clamp(min=eps)
    neg = n - pos
    weights = neg / pos
    return weights.clamp(min=1.0, max=max_weight)


def rare_label_sample_weights(
    y_style: torch.Tensor,
    *,
    cozy_mult: float = 4.0,
    romantic_calm_mult: float = 2.5,
    base: float = 1.0,
) -> torch.Tensor:
    """
    Per-sample weights for ``WeightedRandomSampler``.

    - cozy present → ``cozy_mult`` (default 4x, within 3~5x range)
    - romantic or calm (no cozy) → ``romantic_calm_mult`` (default 2.5x, within 2~3x)
    """
    weights = torch.full((y_style.shape[0],), base, dtype=torch.float64)
    has_cozy = y_style[:, COZY_INDEX] > 0.5
    has_romantic = y_style[:, ROMANTIC_INDEX] > 0.5
    has_calm = y_style[:, CALM_INDEX] > 0.5
    rare_rc = (has_romantic | has_calm) & ~has_cozy

    weights[has_cozy] *= cozy_mult
    weights[rare_rc] *= romantic_calm_mult
    return weights


def make_rare_label_sampler(
    y_style: torch.Tensor,
    *,
    num_samples: Optional[int] = None,
    cozy_mult: float = 4.0,
    romantic_calm_mult: float = 2.5,
) -> WeightedRandomSampler:
    w = rare_label_sample_weights(
        y_style, cozy_mult=cozy_mult, romantic_calm_mult=romantic_calm_mult
    )
    n = int(y_style.shape[0]) if num_samples is None else int(num_samples)
    return WeightedRandomSampler(
        weights=w.double(),
        num_samples=n,
        replacement=True,
    )


def multilabel_style_pos_rates(y_style: torch.Tensor) -> Dict[str, float]:
    if y_style.numel() == 0:
        return {lab: 0.0 for lab in STYLE_TARGET_ORDER}
    rates = y_style.mean(dim=0).tolist()
    return {lab: round(float(r), 4) for lab, r in zip(STYLE_TARGET_ORDER, rates)}
