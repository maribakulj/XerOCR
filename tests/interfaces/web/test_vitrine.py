"""Vitrine : liste, rendu HTML d'un ``RunResult`` sauvé, accueil, sécurité chemins."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.app.results import dump_run_result
from xerocr.domain.run import RunManifest, utcnow
from xerocr.evaluation.result import RunResult
from xerocr.interfaces.web.app import create_app


def _write_report(reports_dir: Path, name: str = "run1") -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest = RunManifest(
        run_id=name,
        corpus_name="c",
        n_documents=0,
        code_version="1.0",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    dump_run_result(RunResult(manifest=manifest), reports_dir / f"{name}.json")


def _client(reports_dir: Path) -> TestClient:
    return TestClient(create_app(reports_dir=reports_dir))


def test_lists_reports_sorted(tmp_path: Path) -> None:
    _write_report(tmp_path, "run2")
    _write_report(tmp_path, "run1")
    resp = _client(tmp_path).get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == {"reports": ["run1", "run2"]}


def test_missing_dir_lists_nothing(tmp_path: Path) -> None:
    resp = _client(tmp_path / "absent").get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == {"reports": []}


def test_renders_report_as_html(tmp_path: Path) -> None:
    _write_report(tmp_path, "run1")
    resp = _client(tmp_path).get("/reports/run1")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert resp.text.startswith("<!DOCTYPE html>")


def test_unknown_report_is_404(tmp_path: Path) -> None:
    _write_report(tmp_path, "run1")
    assert _client(tmp_path).get("/reports/nope").status_code == 404


def test_path_traversal_is_blocked(tmp_path: Path) -> None:
    # une tentative de sortie du dossier ne doit JAMAIS réussir (jamais 200).
    resp = _client(tmp_path).get("/reports/..%2f..%2f..%2fetc%2fpasswd")
    assert resp.status_code != 200


def test_home_lists_and_links_reports(tmp_path: Path) -> None:
    _write_report(tmp_path, "run1")
    resp = _client(tmp_path).get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert 'href="/reports/run1"' in resp.text


def test_home_empty_when_no_reports(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/")
    assert resp.status_code == 200
    assert "aucun rapport" in resp.text
