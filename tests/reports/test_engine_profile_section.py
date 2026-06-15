"""Section profil moteur : panneaux drill-in (KPIs + CER/document, révélés)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    CalibrationBin,
    CalibrationPayload,
    PipelineCalibration,
    PipelineTaxonomy,
    TaxonomyCount,
    TaxonomyPayload,
)
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.engine_profile import EngineProfileSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id,
        pipeline=pipeline,
        view="text",
        scores=(MetricScore(metric="cer", value=cer, support=1),),
    )


def _result() -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=2,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    pipelines = (
        PipelineResult(
            pipeline="tesseract", view="text",
            aggregate=(MetricScore(metric="cer", value=0.20, support=2),),
        ),
        PipelineResult(
            pipeline="pero", view="text",
            aggregate=(MetricScore(metric="cer", value=0.10, support=2),),
        ),
    )
    docs = (
        _doc("d1", "tesseract", 0.10), _doc("d2", "tesseract", 0.30),
        _doc("d1", "pero", 0.05), _doc("d2", "pero", 0.15),
    )
    return RunResult(manifest=manifest, pipelines=pipelines, documents=docs)


def test_one_hidden_panel_per_engine_with_anchor() -> None:
    html = EngineProfileSection().render(_result(), SectionContext())
    assert html is not None
    assert html.count('class="drill-panel eng-profile"') == 2  # un panneau/moteur
    assert 'id="engine-0"' in html and 'id="engine-1"' in html  # ancres drill-in
    assert html.count('hidden role="region"') == 2  # cachés par défaut (au clic)
    assert "← retour au tableau" in html  # retour dispo dans chaque panneau


def test_panel_has_kpi_band_and_cer_chart() -> None:
    html = EngineProfileSection().render(_result(), SectionContext())
    assert html is not None
    assert 'class="kpi-band"' in html and 'class="kpi-v"' in html
    assert "20.0 %" in html  # CER agrégat de tesseract en KPI
    assert 'class="bars-svg"' in html  # graphe CER par document


def test_prev_next_links_cycle() -> None:
    html = EngineProfileSection().render(_result(), SectionContext())
    assert html is not None
    # panneau 0 → suivant #engine-1 ; précédent boucle sur #engine-1
    assert 'href="#engine-1"' in html and 'href="#engine-0"' in html


def test_profile_includes_calibration_and_composition_when_present() -> None:
    base = _result()
    calib = CalibrationPayload(
        n_bins=2,
        pipelines=(
            PipelineCalibration(
                pipeline="tesseract", n_tokens=10, ece=0.08, mce=0.2,
                bins=(
                    CalibrationBin(
                        lower=0.8, upper=1.0, mean_confidence=0.9,
                        accuracy=0.85, count=10,
                    ),
                ),
            ),
        ),
    )
    taxo = TaxonomyPayload(
        classes=("visual", "case"),
        pipelines=(
            PipelineTaxonomy(
                pipeline="tesseract", total_errors=4,
                counts=(
                    TaxonomyCount(label="visual", count=3),
                    TaxonomyCount(label="case", count=1),
                ),
            ),
        ),
    )
    result = base.model_copy(
        update={
            "analyses": (
                Analysis(scope="corpus", view="text", payload=calib),
                Analysis(scope="corpus", view="text", payload=taxo),
            )
        }
    )
    html = EngineProfileSection().render(result, SectionContext())
    assert html is not None
    assert 'class="calib-svg"' in html  # courbe de calibration du moteur
    assert 'class="comp-bar"' in html  # composition d'erreurs du moteur
    assert "8.0 %" in html  # ECE en KPI (réutilise les builders U2b/U2c)


def test_none_without_pipelines() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=0,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    empty = RunResult(manifest=manifest)
    assert EngineProfileSection().render(empty, SectionContext()) is None


def test_deterministic() -> None:
    r = _result()
    a = EngineProfileSection().render(r, SectionContext())
    b = EngineProfileSection().render(r, SectionContext())
    assert a == b


def test_renders_english_labels() -> None:
    html = EngineProfileSection().render(_result(), SectionContext(lang="en"))
    assert html is not None
    # libellés EN introduits…
    assert "Engine profile" in html
    assert "← back to table" in html
    assert "CER per document " in html
    assert "engine 1 of 2" in html
    # … et leurs équivalents FR absents
    assert "Profil moteur" not in html
    assert "← retour au tableau" not in html
    assert "CER par document " not in html
    assert "moteur 1 sur 2" not in html
