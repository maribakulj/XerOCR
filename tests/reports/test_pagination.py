"""Pagination des longues listes : marqueur ``data-paginate`` présent et — surtout
— **aucun document retiré** (toutes les cartes/lignes restent dans le HTML ; seul
``report.js`` borne l'affichage à une page). Encode l'exigence : à 5000 docs, la
galerie et les tables **contiennent tout**."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    DocumentImageQuality,
    ImageQualityPayload,
)
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.by_document import DocumentSection
from xerocr.reports.sections.gallery import DocumentGallerySection
from xerocr.reports.sections.image_quality import ImageQualitySection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)
_N = 300


def _result() -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=_N, code_version="1.0",
        started_at=FIXED, completed_at=FIXED,
    )
    pipelines = (PipelineResult(
        pipeline="tesseract", view="text",
        aggregate=(MetricScore(metric="cer", value=0.2, support=_N),),
    ),)
    docs = tuple(
        RunDocumentResult(
            document_id=f"doc{i:04d}", pipeline="tesseract", view="text",
            scores=(MetricScore(metric="cer", value=(i % 100) / 100.0, support=10),),
        )
        for i in range(_N)
    )
    iq = ImageQualityPayload(
        documents=tuple(
            DocumentImageQuality(
                document_id=f"doc{i:04d}", sharpness=0.7, noise=0.1, contrast=0.6,
                rotation_degrees=0.0, quality_score=(i % 100) / 100.0, tier="medium",
            )
            for i in range(_N)
        ),
        mean_quality=0.5, mean_sharpness=0.7, mean_noise=0.1, mean_contrast=0.6,
        n_good=0, n_medium=_N, n_poor=0,
    )
    return RunResult(
        manifest=manifest, pipelines=pipelines, documents=docs,
        analyses=(Analysis(scope="corpus", view="text", payload=iq),),
    )


def test_gallery_keeps_all_cards_and_marks_pagination() -> None:
    html = DocumentGallerySection().render(_result(), SectionContext())
    assert html is not None
    assert 'data-paginate="60"' in html
    assert html.count("doc-card") == _N  # TOUTES les cartes présentes, rien retiré


def test_by_document_keeps_all_documents_and_marks_pagination() -> None:
    html = DocumentSection().render(_result(), SectionContext())
    assert html is not None
    assert 'data-paginate="50"' in html
    for i in (0, 150, _N - 1):
        assert f"doc{i:04d}" in html  # documents début/milieu/fin tous présents


def test_image_quality_keeps_all_rows_and_marks_pagination() -> None:
    html = ImageQualitySection().render(_result(), SectionContext())
    assert html is not None
    assert 'data-paginate="50"' in html
    assert html.count("databar") == _N  # une cellule score par document, rien retiré
