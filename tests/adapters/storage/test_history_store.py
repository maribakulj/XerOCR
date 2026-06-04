"""``HistoryStore`` sur **vrai SQLite** : round-trip, idempotence, régressions."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore


def _rec(run_id: str, when: str, value: float, *, metric: str = "cer") -> HistoryRecord:
    return HistoryRecord(
        run_id=run_id,
        completed_at=when,
        corpus_name="corpusA",
        code_version="0.1.0",
        pipeline="tesseract",
        view="text",
        metric=metric,
        value=value,
    )


def test_round_trip_chronological(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    assert store.add([_rec("r2", "2026-02-01T00:00:00+00:00", 0.15)]) == 1
    store.add([_rec("r1", "2026-01-01T00:00:00+00:00", 0.10)])
    hist = store.history("tesseract", "text", "cer")
    assert [r.run_id for r in hist] == ["r1", "r2"]  # trié par completed_at
    assert hist[1].value == pytest.approx(0.15)


def test_re_record_is_idempotent(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add([_rec("r1", "2026-01-01T00:00:00+00:00", 0.10)])
    store.add([_rec("r1", "2026-01-01T00:00:00+00:00", 0.10)])  # même PK
    assert len(store.history("tesseract", "text", "cer")) == 1


def test_persists_across_instances(tmp_path: Path) -> None:
    db = tmp_path / "h.db"
    HistoryStore(db).add([_rec("r1", "2026-01-01T00:00:00+00:00", 0.10)])
    assert len(HistoryStore(db).history("tesseract", "text", "cer")) == 1


def test_regression_detected_when_cer_worsens(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add(
        [
            _rec("r1", "2026-01-01T00:00:00+00:00", 0.10),
            _rec("r2", "2026-02-01T00:00:00+00:00", 0.15),
        ]
    )
    regs = store.regressions("text", "cer")
    assert len(regs) == 1
    reg = regs[0]
    assert reg.pipeline == "tesseract"
    assert (reg.previous, reg.latest) == (pytest.approx(0.10), pytest.approx(0.15))
    assert reg.delta == pytest.approx(0.05)
    assert (reg.previous_run_id, reg.latest_run_id) == ("r1", "r2")


def test_improvement_is_not_a_regression(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add(
        [
            _rec("r1", "2026-01-01T00:00:00+00:00", 0.20),
            _rec("r2", "2026-02-01T00:00:00+00:00", 0.10),
        ]
    )
    assert store.regressions("text", "cer") == ()


def test_threshold_filters_small_changes(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add(
        [
            _rec("r1", "2026-01-01T00:00:00+00:00", 0.10),
            _rec("r2", "2026-02-01T00:00:00+00:00", 0.13),
        ]
    )
    assert store.regressions("text", "cer", threshold=0.05) == ()
    assert len(store.regressions("text", "cer", threshold=0.01)) == 1


def test_higher_is_better_inverts_direction(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add(
        [
            _rec("r1", "2026-01-01T00:00:00+00:00", 0.90, metric="accuracy"),
            _rec("r2", "2026-02-01T00:00:00+00:00", 0.80, metric="accuracy"),
        ]
    )
    # accuracy qui baisse = régression seulement si higher_is_better
    assert store.regressions("text", "accuracy", higher_is_better=True)
    assert store.regressions("text", "accuracy") == ()


def test_single_run_has_no_regression(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add([_rec("r1", "2026-01-01T00:00:00+00:00", 0.10)])
    assert store.regressions("text", "cer") == ()
