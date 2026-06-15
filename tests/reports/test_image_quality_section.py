"""Section qualité d'image : table par document + agrégats, ``None`` sans payload."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    DocumentImageQuality,
    ImageQualityPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.image_quality import ImageQualitySection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _manifest() -> RunManifest:
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )


def _result() -> RunResult:
    payload = ImageQualityPayload(
        documents=(
            DocumentImageQuality(
                document_id="folio_001",
                sharpness=0.85,
                noise=0.0,
                contrast=1.0,
                rotation_degrees=0.0,
                quality_score=0.94,
                tier="good",
            ),
            DocumentImageQuality(
                document_id="folio_002",
                sharpness=0.1,
                noise=0.5,
                contrast=0.2,
                rotation_degrees=-3.0,
                quality_score=0.25,
                tier="poor",
            ),
        ),
        mean_quality=0.595,
        mean_sharpness=0.475,
        mean_noise=0.25,
        mean_contrast=0.6,
        n_good=1,
        n_medium=0,
        n_poor=1,
    )
    return RunResult(
        manifest=_manifest(),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_image_quality_renders() -> None:
    html = ImageQualitySection().render(_result(), SectionContext())
    assert html is not None
    assert "Qualité des images" in html
    assert "folio_001" in html
    assert "folio_002" in html
    assert "0.94" in html  # score qualité du 1er document
    assert "bon" in html  # palier good → libellé FR
    assert "faible" in html  # palier poor → libellé FR
    assert "-3.0°" in html  # inclinaison signée
    # Pédagogie R8 : les pondérations/paliers sont des conventions éditoriales.
    assert "conventions éditoriales" in html
    # Agrégats corpus.
    assert "bon 1 / moyen 0 / faible 1" in html
    # Déterminisme bit-à-bit.
    assert html == ImageQualitySection().render(_result(), SectionContext())


def test_renders_english_labels() -> None:
    html = ImageQualitySection().render(_result(), SectionContext(lang="en"))
    assert html is not None
    assert "Image quality" in html and "Qualité des images" not in html
    assert "editorial conventions" in html and "conventions éditoriales" not in html
    assert "sharpness" in html and "netteté" not in html
    assert "good 1 / medium 0 / poor 1" in html
    assert "bon 1 / moyen 0 / faible 1" not in html


def test_no_payload_returns_none() -> None:
    section = ImageQualitySection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
