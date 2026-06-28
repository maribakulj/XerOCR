"""Import « Cinoc curé » (dataset publié sur HF) côté HTTP : CSRF, 201
sélectionnable, gate public 403, source injoignable 422. L'import est
monkeypatché (pas de lib ``huggingface_hub`` ni de réseau)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cinoc.app.corpus_import import CorpusImportError
from cinoc.domain.artifacts import ArtifactType
from cinoc.domain.corpus import CorpusSpec
from cinoc.domain.documents import DocumentRef, GroundTruthRef
from cinoc.interfaces.web.app import create_app
from cinoc.interfaces.web.security.csrf import CSRF_HEADER

_TARGET = "cinoc.interfaces.web.routers.corpus.import_curated_hf_corpus"
_CSRF = {CSRF_HEADER: "1"}
_BODY = {"repo_id": "Ma-Ri-Ba-Ku/Cinoc-Dresden", "revision": "abc123"}


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(
            reports_dir=tmp_path / "rep",
            uploads_dir=tmp_path / "up",
            rate_limit=1000,
            public_mode=public_mode,
        )
    )


def _ok(
    repo_id: str, dest: Path, *, revision=None, name=None, **_: object
) -> CorpusSpec:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "d1.gt.txt").write_text("g", encoding="utf-8")
    return CorpusSpec(
        name=name or "curated",
        documents=(
            DocumentRef(
                id="d1",
                image_uri=(
                    f"https://huggingface.co/datasets/{repo_id}/resolve/"
                    f"{revision}/iiif/d1/full/1600,/0/default.jpg"
                ),
                ground_truths=(
                    GroundTruthRef(
                        type=ArtifactType.RAW_TEXT, uri=str(dest / "d1.gt.txt")
                    ),
                ),
            ),
        ),
        metadata={"source": "curated", "revision": revision or ""},
    )


def test_curated_import_ok_and_selectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_TARGET, _ok)
    client = _client(tmp_path)
    resp = client.post("/api/corpus/import/curated", json=_BODY, headers=_CSRF)
    assert resp.status_code == 201
    assert resp.json()["n_documents"] == 1


def test_curated_import_requires_csrf(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/corpus/import/curated", json=_BODY)
    assert resp.status_code == 403


def test_curated_import_blocked_in_public_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(*a: object, **k: object) -> CorpusSpec:
        raise AssertionError("l'import ne doit pas s'exécuter en mode public")

    monkeypatch.setattr(_TARGET, _fail)
    resp = _client(tmp_path, public_mode=True).post(
        "/api/corpus/import/curated", json=_BODY, headers=_CSRF
    )
    assert resp.status_code == 403


def test_curated_import_unreachable_is_422(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bad(*a: object, **k: object) -> CorpusSpec:
        raise CorpusImportError("dataset curé HF 'org/x' injoignable : 404.")

    monkeypatch.setattr(_TARGET, _bad)
    resp = _client(tmp_path).post(
        "/api/corpus/import/curated", json=_BODY, headers=_CSRF
    )
    assert resp.status_code == 422
    assert "injoignable" in resp.json()["detail"]


def test_curated_import_rejects_unknown_field(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/corpus/import/curated",
        json={"repo_id": "org/x", "bogus": 1},
        headers=_CSRF,
    )
    assert resp.status_code == 422
