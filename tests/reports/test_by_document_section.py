"""Section by-document : distribution de difficulté (tout le corpus) + table des
documents notables, bornée (invariant d'échelle), vide → ``None``."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports._doc_highlights import HIGHLIGHTS_PER_GROUP
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.by_document import DocumentSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(
    doc_id: str, pipeline: str, cer: float | None, view: str = "text"
) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id,
        pipeline=pipeline,
        view=view,
        scores=(MetricScore(metric="cer", value=cer, support=1),),
    )


def _result(*documents: RunDocumentResult) -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(manifest=manifest, documents=documents)


def test_renders_distribution_and_notable_table() -> None:
    html = DocumentSection().render(
        _result(
            _doc("folio_1", "tesseract", 0.10),
            _doc("folio_1", "pero", 0.05),
            _doc("folio_2", "tesseract", 0.40),
            _doc("folio_2", "pero", 0.20),
        ),
        SectionContext(),
    )
    assert html is not None
    # (1) distribution : histogramme couvrant tout le corpus
    assert "Distribution de la difficulté" in html
    assert "bars-svg" in html
    assert "2 documents" in html
    # (2) table des documents notables (exemples), avec catégorie
    assert "Documents notables" in html
    for token in ("folio_1", "folio_2", "tesseract", "pero", "catégorie"):
        assert token in html


def test_returns_none_without_cer() -> None:
    # aucun CER par document → rien à distribuer ni à classer (no-orphan)
    result = _result(_doc("f", "tesseract", None), _doc("f", "pero", None))
    assert DocumentSection().render(result, SectionContext()) is None


def test_notable_table_is_bounded_at_scale() -> None:
    # 500 documents → la table reste bornée (≤ 3 groupes × HIGHLIGHTS_PER_GROUP) et
    # la distribution reste UN seul histogramme : invariant d'échelle.
    docs = [
        _doc(f"d{i:04d}", eng, (i % 97) / 100.0)
        for i in range(500)
        for eng in ("tesseract", "pero")
    ]
    html = DocumentSection().render(_result(*docs), SectionContext())
    assert html is not None
    body_rows = html.count("<tr>")
    assert 0 < body_rows <= 3 * HIGHLIGHTS_PER_GROUP
    assert html.count("bars-svg") == 1  # une seule distribution
    assert "500 documents" in html


def test_english_labels() -> None:
    html = DocumentSection().render(
        _result(_doc("f1", "tesseract", 0.10), _doc("f2", "tesseract", 0.30)),
        SectionContext(lang="en"),
    )
    assert html is not None
    assert "Difficulty distribution" in html and "Distribution de la" not in html
    assert "Notable documents" in html


def test_is_deterministic_and_escapes_ids() -> None:
    result = _result(_doc("<x>", "tesseract", 0.20), _doc("ok", "tesseract", 0.05))
    html = DocumentSection().render(result, SectionContext())
    assert html is not None
    assert "<x>" not in html and "&lt;x&gt;" in html
    assert html == DocumentSection().render(result, SectionContext())


def test_no_documents_returns_none() -> None:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    result = RunResult(
        manifest=manifest,
        pipelines=(PipelineResult(pipeline="t", view="text"),),
    )
    assert DocumentSection().render(result, SectionContext()) is None
