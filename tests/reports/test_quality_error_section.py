"""Section qualité × erreur : nuage de bulles document (qualité × CER × volume)."""

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
from xerocr.reports.sections.quality_error import QualityErrorSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id,
        pipeline=pipeline,
        view="text",
        scores=(MetricScore(metric="cer", value=cer, support=120),),
    )


def _iq(*ids: str) -> ImageQualityPayload:
    docs = tuple(
        DocumentImageQuality(
            document_id=i, sharpness=0.7, noise=0.1, contrast=0.6,
            rotation_degrees=0.0, quality_score=0.6, tier="medium",
        )
        for i in ids
    )
    return ImageQualityPayload(
        documents=docs, mean_quality=0.6, mean_sharpness=0.7,
        mean_noise=0.1, mean_contrast=0.6, n_good=0, n_medium=len(ids), n_poor=0,
    )


def _result(*, with_quality: bool) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=2,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    pipelines = (
        PipelineResult(pipeline="tesseract", view="text"),
        PipelineResult(pipeline="pero", view="text"),
    )
    docs = (
        _doc("d1", "tesseract", 0.10), _doc("d2", "tesseract", 0.30),
        _doc("d1", "pero", 0.05), _doc("d2", "pero", 0.15),
    )
    analyses = (
        (Analysis(scope="corpus", view="text", payload=_iq("d1", "d2")),)
        if with_quality
        else ()
    )
    return RunResult(
        manifest=manifest, pipelines=pipelines, documents=docs, analyses=analyses
    )


def test_density_bubbles_binned() -> None:
    html = QualityErrorSection().render(_result(with_quality=True), SectionContext())
    assert html is not None
    assert "bubble-svg" in html
    # 4 couples (doc×moteur) dans des cellules distinctes → 4 bulles ; bornées par
    # la grille, pas par le nombre de couples (invariant d'échelle).
    assert html.count('class="bubble-dot"') == 4
    assert "Qualité × erreur" in html
    assert "4 couples" in html  # densité, moteurs poolés (plus de légende/moteur)


def test_density_bubble_count_bounded_at_scale() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=400,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    pipelines = (PipelineResult(pipeline="tesseract", view="text"),)
    docs = tuple(_doc(f"d{i}", "tesseract", (i % 50) / 100.0) for i in range(400))
    iq = _iq(*[f"d{i}" for i in range(400)])
    result = RunResult(
        manifest=manifest, pipelines=pipelines, documents=docs,
        analyses=(Analysis(scope="corpus", view="text", payload=iq),),
    )
    html = QualityErrorSection().render(result, SectionContext())
    assert html is not None
    assert html.count('class="bubble-dot"') <= 24 * 24  # borné par la grille


def test_none_without_image_quality_payload() -> None:
    assert (
        QualityErrorSection().render(_result(with_quality=False), SectionContext())
        is None
    )
