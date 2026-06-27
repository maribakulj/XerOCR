"""FCA : exactitude caractère par appariement optimal de lignes, ordre libre."""

from __future__ import annotations

import pytest

from cinoc.evaluation.context import DocContext
from cinoc.evaluation.errors import EvaluationError
from cinoc.evaluation.metrics.flexible import flexible_character_accuracy as fca


def _ctx(reference: object, hypothesis: object) -> DocContext:
    return DocContext(document_id="d", reference=reference, hypothesis=hypothesis)


def test_identical_multiline_is_perfect() -> None:
    text = "alpha\nbeta\ngamma"
    assert fca.fn(_ctx(text, text)).value == 1.0


def test_reading_order_independent() -> None:
    # Lignes interverties : le CER plongerait, FCA reste parfaite (cœur de FCA).
    gt = "premiere ligne\ndeuxieme ligne\ntroisieme ligne"
    ocr = "troisieme ligne\npremiere ligne\ndeuxieme ligne"
    assert fca.fn(_ctx(gt, ocr)).value == 1.0


def test_one_substitution_counts_once() -> None:
    # 1 caractère faux sur 15 ('alpha'+'beta'+'gamma' = 14 ? -> compter) :
    gt = "alpha\nbeta\ngamma"  # 5 + 4 + 5 = 14 caractères de réf.
    ocr = "alpha\nbxta\ngamma"  # une substitution dans 'beta'
    obs = fca.fn(_ctx(gt, ocr))
    assert obs.weight == 14
    assert obs.value == pytest.approx(1 - 1 / 14)


def test_extra_hypothesis_line_is_insertion_not_free() -> None:
    # Ligne d'hypothèse en trop : comptée comme insertion (n'améliore pas le score).
    gt = "alpha\nbeta"
    ocr = "alpha\nbeta\ngamma"
    obs = fca.fn(_ctx(gt, ocr))
    assert obs.value < 1.0  # 'gamma' inséré pénalise


def test_missing_line_is_deletion() -> None:
    gt = "alpha\nbeta\ngamma"  # 14 car.
    ocr = "alpha\ngamma"  # 'beta' (4 car.) manquant
    obs = fca.fn(_ctx(gt, ocr))
    assert obs.value == pytest.approx(1 - 4 / 14)


def test_empty_reference() -> None:
    assert fca.fn(_ctx("", "")).value == 1.0
    assert fca.fn(_ctx("", "x")).value == 0.0
    assert fca.fn(_ctx("", "x")).weight == 0  # exclue du micro


def test_higher_is_better_and_type_guard() -> None:
    assert fca.spec.higher_is_better is True
    with pytest.raises(EvaluationError):
        fca.fn(_ctx(123, "x"))
