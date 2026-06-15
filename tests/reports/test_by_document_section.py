"""Section by-document : groupage par document, data-bars, vide → ``None``."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.by_document import DocumentSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float | None) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id,
        pipeline=pipeline,
        view="text",
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


def test_renders_per_document_rows_with_grouping() -> None:
    html = DocumentSection().render(
        _result(
            _doc("folio_1", "tesseract", 0.10),
            _doc("folio_1", "pero", 0.05),
            _doc("folio_2", "tesseract", 0.20),
        ),
        SectionContext(),
    )
    assert html is not None
    assert "Vue :" in html  # tables par vue (le titre de vue est dans le héros)
    # les deux documents et les deux pipelines apparaissent
    for token in ("folio_1", "folio_2", "tesseract", "pero"):
        assert token in html
    # nom de document **groupé** : affiché une seule fois malgré 2 lignes
    assert html.count("folio_1") == 1
    # data-bar relative au max de la colonne (0.20) : 0.10 → 50 %, 0.20 → 100 %
    assert 'style="width:50%"' in html
    assert 'style="width:100%"' in html


def test_renders_english_labels() -> None:
    html = DocumentSection().render(
        _result(_doc("folio_1", "tesseract", 0.10)),
        SectionContext(lang="en"),
    )
    assert html is not None
    assert "View :" in html and "Vue :" not in html


def test_none_value_rendered_as_dash() -> None:
    result = _result(_doc("f", "tesseract", None))
    html = DocumentSection().render(result, SectionContext())
    assert html is not None
    assert "—" in html


def test_no_documents_returns_none() -> None:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    # des pipelines mais aucun détail par-document → section absente (no-orphan)
    result = RunResult(
        manifest=manifest,
        pipelines=(PipelineResult(pipeline="t", view="text"),),
    )
    assert DocumentSection().render(result, SectionContext()) is None
