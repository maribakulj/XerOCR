"""Page « Moteurs » (S2.2a) : rendu serveur, aucun JS — entièrement testable."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path, rate_limit=1000, public_mode=public_mode)
    )


def test_engines_page_lists_socle(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/engines")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    for label in ("Pré-calculé", "Tesseract", "OpenAI", "Ollama"):
        assert label in body


def test_engines_page_nav_active_and_no_script(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/engines").text
    assert "<script" not in body  # 100 % rendu serveur, aucun JS


def test_engines_reachable_via_system_details_not_nav(tmp_path: Path) -> None:
    home = _client(tmp_path).get("/").text
    # Comme Picarones : « Moteurs » n'est pas une pastille de nav, mais est
    # accessible via le bouton « Système · détails → » du rail.
    assert 'class="system-trigger" href="/engines?lang=fr"' in home
    assert 'nav-item" href="/engines' not in home
    assert 'nav-item active" href="/engines' not in home


def test_cloud_engine_unavailable_without_key(tmp_path: Path) -> None:
    body = _client(tmp_path, public_mode=True).get("/engines").text
    # openai (cloud) apparaît indisponible faute de clé — plus de motif « mode
    # public » : la disponibilité ne dépend que du SDK + clé.
    assert "indisponible" in body


def test_engines_page_english(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/engines?lang=en").text
    assert "Engines" in body
    assert "available" in body or "unavailable" in body
