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

from xerocr.app.corpus_upload import CorpusStore
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


def test_benchmark_has_corpus_and_engine_controls(tmp_path: Path) -> None:
    # Le corpus est SÉLECTIONNÉ ici (préparé dans la Bibliothèque), pas téléversé.
    body = _client(tmp_path).get("/benchmark").text
    assert 'id="corpus-select"' in body  # <select> de corpus existants
    assert 'id="engine"' in body  # <select> moteur
    for label in ("Pré-calculé", "Tesseract", "OpenAI", "Ollama"):
        assert label in body
    # upload + imports ne sont plus ici : déplacés dans la Bibliothèque
    assert 'id="corpus-file"' not in body
    assert 'id="import-source"' not in body


def test_benchmark_engine_select_disables_unavailable(tmp_path: Path) -> None:
    # tesseract indisponible ici (ni binaire ni pytesseract) → option disabled.
    body = _client(tmp_path).get("/benchmark").text
    # l'option précomputed (toujours dispo) n'est pas désactivée ; au moins une l'est
    assert "disabled" in body


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


# --- Bouton « Segmenter » (S6/T2) ----------------------------------------------

def _benchmark_body(
    tmp_path: Path,
    segmenter_available: bool,
    corpus_store: CorpusStore | None = None,
) -> str:
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates

    from xerocr.adapters.storage.history_store import HistoryStore
    from xerocr.app.engines import EngineStatus
    from xerocr.app.segmentation import SegmentationStore, demo_layout
    from xerocr.interfaces.web.app import _TEMPLATES_DIR
    from xerocr.interfaces.web.routers.home import build_home_router

    seg_store = SegmentationStore(tmp_path / "seg")
    seg_id = seg_store.save(demo_layout())
    detail = "ok" if segmenter_available else "PaddleX absent (extra [segment])"
    status = EngineStatus(
        kind="pp_doclayout",
        label="PP-DocLayout",
        available=segmenter_available,
        detail=detail,
    )
    app = FastAPI()
    app.include_router(
        build_home_router(
            tmp_path / "reports",
            Jinja2Templates(directory=_TEMPLATES_DIR),
            statuses=lambda: (),
            segmenters=lambda: (status,),
            history_store=HistoryStore(tmp_path / "h.db"),
            segmentation_store=seg_store,
            demo_segmentation_id=seg_id,
            corpus_store=corpus_store,
        )
    )
    return TestClient(app).get("/benchmark").text


def test_segment_button_shown_when_available(tmp_path: Path) -> None:
    body = _benchmark_body(tmp_path, segmenter_available=True)
    assert 'id="segment-btn"' in body
    assert "Segmenter (PP-DocLayout)" in body


def test_segment_button_hidden_when_unavailable(tmp_path: Path) -> None:
    body = _benchmark_body(tmp_path, segmenter_available=False)
    assert 'id="segment-btn"' not in body  # pas de bouton actif
    assert "indisponible" in body  # motif affiché
    assert "[segment]" in body


def test_benchmark_corpus_select_lists_corpora(tmp_path: Path) -> None:
    from xerocr.domain.corpus import CorpusSpec
    from xerocr.domain.documents import DocumentRef

    store = CorpusStore(tmp_path / "corpora")
    store.materialize(
        lambda dest: CorpusSpec(
            name="Mon corpus", documents=(DocumentRef(id="d1", image_uri="a.png"),)
        )
    )
    body = _benchmark_body(tmp_path, segmenter_available=False, corpus_store=store)
    assert 'id="corpus-select"' in body
    assert "Mon corpus" in body  # rendu comme option du <select>
