"""Métrique inter-moteurs ``significance`` (Wilcoxon / Friedman, via scipy)."""

from __future__ import annotations

from xerocr.evaluation.context import CrossEngineContext
from xerocr.evaluation.metrics.stats import significance


def _ctx(per_pipeline: dict[str, tuple[float | None, ...]]) -> CrossEngineContext:
    return CrossEngineContext(metric="cer", per_pipeline=per_pipeline)


def test_significant_difference_low_pvalue() -> None:
    # A systématiquement meilleur que B sur 10 docs → p faible
    better = tuple(0.1 for _ in range(10))
    worse = tuple(0.3 for _ in range(10))
    value, support = significance.fn(_ctx({"A": better, "B": worse}))
    assert support == 10
    assert value is not None
    assert value < 0.05


def test_no_difference_returns_none() -> None:
    same = tuple(0.2 for _ in range(5))
    value, support = significance.fn(_ctx({"A": same, "B": same}))
    assert value is None  # aucune variance à tester
    assert support == 5


def test_insufficient_support_returns_none() -> None:
    value, support = significance.fn(_ctx({"A": (0.1,), "B": (0.2,)}))
    assert value is None
    assert support == 1


def test_single_pipeline_returns_none() -> None:
    value, support = significance.fn(_ctx({"A": (0.1, 0.2)}))
    assert value is None
    assert support == 0


def test_incomplete_documents_are_dropped() -> None:
    # doc où B est None → cas incomplet, exclu (support compte les cas complets)
    value, support = significance.fn(
        _ctx({"A": (0.1, 0.1, 0.1), "B": (0.3, 0.3, None)})
    )
    assert support == 2


def test_three_engines_use_friedman() -> None:
    eight = range(8)
    a = tuple(0.1 for _ in eight)
    b = tuple(0.4 for _ in eight)
    c = tuple(0.2 for _ in eight)
    value, support = significance.fn(_ctx({"A": a, "B": b, "C": c}))
    assert support == 8
    assert value is not None
