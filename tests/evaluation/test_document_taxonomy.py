"""Taxonomie d'erreurs par document : non poolée, par pipeline, déterministe."""

from __future__ import annotations

from xerocr.evaluation.document_taxonomy import DocumentTaxonomyCollector


def test_none_when_no_errors() -> None:
    c = DocumentTaxonomyCollector()
    c.observe("tess", "d1", "abc", "abc")  # parfait → aucune erreur
    assert c.build("text") is None


def test_per_document_per_pipeline_profile() -> None:
    c = DocumentTaxonomyCollector()
    c.observe("tess", "doc1", "été", "ete")  # diacritiques
    c.observe("pero", "doc1", "abc", "abc")  # parfait
    c.observe("tess", "doc2", "Mot", "mot")  # casse
    payload = c.build("text").payload  # type: ignore[union-attr]
    docs = {d.document_id: d for d in payload.documents}
    assert set(docs) == {"doc1", "doc2"}  # par document
    # doc1 n'a que tess (pero parfait → exclu, total 0)
    assert [p.pipeline for p in docs["doc1"].pipelines] == ["tess"]
    labels = {c.label for c in docs["doc1"].pipelines[0].counts}
    assert "diacritic" in labels  # classe attendue
    assert docs["doc1"].pipelines[0].total_errors >= 1


def test_deterministic() -> None:
    def run() -> object:
        c = DocumentTaxonomyCollector()
        c.observe("a", "d1", "été", "ete")
        c.observe("b", "d1", "Mot", "mot")
        return c.build("text")

    assert run() == run()
