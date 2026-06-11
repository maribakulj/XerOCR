"""Collecteur de textes complets : top-N pires, troncature, déterminisme."""

from __future__ import annotations

from xerocr.evaluation.analysis import DocumentTextsPayload
from xerocr.evaluation.document_texts import DocumentTextsCollector


def test_none_when_nothing_observed() -> None:
    assert DocumentTextsCollector().build("text") is None


def test_keeps_worst_first_and_orders_hypotheses() -> None:
    c = DocumentTextsCollector()
    c.observe("tesseract", "good", "ref", "ref", 0.02)
    c.observe("pero", "good", "ref", "ref", 0.01)
    c.observe("tesseract", "bad", "ref", "rxf", 0.40)
    c.observe("pero", "bad", "ref", "ref", 0.10)
    analysis = c.build("text")
    assert analysis is not None
    payload = analysis.payload
    assert isinstance(payload, DocumentTextsPayload)
    # ordre = CER moyen décroissant → 'bad' (0.25) avant 'good' (0.015)
    assert [d.document_id for d in payload.documents] == ["bad", "good"]
    # hypothèses ordonnées par pipeline (déterminisme)
    assert [p for p, _ in payload.documents[0].hypotheses] == ["pero", "tesseract"]


def test_truncates_long_texts() -> None:
    c = DocumentTextsCollector()
    c.observe("t", "d", "x" * 20000, "y" * 20000, 0.5)
    payload = c.build("text").payload  # type: ignore[union-attr]
    assert isinstance(payload, DocumentTextsPayload)
    assert len(payload.documents[0].reference) == 8000  # tronqué au plafond
    assert len(payload.documents[0].hypotheses[0][1]) == 8000


def test_deterministic() -> None:
    def run() -> object:
        c = DocumentTextsCollector()
        c.observe("a", "d1", "r", "h", 0.3)
        c.observe("b", "d1", "r", "h2", 0.1)
        return c.build("text")

    assert run() == run()
