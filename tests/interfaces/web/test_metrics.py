"""Observabilité ``/metrics`` opt-in : compteur déterministe + endpoint gardé."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.metrics import RequestMetrics


def _client(tmp_path: Path, *, metrics: bool | None = None) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path, rate_limit=1000, metrics=metrics)
    )


def test_request_metrics_render_is_deterministic_and_prometheus() -> None:
    m = RequestMetrics()
    m.record("GET", 200)
    m.record("GET", 200)
    m.record("POST", 403)
    text = m.render()
    assert "# TYPE xerocr_requests_total counter" in text
    assert 'xerocr_requests_total{method="GET",status="200"} 2' in text
    assert 'xerocr_requests_total{method="POST",status="403"} 1' in text
    assert m.render() == text  # déterministe (clés triées)


def test_metrics_endpoint_absent_by_default(tmp_path: Path) -> None:
    # Un Space exposé ne publie pas ses stats sans opt-in explicite.
    assert _client(tmp_path).get("/metrics").status_code == 404


def test_metrics_endpoint_opt_in_counts_requests(tmp_path: Path) -> None:
    client = _client(tmp_path, metrics=True)
    client.get("/health")
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain; version=0.0.4")
    # Les 2 /health (200) sont comptés (≥ 2 — l'ordre des requêtes peut varier).
    assert 'method="GET",status="200"' in resp.text


def test_metrics_opt_in_via_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XEROCR_METRICS", "true")
    client = TestClient(create_app(reports_dir=tmp_path, rate_limit=1000))
    assert client.get("/metrics").status_code == 200
