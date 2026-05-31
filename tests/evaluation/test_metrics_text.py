"""CER : valeurs, cas dégénérés, fiche."""

from __future__ import annotations

import pytest

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metrics.text import cer


def _ctx(reference: object, hypothesis: object) -> DocContext:
    return DocContext(document_id="d", reference=reference, hypothesis=hypothesis)


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


def test_cer_fiche() -> None:
    assert cer.name == "cer"
    assert cer.input_types == (ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT)
    assert cer.spec.higher_is_better is False


def test_cer_rejects_non_text() -> None:
    with pytest.raises(EvaluationError):
        cer.fn(_ctx(123, "x"))
