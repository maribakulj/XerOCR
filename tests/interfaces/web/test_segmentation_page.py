"""Écran segmentation (S6) : page rendue serveur + endpoint image, anti-traversal."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cinoc.interfaces.web.app import create_app


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


def test_segmentation_is_not_listed_in_home_nav(tmp_path: Path) -> None:
    home = _client(tmp_path).get("/").text
    assert 'href="/segmentation?lang=fr"' not in home


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


def test_hybrid_panel_present_on_segmentation_page(tmp_path: Path) -> None:
    # Le panneau « transcription hybride » est rendu serveur (toujours présent).
    body = _client(tmp_path).get("/segmentation").text
    assert "hybride" in body  # titre du panneau (t.hyb_run_title)


def _home_with(tmp_path: Path, *, statuses, segmenters, corpus_store=None):
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates

    from cinoc.adapters.storage.history_store import HistoryStore
    from cinoc.app.segmentation import SegmentationStore, demo_layout
    from cinoc.interfaces.web.app import _TEMPLATES_DIR
    from cinoc.interfaces.web.routers.home import build_home_router

    store = SegmentationStore(tmp_path / "seg")
    demo_id = store.save(demo_layout())
    app = FastAPI()
    app.include_router(
        build_home_router(
            tmp_path / "reports",
            Jinja2Templates(directory=_TEMPLATES_DIR),
            statuses=statuses,
            segmenters=segmenters,
            history_store=HistoryStore(tmp_path / "h.db"),
            segmentation_store=store,
            demo_segmentation_id=demo_id,
            corpus_store=corpus_store,
        )
    )
    return TestClient(app)


def test_hybrid_panel_gated_without_any_recognizer(tmp_path: Path) -> None:
    # Aucun reconnaisseur disponible → le panneau affiche le hint, pas le formulaire.
    client = _home_with(tmp_path, statuses=lambda: (), segmenters=lambda: ())
    body = client.get("/segmentation").text
    assert "hyb-run-form" not in body
    assert "Aucun reconnaisseur disponible" in body


def test_hybrid_form_offered_with_tesseract_and_corpus(tmp_path: Path) -> None:
    from cinoc.app.corpus_upload import CorpusStore
    from cinoc.app.engines import EngineStatus
    from cinoc.domain.corpus import CorpusSpec
    from cinoc.domain.documents import DocumentRef

    corpus_store = CorpusStore(tmp_path / "corpus")

    def build(dest: Path) -> CorpusSpec:
        dest.mkdir(parents=True, exist_ok=True)
        img = dest / "d.png"
        img.write_bytes(b"\x89PNG stub")
        return CorpusSpec(
            name="c", documents=(DocumentRef(id="d", image_uri=str(img)),)
        )

    corpus_store.materialize(build)
    client = _home_with(
        tmp_path,
        statuses=lambda: (
            EngineStatus(
                kind="tesseract", label="Tesseract", available=True, detail="ok"
            ),
            EngineStatus(
                kind="mistral_ocr", label="Mistral OCR", available=True, detail="ok"
            ),
            EngineStatus(
                kind="openai", label="OpenAI", available=True, detail="ok"
            ),
        ),
        segmenters=lambda: (
            EngineStatus(
                kind="pp_doclayout", label="PP-DocLayout", available=True,
                detail="ok",
            ),
        ),
        corpus_store=corpus_store,
    )
    body = client.get("/segmentation").text
    assert 'id="hyb-run-form"' in body
    assert 'id="hybrid-btn"' in body
    assert 'id="hyb-download"' in body
    # Le <select> reconnaisseur par bloc liste OCR réels ET VLM (zero-shot).
    assert 'id="hyb-ocr"' in body
    assert 'value="mistral_ocr"' in body  # OCR cloud câblé par bloc
    assert 'value="openai"' in body and 'data-vlm="1"' in body  # VLM par bloc


def test_segmentation_page_shows_latest_persisted_run(tmp_path: Path) -> None:
    # Quand un run réel a persisté un LAYOUT, /segmentation l'affiche (plus récent
    # que la graine de démo), via build_home_router monté avec un store amorcé.
    import os

    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates

    from cinoc.adapters.storage.history_store import HistoryStore
    from cinoc.app.segmentation import SegmentationStore, demo_layout
    from cinoc.domain.layout import CanonicalLayout, LayoutPage, Region
    from cinoc.interfaces.web.app import _TEMPLATES_DIR
    from cinoc.interfaces.web.routers.home import build_home_router

    store = SegmentationStore(tmp_path / "seg")
    demo_id = store.save(demo_layout())
    run_layout = CanonicalLayout(
        pages=(LayoutPage(regions=(Region(id="rx", region_type="headline"),)),)
    )
    run_id = store.save(run_layout)
    os.utime(tmp_path / "seg" / demo_id, (1_000_000_000, 1_000_000_000))
    os.utime(tmp_path / "seg" / run_id, (2_000_000_000, 2_000_000_000))

    app = FastAPI()
    app.include_router(
        build_home_router(
            tmp_path / "reports",
            Jinja2Templates(directory=_TEMPLATES_DIR),
            statuses=lambda: (),
            segmenters=lambda: (),
            history_store=HistoryStore(tmp_path / "h.db"),
            segmentation_store=store,
            demo_segmentation_id=demo_id,
        )
    )
    body = TestClient(app).get("/segmentation").text
    assert "headline" in body  # le run réel le plus récent
    assert "figure" not in body  # un type propre à la démo n'apparaît pas
