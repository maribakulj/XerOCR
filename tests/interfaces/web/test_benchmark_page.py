"""Page « Banc d'essai » (TU2.f) : rendu serveur + JS auto-hébergé + CSP ouverte.

Le comportement *navigateur* (fetch + EventSource) n'est pas exécutable en CI
(pas de navigateur) ; on vérifie ici la **surface serveur** : la page existe au
design, lie son JS, la nav est vivante, le JS est servi et sa **syntaxe valide**
(``node --check``), et la CSP autorise bien ``script-src``/``connect-src 'self'``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app

_JS = Path(__file__).resolve().parents[3] / (
    "xerocr/interfaces/web/static/js/benchmark.js"
)


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(reports_dir=tmp_path, rate_limit=1000))


def test_benchmark_page_renders_with_launcher(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/benchmark")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert 'id="launch"' in body  # le bouton de lancement
    assert 'src="/static/js/benchmark.js"' in body  # le JS est lié
    assert "Lancer la démonstration" in body  # libellé du lanceur (FR par défaut)


def test_nav_links_benchmark_and_reports(tmp_path: Path) -> None:
    # depuis l'accueil, « Banc d'essai » est un lien vivant (plus un placeholder)
    home = _client(tmp_path).get("/").text
    assert 'href="/benchmark?lang=fr"' in home
    # depuis le banc d'essai, « Rapports » reste accessible
    bench = _client(tmp_path).get("/benchmark").text
    assert 'href="/?lang=fr"' in bench
    assert 'aria-current="page"' in bench  # l'onglet courant est marqué


def test_benchmark_english(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/benchmark?lang=en").text
    assert "Run the demonstration" in body


def test_js_asset_is_served(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/static/js/benchmark.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]


def test_csp_allows_self_script_and_connect(tmp_path: Path) -> None:
    csp = _client(tmp_path).get("/benchmark").headers["content-security-policy"]
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp


def test_benchmark_js_syntax_is_valid() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent : vérification de syntaxe JS ignorée")
    result = subprocess.run(
        [node, "--check", str(_JS)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
