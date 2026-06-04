"""Trait d'union ``RunResult`` → historique : extraction + enregistrement."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from xerocr.adapters.storage.history_store import HistoryStore
from xerocr.app.history import record_run, records_from_run
from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult


def _run(run_id: str, cer: float, when: datetime) -> RunResult:
    manifest = RunManifest(
        run_id=run_id,
        corpus_name="corpusA",
        n_documents=2,
        code_version="0.1.0",
        started_at=when,
        completed_at=when,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="tesseract",
                view="text",
                aggregate=(
                    MetricScore(metric="cer", value=cer, support=2),
                    MetricScore(metric="wer", value=None),  # non applicable → ignoré
                ),
            ),
        ),
    )


def test_records_from_run_skips_none() -> None:
    recs = records_from_run(_run("r1", 0.1, datetime(2026, 1, 1, tzinfo=UTC)))
    assert len(recs) == 1  # wer None écarté
    rec = recs[0]
    assert rec.metric == "cer" and rec.value == 0.1
    assert rec.run_id == "r1" and rec.corpus_name == "corpusA"
    assert rec.code_version == "0.1.0" and rec.pipeline == "tesseract"


def test_record_run_then_query_and_regression(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    assert record_run(store, _run("r1", 0.10, datetime(2026, 1, 1, tzinfo=UTC))) == 1
    record_run(store, _run("r2", 0.20, datetime(2026, 2, 1, tzinfo=UTC)))

    hist = store.history("tesseract", "text", "cer")
    assert [r.value for r in hist] == [0.10, 0.20]

    regs = store.regressions("text", "cer")
    assert len(regs) == 1 and regs[0].latest == 0.20
