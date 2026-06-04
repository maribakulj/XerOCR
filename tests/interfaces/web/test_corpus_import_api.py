"""Import IIIF côté HTTP : CSRF, 201 + corpus sélectionnable, gate mode public, 422."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.adapters.corpus._http import SsrfError
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

_IMPORT_TARGET = "xerocr.interfaces.web.routers.corpus.import_iiif_corpus"

_CSRF = {CSRF_HEADER: "1"}
_BODY = {"manifest_url": "https://example.org/manifest.json", "limit": 1}


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(
            reports_dir=tmp_path / "rep",
            uploads_dir=tmp_path / "up",
            rate_limit=1000,
            public_mode=public_mode,
        )
    )


def _fake_import(manifest_url: str, dest: Path, *, name: str, limit: int | None = None,
                 **_: object) -> CorpusSpec:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "page_0001.jpg").write_bytes(b"img")
    return CorpusSpec(
        name=name,
        documents=(DocumentRef(id="page_0001", image_uri=str(dest / "page_0001.jpg")),),
        metadata={"source": "iiif", "manifest_url": manifest_url},
    )


def _patch_import(monkeypatch: pytest.MonkeyPatch, fn: object) -> None:
    monkeypatch.setattr(_IMPORT_TARGET, fn)


def _fail(*a: object, **k: object) -> CorpusSpec:
    raise AssertionError("l'import ne doit pas s'exécuter")


def test_import_iiif_ok_and_selectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_import(monkeypatch, _fake_import)
    client = _client(tmp_path)
    resp = client.post("/api/corpus/import/iiif", json=_BODY, headers=_CSRF)
    assert resp.status_code == 201
    body = resp.json()
    assert body["n_documents"] == 1
    # le corpus importé est immédiatement consultable (donc cible d'un run)
    got = client.get(f"/api/corpus/{body['corpus_id']}").json()
    assert got["documents"] == ["page_0001"]


def test_import_without_csrf_is_403(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/corpus/import/iiif", json=_BODY)
    assert resp.status_code == 403


def test_import_refused_in_public_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _must_not_run(*a: object, **k: object) -> CorpusSpec:
        raise AssertionError("l'import ne doit pas s'exécuter en mode public")

    _patch_import(monkeypatch, _must_not_run)
    resp = _client(tmp_path, public_mode=True).post(
        "/api/corpus/import/iiif", json=_BODY, headers=_CSRF
    )
    assert resp.status_code == 403


def test_import_ssrf_is_422(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _ssrf(*a: object, **k: object) -> CorpusSpec:
        raise SsrfError("hôte non public")

    _patch_import(monkeypatch, _ssrf)
    resp = _client(tmp_path).post("/api/corpus/import/iiif", json=_BODY, headers=_CSRF)
    assert resp.status_code == 422


def test_import_missing_url_is_422(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/corpus/import/iiif", json={"limit": 1}, headers=_CSRF
    )
    assert resp.status_code == 422


# --- eScriptorium --------------------------------------------------------------

_ESC_TARGET = "xerocr.interfaces.web.routers.corpus.import_escriptorium_corpus"
_ESC_BODY = {"base_url": "https://e.org", "token": "tok", "doc_pk": 5, "limit": 1}


def _fake_esc(
    base_url: str,
    token: str,
    doc_pk: int,
    dest: Path,
    *,
    name: str | None = None,
    layer: str = "manual",
    limit: int | None = None,
    **_: object,
) -> CorpusSpec:
    dest.mkdir(parents=True, exist_ok=True)
    img = dest / "part_00042.jpg"
    img.write_bytes(b"img")
    return CorpusSpec(
        name=name or f"escriptorium-{doc_pk}",
        documents=(DocumentRef(id="part_00042", image_uri=str(img)),),
        metadata={"source": "escriptorium"},
    )


def test_escriptorium_ok_and_selectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_ESC_TARGET, _fake_esc)
    client = _client(tmp_path)
    resp = client.post("/api/corpus/import/escriptorium", json=_ESC_BODY, headers=_CSRF)
    assert resp.status_code == 201
    got = client.get(f"/api/corpus/{resp.json()['corpus_id']}").json()
    assert got["documents"] == ["part_00042"]


def test_escriptorium_public_mode_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_ESC_TARGET, _fail)
    resp = _client(tmp_path, public_mode=True).post(
        "/api/corpus/import/escriptorium", json=_ESC_BODY, headers=_CSRF
    )
    assert resp.status_code == 403


def test_escriptorium_http_error_422(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from xerocr.adapters.corpus._http import HttpFetchError

    def _boom(*a: object, **k: object) -> CorpusSpec:
        raise HttpFetchError("401 du serveur eScriptorium")

    monkeypatch.setattr(_ESC_TARGET, _boom)
    resp = _client(tmp_path).post(
        "/api/corpus/import/escriptorium", json=_ESC_BODY, headers=_CSRF
    )
    assert resp.status_code == 422


def test_escriptorium_missing_token_is_422(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/corpus/import/escriptorium",
        json={"base_url": "https://e.org", "doc_pk": 5},
        headers=_CSRF,
    )
    assert resp.status_code == 422


# --- Gallica -------------------------------------------------------------------

_GAL_TARGET = "xerocr.interfaces.web.routers.corpus.import_gallica_corpus"
_GAL_BODY = {"ark": "12148/btv1bTEST", "limit": 1}


def _fake_gallica(ark: str, dest: Path, *, name: str | None = None,
                  limit: int | None = None, include_ocr: bool = True,
                  **_: object) -> CorpusSpec:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "f0001.jpg").write_bytes(b"img")
    return CorpusSpec(
        name=name or "gallica-btv1bTEST",
        documents=(DocumentRef(id="f0001", image_uri=str(dest / "f0001.jpg")),),
        metadata={"source": "gallica"},
    )


def test_gallica_ok_and_selectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_GAL_TARGET, _fake_gallica)
    client = _client(tmp_path)
    resp = client.post("/api/corpus/import/gallica", json=_GAL_BODY, headers=_CSRF)
    assert resp.status_code == 201
    got = client.get(f"/api/corpus/{resp.json()['corpus_id']}").json()
    assert got["documents"] == ["f0001"]


def test_gallica_public_mode_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_GAL_TARGET, _fail)
    resp = _client(tmp_path, public_mode=True).post(
        "/api/corpus/import/gallica", json=_GAL_BODY, headers=_CSRF
    )
    assert resp.status_code == 403


def test_gallica_bad_ark_is_422(tmp_path: Path) -> None:
    # Vrai chemin (sans réseau) : ARK malformé → GallicaArkError → 422.
    resp = _client(tmp_path).post(
        "/api/corpus/import/gallica", json={"ark": "pas un ark"}, headers=_CSRF
    )
    assert resp.status_code == 422
