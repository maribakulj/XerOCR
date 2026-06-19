"""Hallucination par document : passages **insérés** (≠ mots mal lus), déterminisme."""

from __future__ import annotations

from xerocr.evaluation.document_hallucination import DocumentHallucinationCollector


def test_none_when_nothing_observed() -> None:
    assert DocumentHallucinationCollector().build("text") is None


def test_correct_output_has_no_insertion() -> None:
    c = DocumentHallucinationCollector()
    text = "le budget de la ville pour l année"
    c.observe("tess", "d1", text, text)  # sortie = GT → aucun insert
    assert c.build("text") is None


def test_misread_is_not_a_hallucination() -> None:
    c = DocumentHallucinationCollector()
    # mots mal lus = substitutions (alignées face au GT), PAS des insertions
    c.observe("tess", "d1", "le budget de la ville", "le budjet de la villle")
    assert c.build("text") is None


def test_inserted_passage_is_flagged() -> None:
    c = DocumentHallucinationCollector()
    gt = "le budget de la ville"
    # une phrase ajoutée (≥ 4 mots contigus absents du GT) entre du texte ancré
    hyp = "le budget puis vint la grande inondation imprévue de la ville"
    c.observe("llm", "d1", gt, hyp)
    payload = c.build("text").payload  # type: ignore[union-attr]
    ph = payload.documents[0].pipelines[0]
    assert ph.is_hallucinating and ph.blocks
    assert "grande inondation imprévue" in ph.blocks[0].text
    assert ph.net_insertion_rate > 0.0


def test_short_spurious_word_below_threshold_not_flagged() -> None:
    c = DocumentHallucinationCollector()
    # un seul mot parasite inséré (< _MIN_INSERT) → pas signalé comme passage
    c.observe("tess", "d1", "le budget de la ville", "le budget de la xyz ville")
    assert c.build("text") is None


def test_only_documents_with_insertion_kept_and_sorted() -> None:
    c = DocumentHallucinationCollector()
    c.observe("tess", "clean", "a b c d e", "a b c d e")  # rien → omis
    c.observe("llm", "halluc", "a b", "a b puis une longue invention ajoutee ici")
    payload = c.build("text").payload  # type: ignore[union-attr]
    assert [d.document_id for d in payload.documents] == ["halluc"]


def test_deterministic() -> None:
    def run() -> object:
        c = DocumentHallucinationCollector()
        c.observe("a", "d1", "le chat", "le chat puis une longue phrase inventee ici")
        return c.build("text")

    assert run() == run()
