"""Détection d'hallucinations par document : ancrage, blocs inventés, déterminisme."""

from __future__ import annotations

from xerocr.evaluation.document_hallucination import DocumentHallucinationCollector


def test_none_when_nothing_observed() -> None:
    assert DocumentHallucinationCollector().build("text") is None


def test_anchored_output_is_not_flagged() -> None:
    c = DocumentHallucinationCollector()
    # sortie = GT → ancrage parfait, pas d'hallucination, aucun bloc
    text = "le chat noir dort sur le mur"
    c.observe("tess", "d1", text, text)  # sortie = GT
    payload = c.build("text").payload  # type: ignore[union-attr]
    ph = payload.documents[0].pipelines[0]
    assert ph.anchor_score == 1.0
    assert not ph.is_hallucinating
    assert ph.blocks == ()


def test_invented_block_detected_and_flagged() -> None:
    c = DocumentHallucinationCollector()
    gt = "le budget de la ville"
    # sortie : mots inventés contigus absents du GT → bloc halluciné + ancrage bas
    hyp = "durch beflhuß vom san lethin haben veröffentlihung budgetd kabr beichlofien"
    c.observe("tess", "d1", gt, hyp)
    payload = c.build("text").payload  # type: ignore[union-attr]
    ph = payload.documents[0].pipelines[0]
    assert ph.is_hallucinating  # ancrage faible
    assert ph.blocks  # au moins un bloc sans ancrage
    assert ph.net_insertion_rate > 0.5
    assert ph.gt_words == 5


def test_per_document_per_pipeline_sorted() -> None:
    c = DocumentHallucinationCollector()
    c.observe("tess", "d2", "a b", "a b")
    c.observe("pero", "d1", "a b", "a b")
    c.observe("tess", "d1", "a b", "a b")
    payload = c.build("text").payload  # type: ignore[union-attr]
    docs = [d.document_id for d in payload.documents]
    assert docs == ["d1", "d2"]  # docs triés
    assert [p.pipeline for p in payload.documents[0].pipelines] == ["pero", "tess"]


def test_deterministic() -> None:
    def run() -> object:
        c = DocumentHallucinationCollector()
        c.observe("a", "d1", "le chat", "le chien xyz abcd efgh ijkl")
        return c.build("text")

    assert run() == run()
