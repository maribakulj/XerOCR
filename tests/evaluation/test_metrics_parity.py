"""Parité CER/WER/MER vs jiwer (oracle, dépendance *dev*). Skippé si jiwer absent.

Entrées propres (espaces simples, sans bord) → alignement non ambigu, donc MER
comparable. Les valeurs exactes (y compris cas dégénérés) sont, elles, vérifiées
sans jiwer dans ``test_metrics_text``.
"""

from __future__ import annotations

import pytest

from xerocr.evaluation.context import DocContext
from xerocr.evaluation.metrics.text import cer, mer, wer

jiwer = pytest.importorskip("jiwer")

_PAIRS = [
    ("le chat noir", "le chien noir"),
    ("Icy commence le prologue", "Icy commence le prologve"),
    ("maistre Jehan Froissart", "maistre Jehan Froiart"),
    ("hello world here", "world here"),
    ("transcription test case", "transcryption test case"),
]


def _ctx(reference: str, hypothesis: str) -> DocContext:
    return DocContext(document_id="d", reference=reference, hypothesis=hypothesis)


@pytest.mark.parametrize(("ref", "hyp"), _PAIRS)
def test_cer_matches_jiwer(ref: str, hyp: str) -> None:
    assert cer.fn(_ctx(ref, hyp)) == pytest.approx(jiwer.cer(ref, hyp))


@pytest.mark.parametrize(("ref", "hyp"), _PAIRS)
def test_wer_matches_jiwer(ref: str, hyp: str) -> None:
    assert wer.fn(_ctx(ref, hyp)) == pytest.approx(jiwer.wer(ref, hyp))


@pytest.mark.parametrize(("ref", "hyp"), _PAIRS)
def test_mer_matches_jiwer(ref: str, hyp: str) -> None:
    assert mer.fn(_ctx(ref, hyp)) == pytest.approx(jiwer.mer(ref, hyp))
