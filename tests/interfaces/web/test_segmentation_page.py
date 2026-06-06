"""Écran segmentation (S6) : page rendue serveur + endpoint image, anti-traversal."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(reports_dir=tmp_path, rate_limit=1000))


def test_segmentation_page_renders_regions_and_svg(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/segmentation")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "<svg" in body  # le SVG de régions est rendu serveur (inline)
    assert "seg-svg" in body
    # les 3 régions de la démo apparaissent (id + type)
    for token in ("r1", "r2", "r3", "title", "paragraph", "figure"):
        assert token in body
    # le fond pointe vers l'endpoint image (infra exercée, pas dormante)
    assert "/api/segmentation/" in body
    assert "/image" in body


def test_segmentation_is_a_live_nav_link_from_home(tmp_path: Path) -> None:
    home = _client(tmp_path).get("/").text
    assert 'href="/segmentation?lang=fr"' in home


def test_segmentation_image_endpoint_serves_png(tmp_path: Path) -> None:
    client = _client(tmp_path)
    page = client.get("/segmentation").text
    start = page.index("/api/segmentation/")
    href = page[start : page.index('"', start)]
    resp = client.get(href)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_segmentation_image_traversal_is_404(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/segmentation/..%2F..%2Fsecret/image")
    assert resp.status_code == 404


def test_segmentation_image_unknown_id_is_404(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/segmentation/deadbeef/image")
    assert resp.status_code == 404


def test_segmentation_page_english(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/segmentation?lang=en").text
    assert "Regions" in body
    assert "Demonstration page" in body
