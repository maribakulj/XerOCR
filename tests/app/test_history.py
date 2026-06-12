"""Trait d'union ``RunResult`` ↔ historique : enregistrement + analyse de série."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.app.history import record_run, records_from_run, series_insight
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


def _record(run_id: str, completed_at: str, value: float) -> HistoryRecord:
    return HistoryRecord(
        run_id=run_id,
        completed_at=completed_at,
        corpus_name="c",
        code_version="1.0",
        pipeline="tesseract",
        view="text",
        metric="cer",
        value=value,
    )


def test_series_insight_trend_and_significant_shift() -> None:
    # 6 runs à 0.30 puis 6 à 0.10 (un jour d'écart) : tendance descendante,
    # rupture Pettitt significative — le premier run du nouveau régime est r07.
    records = [
        _record(f"r{i + 1:02d}", f"2026-01-{i + 1:02d}T00:00:00", value)
        for i, value in enumerate([0.30] * 6 + [0.10] * 6)
    ]
    insight = series_insight(records)
    assert insight.trend is not None
    assert insight.trend.slope_per_day < 0 and insight.trend.n_points == 12
    assert insight.rupture is not None and insight.rupture.significant
    assert insight.rupture.delta == pytest.approx(-0.2)
    assert insight.rupture_run_id == "r07"


def test_series_insight_sorts_chronologically() -> None:
    # L'analyse trie elle-même (Pettitt dépend de l'ordre) : entrée renversée
    # → même verdict que l'entrée chronologique.
    records = [
        _record(f"r{i + 1:02d}", f"2026-01-{i + 1:02d}T00:00:00", value)
        for i, value in enumerate([0.30] * 6 + [0.10] * 6)
    ]
    assert series_insight(list(reversed(records))) == series_insight(records)


def test_series_insight_skips_unreadable_timestamp_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    records = [
        _record("r1", "2026-01-01T00:00:00", 0.30),
        _record("rX", "pas-une-date", 0.99),
        _record("r2", "2026-01-02T00:00:00", 0.20),
    ]
    with caplog.at_level(logging.WARNING):
        insight = series_insight(records)
    assert "horodatage illisible" in caplog.text and "rX" in caplog.text
    assert insight.trend is not None and insight.trend.n_points == 2


def test_series_insight_short_series_degrades_to_none() -> None:
    insight = series_insight([_record("r1", "2026-01-01T00:00:00", 0.30)])
    assert insight.trend is None
    assert insight.rupture is None
    assert insight.rupture_run_id is None
