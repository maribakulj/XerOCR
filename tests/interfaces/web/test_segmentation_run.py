"""``POST /api/segmentation/run`` (T2.4a) : gate, erreurs, et chaîne complète.

La chaîne run → sink → store est prouvée **en CI sans PaddleX** : le registre
substitue ``pp_doclayout`` par un segmenteur à **détecteur injecté**, et le
provider de statut déclare le segmenteur disponible.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cinoc.adapters.layout._base import DetectedRegion, LayoutDetection
from cinoc.adapters.layout.pp_doclayout import PPDocLayoutSegmenter
from cinoc.adapters.layout.remote import RemoteSegmenter
from cinoc.adapters.storage import JobState, JobStore
from cinoc.app.corpus_upload import CorpusStore
from cinoc.app.engines import EngineStatus
from cinoc.app.jobs import JobRunner
from cinoc.app.modules.registry import ModuleRegistry, register_default_modules
from cinoc.app.segmentation import SegmentationStore
from cinoc.domain.corpus import CorpusSpec
from cinoc.domain.documents import DocumentRef
from cinoc.interfaces.web.routers.segmentation import build_segmentation_router
from cinoc.interfaces.web.security.csrf import CSRF_HEADER

_CSRF = {CSRF_HEADER: "1"}
_AVAILABLE = (
    EngineStatus(
        kind="pp_doclayout", label="PP-DocLayout", available=True, detail="ok"
    ),
)
_UNAVAILABLE = (
    EngineStatus(
        kind="pp_doclayout", label="PP-DocLayout", available=False,
        detail="PaddleX non installé (extra [segment])",
    ),
)
#: Les deux segmenteurs du socle disponibles (local + distant).
_BOTH_AVAILABLE = (
    EngineStatus(
        kind="pp_doclayout", label="PP-DocLayout", available=True, detail="ok"
    ),
    EngineStatus(
        kind="remote_segmenter", label="Segmenteur distant (HF)",
        available=True, detail="ok",
    ),
)


def _fake_segmenter_registry() -> ModuleRegistry:
    """Registre du socle où les segmenteurs ont un détecteur injecté (pas de SDK
    ni de réseau) : ``pp_doclayout`` (local) **et** ``remote_segmenter`` (distant)."""
    detection = LayoutDetection(
        page_width=100, page_height=120,
        regions=(DetectedRegion("title", 1, 2, 30, 10, 0.95),),
    )
    registry = ModuleRegistry()
    register_default_modules(registry)
    registry.register_builder(
        "pp_doclayout",
        lambda _kw: PPDocLayoutSegmenter(detector=lambda _path: detection),
    )
    registry.register_builder(
        "remote_segmenter",
        lambda kw: RemoteSegmenter(
            endpoint=str(kw["endpoint"]), detector=lambda _path: detection
        ),
    )
    return registry


def _client(
    tmp_path: Path,
    *,
    segmenters: tuple[EngineStatus, ...] = _AVAILABLE,
) -> tuple[TestClient, JobRunner, SegmentationStore, CorpusStore]:
    seg_store = SegmentationStore(tmp_path / "seg")
    corpus_store = CorpusStore(tmp_path / "corpus")
    runner = JobRunner(
        store=JobStore(),
        registry=_fake_segmenter_registry(),
        reports_dir=tmp_path / "rep",
        code_version="1.0",
        segmentation_store=seg_store,
    )
    app = FastAPI()
    app.include_router(
        build_segmentation_router(
            seg_store,
            runner=runner,
            corpus_store=corpus_store,
            segmenters=lambda: segmenters,
        )
    )
    return TestClient(app), runner, seg_store, corpus_store


def _add_corpus(corpus_store: CorpusStore) -> str:
    def build(dest: Path) -> CorpusSpec:
        dest.mkdir(parents=True, exist_ok=True)
        image = dest / "doc1.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n stub")
        return CorpusSpec(
            name="c", documents=(DocumentRef(id="doc1", image_uri=str(image)),)
        )

    corpus_id, _ = corpus_store.materialize(build)
    return corpus_id


def test_run_segments_corpus_and_persists_layout(tmp_path: Path) -> None:
    client, runner, seg_store, corpus_store = _client(tmp_path)
    corpus_id = _add_corpus(corpus_store)
    resp = client.post(
        "/api/segmentation/run", json={"corpus_id": corpus_id}, headers=_CSRF
    )
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    # le run a produit un LAYOUT → persisté par le sink, visible par /segmentation
    seg_id = seg_store.latest()
    assert seg_id is not None
    layout = seg_store.get_layout(seg_id)
    assert layout is not None
    assert layout.pages[0].regions[0].region_type == "title"


def test_run_with_remote_segmenter_persists_layout(tmp_path: Path) -> None:
    client, runner, seg_store, corpus_store = _client(
        tmp_path, segmenters=_BOTH_AVAILABLE
    )
    corpus_id = _add_corpus(corpus_store)
    resp = client.post(
        "/api/segmentation/run",
        json={
            "corpus_id": corpus_id,
            "segmenter": "remote_segmenter",
            "endpoint": "https://example.org/seg",
            "token": "secret",
        },
        headers=_CSRF,
    )
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    seg_id = seg_store.latest()
    assert seg_id is not None
    layout = seg_store.get_layout(seg_id)
    assert layout is not None
    assert layout.pages[0].regions[0].region_type == "title"


def test_run_remote_segmenter_without_endpoint_is_422(tmp_path: Path) -> None:
    client, _, _, corpus_store = _client(tmp_path, segmenters=_BOTH_AVAILABLE)
    corpus_id = _add_corpus(corpus_store)
    resp = client.post(
        "/api/segmentation/run",
        json={"corpus_id": corpus_id, "segmenter": "remote_segmenter"},
        headers=_CSRF,
    )
    assert resp.status_code == 422
    assert "endpoint" in resp.json()["detail"]


def test_run_unknown_segmenter_is_422(tmp_path: Path) -> None:
    client, _, _, corpus_store = _client(tmp_path, segmenters=_BOTH_AVAILABLE)
    corpus_id = _add_corpus(corpus_store)
    resp = client.post(
        "/api/segmentation/run",
        json={"corpus_id": corpus_id, "segmenter": "nope"},
        headers=_CSRF,
    )
    assert resp.status_code == 422


def test_run_unavailable_segmenter_is_409(tmp_path: Path) -> None:
    client, _, _, corpus_store = _client(tmp_path, segmenters=_UNAVAILABLE)
    corpus_id = _add_corpus(corpus_store)
    resp = client.post(
        "/api/segmentation/run", json={"corpus_id": corpus_id}, headers=_CSRF
    )
    assert resp.status_code == 409
    assert "[segment]" in resp.json()["detail"]


def test_run_without_csrf_is_403(tmp_path: Path) -> None:
    client, _, _, corpus_store = _client(tmp_path)
    corpus_id = _add_corpus(corpus_store)
    resp = client.post("/api/segmentation/run", json={"corpus_id": corpus_id})
    assert resp.status_code == 403


def test_run_unknown_corpus_is_404(tmp_path: Path) -> None:
    client, _, _, _ = _client(tmp_path)
    resp = client.post(
        "/api/segmentation/run", json={"corpus_id": "absent"}, headers=_CSRF
    )
    assert resp.status_code == 404


def test_run_missing_corpus_id_is_422(tmp_path: Path) -> None:
    client, _, _, _ = _client(tmp_path)
    resp = client.post("/api/segmentation/run", json={}, headers=_CSRF)
    assert resp.status_code == 422


# --- Aperçu de mise en page (panneau du lanceur, remplace la page /segmentation) ---


def test_preview_renders_svg_of_latest_layout(tmp_path: Path) -> None:
    # Après un run, l'aperçu rend le SVG des régions du dernier layout persisté.
    client, runner, _seg_store, corpus_store = _client(tmp_path)
    corpus_id = _add_corpus(corpus_store)
    job_id = client.post(
        "/api/segmentation/run", json={"corpus_id": corpus_id}, headers=_CSRF
    ).json()["job_id"]
    assert runner.join(job_id, timeout=30)
    resp = client.get("/api/segmentation/preview")
    assert resp.status_code == 200
    assert "<svg" in resp.text


def test_preview_without_any_segmentation_is_404(tmp_path: Path) -> None:
    client, *_ = _client(tmp_path)
    assert client.get("/api/segmentation/preview").status_code == 404


def test_image_endpoint_serves_persisted_png(tmp_path: Path) -> None:
    from cinoc.domain.layout import CanonicalLayout, LayoutPage

    client, _runner, seg_store, _corpus = _client(tmp_path)
    seg_id = seg_store.save(
        CanonicalLayout(pages=(LayoutPage(),)),
        image_ext=".png",
        image_bytes=b"\x89PNG\r\n\x1a\n",
    )
    resp = client.get(f"/api/segmentation/{seg_id}/image")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_image_endpoint_traversal_is_404(tmp_path: Path) -> None:
    client, *_ = _client(tmp_path)
    assert (
        client.get("/api/segmentation/..%2F..%2Fsecret/image").status_code == 404
    )
