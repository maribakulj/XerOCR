"""Section duel par document : graphe haltère du CER par moteur et document."""

from __future__ import annotations

from datetime import UTC, datetime

from cinoc.domain.run import RunManifest
from cinoc.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from cinoc.reports.section import SectionContext
from cinoc.reports.sections.engine_duel import EngineDuelSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id,
        pipeline=pipeline,
        view="text",
        scores=(MetricScore(metric="cer", value=cer, support=100),),
    )


def _result(docs: tuple[RunDocumentResult, ...]) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=2,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    pipelines = tuple(
        PipelineResult(pipeline=p, view="text")
        for p in dict.fromkeys(d.pipeline for d in docs)
    )
    return RunResult(manifest=manifest, pipelines=pipelines, documents=docs)


def test_duel_one_row_per_complete_document() -> None:
    docs = (
        _doc("d1", "tesseract", 0.10), _doc("d1", "pero", 0.30),
        _doc("d2", "tesseract", 0.20), _doc("d2", "pero", 0.22),
    )
    html = EngineDuelSection().render(_result(docs), SectionContext())
    assert html is not None
    assert "dumb-svg" in html
    assert html.count('class="dumb-dot"') == 4  # 2 docs × 2 moteurs
    assert "Duel par document" in html
    # tri par écart : d1 (0.20) avant d2 (0.02) → d1 en premier dans le markup.
    assert html.index(">d1<") < html.index(">d2<")


def test_none_with_single_engine() -> None:
    docs = (_doc("d1", "tesseract", 0.10), _doc("d2", "tesseract", 0.20))
    assert EngineDuelSection().render(_result(docs), SectionContext()) is None


def test_none_without_documents() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=0,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    empty = RunResult(manifest=manifest)
    assert EngineDuelSection().render(empty, SectionContext()) is None
