"""``POST /api/hybrid/run`` : gate, erreurs, et chaîne complète (mode precomputed).

La chaîne run → sink → AltoStore est prouvée **en CI sans tesseract ni PIL** :
mode ``precomputed`` (``crop=False`` → reconnaissance par ``region_id`` sur la
page entière). L'ALTO produit est persisté, téléchargeable par
``/reports/{run_id}/alto.zip``.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cinoc.adapters.storage import JobState, JobStore
from cinoc.app.alto_store import AltoStore
from cinoc.app.corpus_upload import CorpusStore
from cinoc.app.engines import EngineStatus
from cinoc.app.jobs import JobRunner
from cinoc.app.modules.registry import ModuleRegistry, register_default_modules
from cinoc.app.segmentation import SegmentationStore
from cinoc.domain.corpus import CorpusSpec
from cinoc.domain.documents import DocumentRef
from cinoc.domain.layout import CanonicalLayout, LayoutPage, Region
from cinoc.interfaces.web.routers.hybrid import build_hybrid_router
from cinoc.interfaces.web.security.csrf import CSRF_HEADER

_CSRF = {CSRF_HEADER: "1"}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    register_default_modules(registry)
    return registry


def _client(
    tmp_path: Path,
    *,
    segmenters: tuple[EngineStatus, ...] = (),
    engines: tuple[EngineStatus, ...] = (),
) -> tuple[TestClient, JobRunner, AltoStore, CorpusStore]:
    alto_store = AltoStore(tmp_path / "alto")
    seg_store = SegmentationStore(tmp_path / "seg")
    corpus_store = CorpusStore(tmp_path / "corpus")
    runner = JobRunner(
        store=JobStore(),
        registry=_registry(),
        reports_dir=tmp_path / "rep",
        code_version="1.0",
        segmentation_store=seg_store,
        alto_store=alto_store,
    )
    app = FastAPI()
    app.include_router(
        build_hybrid_router(
            runner=runner,
            corpus_store=corpus_store,
            segmenters=lambda: segmenters,
            engines=lambda: engines,
        )
    )
    return TestClient(app), runner, alto_store, corpus_store


def _add_corpus(corpus_store: CorpusStore, regions: dict[str, str]) -> str:
    def build(dest: Path) -> CorpusSpec:
        dest.mkdir(parents=True, exist_ok=True)
        image = dest / "doc1.png"
        image.write_bytes(b"\x89PNG stub")
        seg = CanonicalLayout(
            pages=(
                LayoutPage(
                    regions=(
                        Region(id="r1", region_type="text"),
                        Region(id="r2", region_type="text"),
                    ),
                    reading_order=("r1", "r2"),
                ),
            )
        )
        (dest / "doc1.layout.json").write_bytes(
            seg.model_dump_json().encode("utf-8")
        )
        (dest / "doc1.eng.regions.json").write_text(
            json.dumps(regions), encoding="utf-8"
        )
        return CorpusSpec(
            name="c", documents=(DocumentRef(id="doc1", image_uri=str(image)),)
        )

    corpus_id, _ = corpus_store.materialize(build)
    return corpus_id


def test_hybrid_run_precomputed_persists_downloadable_alto(tmp_path: Path) -> None:
    client, runner, alto_store, corpus_store = _client(tmp_path)
    corpus_id = _add_corpus(corpus_store, {"r1": "hello world", "r2": "second"})
    resp = client.post(
        "/api/hybrid/run",
        json={
            "corpus_id": corpus_id,
            "segmenter": "precomputed_layout",
            "ocr": "precomputed_region",
            "source_label": "eng",
        },
        headers=_CSRF,
    )
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]
    job_id = resp.json()["job_id"]
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    # ALTO persisté sous le run_id → téléchargeable via /reports/{run_id}/alto.zip
    assert alto_store.has(run_id)


def test_hybrid_run_unknown_corpus_404(tmp_path: Path) -> None:
    client, *_ = _client(tmp_path)
    resp = client.post(
        "/api/hybrid/run", json={"corpus_id": "absent"}, headers=_CSRF
    )
    assert resp.status_code == 404


def test_hybrid_run_unknown_ocr_422(tmp_path: Path) -> None:
    client, _runner, _alto, corpus_store = _client(tmp_path)
    corpus_id = _add_corpus(corpus_store, {"r1": "x"})
    resp = client.post(
        "/api/hybrid/run",
        json={
            "corpus_id": corpus_id,
            "segmenter": "precomputed_layout",
            "ocr": "bogus",
        },
        headers=_CSRF,
    )
    assert resp.status_code == 422


def test_hybrid_run_unavailable_segmenter_409(tmp_path: Path) -> None:
    segmenters = (
        EngineStatus(
            kind="pp_doclayout", label="PP-DocLayout", available=False,
            detail="PaddleX absent (extra [segment])",
        ),
    )
    engines = (
        EngineStatus(
            kind="tesseract", label="Tesseract", available=True, detail="ok"
        ),
    )
    client, _runner, _alto, corpus_store = _client(
        tmp_path, segmenters=segmenters, engines=engines
    )
    corpus_id = _add_corpus(corpus_store, {"r1": "x"})
    resp = client.post(
        "/api/hybrid/run",
        json={
            "corpus_id": corpus_id,
            "segmenter": "pp_doclayout",
            "ocr": "tesseract",
        },
        headers=_CSRF,
    )
    assert resp.status_code == 409
