"""Collecteur de textes complets : tous les docs, pires-d'abord, déterminisme."""

from __future__ import annotations

from cinoc.evaluation.analysis import _MAX_TEXT_CHARS, DocumentTextsPayload
from cinoc.evaluation.document_texts import DocumentTextsCollector


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


def test_keeps_all_documents_not_just_worst() -> None:
    # Tous les documents scorés sont embarqués (la vue document montre chacun en
    # entier, pas seulement les pires) — pires-d'abord conservé pour l'ordre.
    c = DocumentTextsCollector()
    for i in range(30):
        c.observe("t", f"d{i:02d}", "ref", "rxf", i / 100)
    payload = c.build("text").payload  # type: ignore[union-attr]
    assert isinstance(payload, DocumentTextsPayload)
    assert len(payload.documents) == 30  # aucun plafond de documents
    assert payload.documents[0].document_id == "d29"  # pire (CER 0.29) d'abord


def test_truncates_at_safety_bound() -> None:
    c = DocumentTextsCollector()
    big = _MAX_TEXT_CHARS + 5000
    c.observe("t", "d", "x" * big, "y" * big, 0.5)
    payload = c.build("text").payload  # type: ignore[union-attr]
    assert isinstance(payload, DocumentTextsPayload)
    assert len(payload.documents[0].reference) == _MAX_TEXT_CHARS  # borne de sûreté
    assert len(payload.documents[0].hypotheses[0][1]) == _MAX_TEXT_CHARS


def test_deterministic() -> None:
    def run() -> object:
        c = DocumentTextsCollector()
        c.observe("a", "d1", "r", "h", 0.3)
        c.observe("b", "d1", "r", "h2", 0.1)
        return c.build("text")

    assert run() == run()
