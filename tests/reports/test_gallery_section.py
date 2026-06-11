"""Section galerie : cartes par document, CER/badges, meilleur surligné, échappement."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.section import Section, SectionContext
from xerocr.reports.sections.gallery import DocumentGallerySection

FIXED = datetime(2026, 6, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float | None) -> RunDocumentResult:
    score = MetricScore(metric="cer", value=cer, support=1)
    return RunDocumentResult(
        document_id=doc_id, pipeline=pipeline, view="text", scores=(score,)
    )


def _result(*docs: RunDocumentResult) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=2, code_version="1.0",
        started_at=FIXED, completed_at=FIXED,
    )
    pipelines = (
        PipelineResult(
            pipeline="tesseract", view="text",
            aggregate=(MetricScore(metric="cer", value=0.25, support=2),),
        ),
        PipelineResult(
            pipeline="openai", view="text",
            aggregate=(MetricScore(metric="cer", value=0.10, support=1),),
        ),
    )
    return RunResult(manifest=manifest, pipelines=pipelines, documents=docs)


def test_satisfies_section_protocol() -> None:
    section = DocumentGallerySection()
    assert isinstance(section, Section)
    assert section.name == "documents_gallery"


def test_returns_none_without_documents() -> None:
    empty = _result()
    assert DocumentGallerySection().render(empty, SectionContext()) is None


def test_renders_card_per_document_with_cer_and_badges() -> None:
    result = _result(
        _doc("doc1", "tesseract", 0.20),
        _doc("doc1", "openai", 0.10),
        _doc("doc2", "tesseract", 0.30),
    )
    html = DocumentGallerySection().render(result, SectionContext())
    assert html is not None
    assert "Galerie des documents" in html
    assert 'class="doc-grid"' in html
    assert "doc1" in html and "doc2" in html
    assert "doc-preview" in html  # aperçu synthétique (zéro image)
    assert 'class="eng-badge"' in html  # CER par moteur via badges A→E
    assert "0.1000" in html and "0.2000" in html
    # le meilleur moteur du document (openai 0.10 sur doc1) est surligné
    assert "dc-row best" in html


def test_is_deterministic_and_escapes_ids() -> None:
    result = _result(_doc("<x>", "tesseract", 0.20))
    html = DocumentGallerySection().render(result, SectionContext())
    assert html is not None
    assert "<x>" not in html and "&lt;x&gt;" in html  # id échappé (anti-XSS)
    assert html == DocumentGallerySection().render(result, SectionContext())
