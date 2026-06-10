"""Inférence statistique corrigée : post-hoc de Nemenyi + bootstrap (couche 3).

Référence : Demšar, J. (2006), *Statistical Comparisons of Classifiers over
Multiple Data Sets*, JMLR 7:1-30 — le standard pour comparer k systèmes sur n
jeux appariés (ici : k pipelines × n documents). La p-value brute
(``significance_p``, Wilcoxon/Friedman) dit « il existe une différence » ; le
post-hoc dit **lesquelles** des paires diffèrent, en corrigeant les
comparaisons multiples (distance critique CD = q_α·√(k(k+1)/6n)).

Bootstrap : **percentile** (Efron), graine fixe → déterministe (invariant §12) ;
volontairement pas BCa (simple à auditer, suffisant pour un IC indicatif).
Indice de quantile = statistique d'ordre ``round(q·(n_iter−1))`` (l'indice
``int(q·n_iter)`` décalerait la borne haute d'un rang — bug relevé à l'audit
scientifique de l'implémentation source, non reproduit ici).

Tout est stdlib (``random``, ``math``) : pas de tirage numpy, déterminisme
indépendant des versions BLAS.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence

from xerocr.evaluation.analysis import (
    Analysis,
    InferencePayload,
    PairwiseDifference,
    PipelineInterval,
    PipelineRank,
)

#: Plancher de **puissance**, partagé avec ``metrics.stats.significance`` :
#: sous ~6 cas complets, ni Wilcoxon ni des rangs moyens n'ont de sens — on ne
#: produit pas d'analyse plutôt qu'un verdict artefact de petit n.
MIN_SUPPORT = 6

#: Valeurs critiques du Studentized Range ÷ √2, df = ∞ (tables de Tukey),
#: q_α pour α ∈ {0.05, 0.01} — clé : nombre de pipelines k.
_NEMENYI_Q_TABLE: dict[int, tuple[float, float]] = {
    2: (1.960, 2.576),
    3: (2.343, 2.913),
    4: (2.569, 3.113),
    5: (2.728, 3.255),
    6: (2.850, 3.364),
    7: (2.949, 3.452),
    8: (3.031, 3.526),
    9: (3.102, 3.590),
    10: (3.164, 3.646),
    11: (3.219, 3.696),
    12: (3.268, 3.741),
    13: (3.313, 3.781),
    14: (3.354, 3.818),
    15: (3.391, 3.853),
    16: (3.426, 3.886),
    17: (3.458, 3.916),
    18: (3.489, 3.944),
    19: (3.517, 3.970),
    20: (3.544, 3.995),
    25: (3.658, 4.095),
    30: (3.739, 4.167),
    40: (3.858, 4.272),
    50: (3.945, 4.349),
}


def nemenyi_critical_value(k: int, alpha: float = 0.05) -> tuple[float, bool]:
    """``(q_α, extrapolé)`` pour k pipelines, df = ∞.

    Entre deux clés tabulées : interpolation linéaire. Au-delà de k = 50 :
    **extrapolation** linéaire depuis les deux derniers points — q(k) étant
    concave croissante, la droite **surestime** q ⇒ CD plus grande ⇒ moins de
    rejets ⇒ réellement conservateur (réutiliser q(50), plus petit, serait
    anti-conservateur : plus de faux positifs).
    """
    if k < 2:
        raise ValueError("nemenyi_critical_value : k >= 2 requis.")
    col = 1 if alpha == 0.01 else 0
    if k in _NEMENYI_Q_TABLE:
        return _NEMENYI_Q_TABLE[k][col], False
    keys = sorted(_NEMENYI_Q_TABLE)
    if k > keys[-1]:
        lo, hi = keys[-2], keys[-1]
        q_lo, q_hi = _NEMENYI_Q_TABLE[lo][col], _NEMENYI_Q_TABLE[hi][col]
        slope = (q_hi - q_lo) / (hi - lo)
        return q_hi + slope * (k - hi), True
    hi = min(key for key in keys if key > k)
    lo = max(key for key in keys if key < k)
    q_lo, q_hi = _NEMENYI_Q_TABLE[lo][col], _NEMENYI_Q_TABLE[hi][col]
    return q_lo + (q_hi - q_lo) * (k - lo) / (hi - lo), False


def bootstrap_ci(
    values: Sequence[float],
    n_iter: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """IC percentile de la moyenne par bootstrap — déterministe (graine fixe)."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(
        sum(values[rng.randint(0, n - 1)] for _ in range(n)) / n
        for _ in range(n_iter)
    )
    half_alpha = (1.0 - ci) / 2.0

    def order_stat(q: float) -> float:
        return means[max(0, min(n_iter - 1, round(q * (n_iter - 1))))]

    return (order_stat(half_alpha), order_stat(1.0 - half_alpha))


