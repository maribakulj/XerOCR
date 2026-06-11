"""Section by-engine : classement trié par CER + dispersion par-document."""

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
from xerocr.reports.sections.by_engine import EngineSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _agg(pipeline: str, cer: float) -> PipelineResult:
    return PipelineResult(
        pipeline=pipeline,
        view="text",
        aggregate=(MetricScore(metric="cer", value=cer, support=2),),
    )


def _doc(doc_id: str, pipeline: str, cer: float) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id,
        pipeline=pipeline,
        view="text",
        scores=(MetricScore(metric="cer", value=cer, support=1),),
    )


def _result() -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(_agg("slow", 0.30), _agg("fast", 0.10)),
        documents=(
            _doc("d1", "slow", 0.40),
            _doc("d2", "slow", 0.20),
            _doc("d1", "fast", 0.05),
            _doc("d2", "fast", 0.15),
        ),
    )


def test_engines_ranked_by_cer_ascending() -> None:
    html = EngineSection().render(_result(), SectionContext())
    assert html is not None
    assert "Classement" in html  # titre de carte (le titre de vue est dans le héros)
    # le meilleur (fast, CER 0.10) précède le pire (slow, 0.30)
    assert html.index("fast") < html.index("slow")
    # dispersion de fast : min 0.05 · médiane 0.10 · max 0.15
    assert "0.050" in html and "0.150" in html
    # badge moteur présent, et la lettre suit l'ordre canonique (pas le rang) :
    # `fast` apparaît avant `slow` dans le run → A puis B, même si `fast` gagne.
    assert 'class="eng-badge"' in html


def test_returns_none_without_pipelines() -> None:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=0,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    empty = RunResult(manifest=manifest)
    assert EngineSection().render(empty, SectionContext()) is None
