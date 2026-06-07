"""Historique : sparklines CER (tendances) rendues **serveur** depuis le store."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.app.segmentation import SegmentationStore, demo_layout
from xerocr.interfaces.web.app import _TEMPLATES_DIR
from xerocr.interfaces.web.routers.home import build_home_router


def _history_body(tmp_path: Path, store: HistoryStore) -> str:
    seg = SegmentationStore(tmp_path / "seg")
    seg_id = seg.save(demo_layout())
    app = FastAPI()
    app.include_router(
        build_home_router(
            tmp_path / "reports",
            Jinja2Templates(directory=_TEMPLATES_DIR),
            statuses=lambda: (),
            segmenters=lambda: (),
            history_store=store,
            segmentation_store=seg,
            demo_segmentation_id=seg_id,
        )
    )
    return TestClient(app).get("/history").text


def _rec(run_id: str, ts: str, value: float) -> HistoryRecord:
    return HistoryRecord(
        run_id=run_id,
        completed_at=ts,
        corpus_name="c",
        code_version="1.0",
        pipeline="tesseract",
        view="text",
        metric="cer",
        value=value,
    )


def test_history_renders_cer_sparkline(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "h.db")
    store.add(
        [
            _rec("r1", "2026-01-01T00:00:00", 0.30),
            _rec("r2", "2026-02-01T00:00:00", 0.20),
        ]
    )
    body = _history_body(tmp_path, store)
    assert "Tendances" in body  # section des tendances
    assert 'class="spark"' in body  # sparkline SVG rendue serveur
    assert "<polyline" in body  # 2 points → courbe
    assert "tesseract" in body


def test_history_no_sparkline_when_empty(tmp_path: Path) -> None:
    body = _history_body(tmp_path, HistoryStore(tmp_path / "h.db"))
    assert 'class="spark"' not in body  # aucune tendance sans donnée