def _rank_row(values: Sequence[float]) -> list[float]:
    """Rangs d'une ligne (petit = rang 1) ; ex-aequo → rangs moyens."""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and values[indexed[j]] == values[indexed[i]]:
            j += 1
        avg = (i + j + 1) / 2.0  # 1-based
        for pos in range(i, j):
            ranks[indexed[pos]] = avg
        i = j
    return ranks


def _tied_groups(
    names: Sequence[str], ranks: Sequence[float], critical_distance: float
) -> tuple[tuple[str, ...], ...]:
    """Groupes maximaux d'indiscernables : fenêtre ≤ CD sur les rangs triés."""
    order = sorted(range(len(names)), key=lambda i: (ranks[i], names[i]))
    sorted_names = [names[i] for i in order]
    sorted_ranks = [ranks[i] for i in order]
    groups: list[tuple[str, ...]] = []
    i = 0
    while i < len(sorted_names):
        j = i
        while (
            j + 1 < len(sorted_names)
            and sorted_ranks[j + 1] - sorted_ranks[i] <= critical_distance
        ):
            j += 1
        groups.append(tuple(sorted_names[i : j + 1]))
        i = j + 1 if j > i else i + 1
    return tuple(groups)


def inference_payload(
    metric: str,
    per_pipeline: Mapping[str, Sequence[float | None]],
    alpha: float = 0.05,
) -> InferencePayload | None:
    """Inférentiel d'une (vue × métrique) ; ``None`` si non applicable.

    ``per_pipeline`` : valeurs par-document **alignées** (même index = même
    document ; ``None`` = non applicable). Rangs et Nemenyi sur les **cas
    complets** ; IC bootstrap sur les valeurs valides **marginales** de chaque
    pipeline (plus de données, l'IC est par-pipeline, pas apparié).
    """
    names = sorted(per_pipeline)
    k = len(names)
    if k < 2:
        return None
    series = [per_pipeline[name] for name in names]
    n_aligned = min(len(column) for column in series)
    complete = [
        [series[i][j] for i in range(k)]
        for j in range(n_aligned)
        if all(series[i][j] is not None for i in range(k))
    ]
    if len(complete) < MIN_SUPPORT:
        return None

    rank_sums = [0.0] * k
    for row in complete:
        for i, rank in enumerate(_rank_row([float(v) for v in row if v is not None])):
            rank_sums[i] += rank
    n_blocks = len(complete)
    means = [rank_sums[i] / n_blocks for i in range(k)]
    mean_ranks = tuple(
        PipelineRank(pipeline=name, mean_rank=rank)
        for rank, name in sorted(
            ((means[i], names[i]) for i in range(k)), key=lambda p: (p[0], p[1])
        )
    )

    critical_distance: float | None = None
    q_alpha: float | None = None
    extrapolated = False
    tied: tuple[tuple[str, ...], ...] = ()
    pairwise: tuple[PairwiseDifference, ...] = ()
    if k >= 3:
        q_alpha, extrapolated = nemenyi_critical_value(k, alpha)
        critical_distance = q_alpha * math.sqrt(k * (k + 1) / (6.0 * n_blocks))
        tied = _tied_groups(names, means, critical_distance)
        pairwise = tuple(
            PairwiseDifference(
                a=names[i],
                b=names[j],
                rank_gap=abs(means[i] - means[j]),
                significant=abs(means[i] - means[j]) > critical_distance,
            )
            for i in range(k)
            for j in range(i + 1, k)
        )

    intervals: list[PipelineInterval] = []
    for i, name in enumerate(names):
        valid = [float(v) for v in series[i] if v is not None]
        if not valid:
            continue
        lower, upper = bootstrap_ci(valid)
        intervals.append(
            PipelineInterval(
                pipeline=name,
                mean=sum(valid) / len(valid),
                lower=lower,
                upper=upper,
                n_documents=len(valid),
            )
        )

    return InferencePayload(
        metric=metric,
        alpha=alpha,
        n_documents=n_blocks,
        critical_distance=critical_distance,
        q_alpha=q_alpha,
        q_alpha_extrapolated=extrapolated,
        mean_ranks=mean_ranks,
        tied_groups=tied,
        pairwise=pairwise,
        intervals=tuple(intervals),
    )


def inference_analysis(
    view: str,
    metric: str,
    per_pipeline: Mapping[str, Sequence[float | None]],
    alpha: float = 0.05,
) -> Analysis | None:
    """``Analysis`` de portée corpus pour (vue × métrique), ou ``None``."""
    payload = inference_payload(metric, per_pipeline, alpha)
    if payload is None:
        return None
    return Analysis(scope="corpus", view=view, payload=payload)


__all__ = [
    "MIN_SUPPORT",
    "bootstrap_ci",
    "inference_analysis",
    "inference_payload",
    "nemenyi_critical_value",
]
