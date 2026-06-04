"""API Historique (lecture seule) : série chronologique + régressions (S6)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.routers.history import build_history_router


def _rec(run_id: str, when: str, value: float) -> HistoryRecord:
    return HistoryRecord(
        run_id=run_id,
        completed_at=when,
        corpus_name="corpusA",
        code_version="0.1.0",
        pipeline="tesseract",
        view="text",
        metric="cer",
        value=value,
    )


def _seeded_client(tmp_path: Path) -> TestClient:
    store = HistoryStore(tmp_path / "h.db")
    store.add(
        [
            _rec("r1", "2026-01-01T00:00:00+00:00", 0.10),
            _rec("r2", "2026-02-01T00:00:00+00:00", 0.15),
        ]
    )
    app = FastAPI()
    app.include_router(build_history_router(store))
    return TestClient(app)


def test_series_is_chronological(tmp_path: Path) -> None:
    resp = _seeded_client(tmp_path).get(
        "/api/history/series",
        params={"pipeline": "tesseract", "view": "text", "metric": "cer"},
    )
    assert resp.status_code == 200
    assert [row["value"] for row in resp.json()] == [0.10, 0.15]


def test_regressions_reports_worsening(tmp_path: Path) -> None:
    resp = _seeded_client(tmp_path).get(
        "/api/history/regressions", params={"view": "text", "metric": "cer"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["pipeline"] == "tesseract"
    assert data[0]["latest"] == 0.15
    assert data[0]["previous"] == 0.10


def test_regressions_requires_view(tmp_path: Path) -> None:
    # ``view`` est un paramètre requis → 422 sans lui.
    assert _seeded_client(tmp_path).get("/api/history/regressions").status_code == 422


def test_history_mounted_in_app(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            reports_dir=tmp_path / "rep",
            uploads_dir=tmp_path / "up",
            rate_limit=1000,
        )
    )
    resp = client.get(
        "/api/history/regressions", params={"view": "text", "metric": "cer"}
    )
    assert resp.status_code == 200 and resp.json() == []
