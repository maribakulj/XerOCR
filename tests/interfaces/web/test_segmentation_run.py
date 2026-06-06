"""``POST /api/segmentation/run`` (T2.4a) : gate, erreurs, et chaîne complète.

La chaîne run → sink → store est prouvée **en CI sans PaddleX** : le registre
substitue ``pp_doclayout`` par un segmenteur à **détecteur injecté**, et le
provider de statut déclare le segmenteur disponible.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from xerocr.adapters.layout.pp_doclayout import (
    DetectedRegion,
    LayoutDetection,
    PPDocLayoutSegmenter,
)
from xerocr.adapters.storage import JobState, JobStore
from xerocr.app.corpus_upload import CorpusStore
from xerocr.app.engines import EngineStatus
from xerocr.app.jobs import JobRunner
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.app.segmentation import SegmentationStore
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.interfaces.web.routers.segmentation import build_segmentation_router
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

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


def _fake_segmenter_registry() -> ModuleRegistry:
    """Registre du socle où ``pp_doclayout`` a un détecteur injecté (pas de SDK)."""
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
