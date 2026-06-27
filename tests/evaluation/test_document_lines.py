"""Collecteur CER par ligne et par document : non poolé, déterministe, enabled."""

from __future__ import annotations

from cinoc.evaluation.analysis import DocumentLinesPayload
from cinoc.evaluation.document_lines import DocumentLinesCollector


def test_none_when_nothing_observed() -> None:
    assert DocumentLinesCollector().build("text") is None


def test_disabled_is_noop() -> None:
    c = DocumentLinesCollector(enabled=False)
    c.observe("tess", "d1", "a\nb", "x\ny")
    assert c.build("text") is None


def test_per_document_per_pipeline_line_cers() -> None:
    c = DocumentLinesCollector()
    # doc1 : ligne 1 parfaite, ligne 2 fautive (1/3 caractères faux)
    c.observe("tess", "doc1", "abc\ndef", "abc\ndxf")
    c.observe("pero", "doc1", "abc\ndef", "abc\ndef")
    c.observe("tess", "doc2", "ghi", "ghi")
    payload = c.build("text").payload  # type: ignore[union-attr]
    assert isinstance(payload, DocumentLinesPayload)
    docs = {d.document_id: d for d in payload.documents}
    assert set(docs) == {"doc1", "doc2"}  # par document
    pipes = dict(docs["doc1"].pipelines)
    assert set(pipes) == {"pero", "tess"}  # par pipeline, ordonné
    assert pipes["tess"][0] == 0.0  # ligne 1 parfaite
    assert pipes["tess"][1] > 0.0  # ligne 2 fautive
    assert pipes["pero"] == (0.0, 0.0)  # pero parfait sur doc1


def test_deterministic() -> None:
    def run() -> object:
        c = DocumentLinesCollector()
        c.observe("a", "d1", "x\ny", "x\nz")
        c.observe("b", "d1", "x\ny", "x\ny")
        return c.build("text")

    assert run() == run()
