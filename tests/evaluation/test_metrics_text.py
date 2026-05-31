"""CER / WER / MER : valeurs calculées à la main, cas dégénérés, fiches."""

from __future__ import annotations

import pytest

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metrics.text import cer, mer, wer


def _ctx(reference: object, hypothesis: object) -> DocContext:
    return DocContext(document_id="d", reference=reference, hypothesis=hypothesis)


# ── CER ──────────────────────────────────────────────────────────────────
def test_cer_perfect_match() -> None:
    assert cer.fn(_ctx("abc", "abc")) == 0.0


def test_cer_one_substitution() -> None:
    assert cer.fn(_ctx("abc", "abx")) == pytest.approx(1 / 3)


def test_cer_both_empty() -> None:
    assert cer.fn(_ctx("", "")) == 0.0


def test_cer_empty_reference_nonempty_hypothesis() -> None:
    assert cer.fn(_ctx("", "x")) == 1.0


def test_cer_nonempty_reference_empty_hypothesis() -> None:
    assert cer.fn(_ctx("abc", "")) == 1.0


# ── WER ──────────────────────────────────────────────────────────────────
def test_wer_one_substitution() -> None:
    # ["le","chat","noir"] vs ["le","chien","noir"] : 1 sub / 3 mots
    assert wer.fn(_ctx("le chat noir", "le chien noir")) == pytest.approx(1 / 3)


def test_wer_deletion() -> None:
    assert wer.fn(_ctx("a b c", "a c")) == pytest.approx(1 / 3)


def test_wer_degenerate() -> None:
    assert wer.fn(_ctx("", "")) == 0.0
    assert wer.fn(_ctx("", "x")) == 1.0
    assert wer.fn(_ctx("a b", "")) == 1.0


# ── MER ──────────────────────────────────────────────────────────────────
def test_mer_substitution() -> None:
    # hits=2 (le, noir), subs=1 (chat/chien) -> 1/3
    assert mer.fn(_ctx("le chat noir", "le chien noir")) == pytest.approx(1 / 3)


def test_mer_insertion() -> None:
    # hits=2, ins=1 -> 1/3
    assert mer.fn(_ctx("a b", "a b c")) == pytest.approx(1 / 3)


def test_mer_both_empty() -> None:
    assert mer.fn(_ctx("", "")) == 0.0


# ── fiches & garde-types ──────────────────────────────────────────────────
def test_fiches() -> None:
    for metric in (cer, wer, mer):
        assert metric.input_types == (ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT)
        assert metric.spec.higher_is_better is False
    assert {cer.name, wer.name, mer.name} == {"cer", "wer", "mer"}


def test_metrics_reject_non_text() -> None:
    for metric in (cer, wer, mer):
        with pytest.raises(EvaluationError):
            metric.fn(_ctx(123, "x"))
