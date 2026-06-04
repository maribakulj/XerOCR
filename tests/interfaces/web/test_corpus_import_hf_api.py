"""Import HuggingFace côté HTTP : CSRF, 201 sélectionnable, gate public 403,
non-conforme 422, extra absent 409. L'import est monkeypatché (pas de lib/réseau)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.adapters.corpus.huggingface import (
    HuggingFaceConventionError,
    HuggingFaceUnavailableError,
)
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

_TARGET = "xerocr.interfaces.web.routers.corpus.import_hf_corpus"
_CSRF = {CSRF_HEADER: "1"}
_BODY = {"dataset_id": "org/corpus-xerocr", "limit": 2}


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(
            reports_dir=tmp_path / "rep",
            uploads_dir=tmp_path / "up",
            rate_limit=1000,
            public_mode=public_mode,
        )
    )


def _ok(dataset_id: str, dest: Path, *, name=None, split="train", limit=None,
        **_: object) -> CorpusSpec:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "page_0001.png").write_bytes(b"img")
    (dest / "page_0001.gt.txt").write_text("g", encoding="utf-8")
    return CorpusSpec(
        name=name or "hf",
        documents=(
            DocumentRef(
                id="page_0001",
                image_uri=str(dest / "page_0001.png"),
                ground_truths=(
                    GroundTruthRef(
                        type=ArtifactType.RAW_TEXT, uri=str(dest / "page_0001.gt.txt")
                    ),
                ),
            ),
        ),
        metadata={"source": "huggingface", "dataset_id": dataset_id, "split": split},
    )


def test_hf_import_ok_and_selectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_TARGET, _ok)
    client = _client(tmp_path)
    resp = client.post("/api/corpus/import/huggingface", json=_BODY, headers=_CSRF)
    assert resp.status_code == 201
    corpus_id = resp.json()["corpus_id"]
    # corpus immédiatement consultable (intégré au store, cible de run)
    assert client.get(f"/api/corpus/{corpus_id}").json()["n_documents"] == 1


def test_hf_import_requires_csrf(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/corpus/import/huggingface", json=_BODY)
    assert resp.status_code == 403


def test_hf_import_blocked_in_public_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(*a: object, **k: object) -> CorpusSpec:
        raise AssertionError("l'import ne doit pas s'exécuter en mode public")

    monkeypatch.setattr(_TARGET, _fail)
    resp = _client(tmp_path, public_mode=True).post(
        "/api/corpus/import/huggingface", json=_BODY, headers=_CSRF
    )
    assert resp.status_code == 403


def test_nonconformant_dataset_is_422(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bad(*a: object, **k: object) -> CorpusSpec:
        raise HuggingFaceConventionError("colonnes manquantes ['ground_truth'].")

    monkeypatch.setattr(_TARGET, _bad)
    resp = _client(tmp_path).post(
        "/api/corpus/import/huggingface", json=_BODY, headers=_CSRF
    )
    assert resp.status_code == 422
    assert "ground_truth" in resp.json()["detail"]


def test_missing_extra_is_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _unavailable(*a: object, **k: object) -> CorpusSpec:
        raise HuggingFaceUnavailableError("installer 'xerocr[huggingface]'.")

    monkeypatch.setattr(_TARGET, _unavailable)
    resp = _client(tmp_path).post(
        "/api/corpus/import/huggingface", json=_BODY, headers=_CSRF
    )
    assert resp.status_code == 409
