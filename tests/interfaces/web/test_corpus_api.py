"""Upload de corpus côté HTTP : CSRF, 201 + résumé, 422 sur archive hostile."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

_CSRF = {CSRF_HEADER: "1"}
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path / "rep", uploads_dir=tmp_path / "up",
                   rate_limit=1000)
    )


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, payload in entries.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def _upload(client: TestClient, data: bytes, *, csrf: bool = True) -> object:
    headers = _CSRF if csrf else {}
    files = {"file": ("corpus.zip", data, "application/zip")}
    return client.post("/api/corpus", files=files, headers=headers)


def test_upload_without_csrf_is_403(tmp_path: Path) -> None:
    resp = _upload(_client(tmp_path), _zip({"a.png": _PNG}), csrf=False)
    assert resp.status_code == 403


def test_upload_ok_returns_summary(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = _upload(client, _zip({"a.png": _PNG, "a.gt.txt": b"v", "b.png": _PNG}))
    assert resp.status_code == 201
    body = resp.json()
    assert body["n_documents"] == 2
    # le résumé est consultable
    got = client.get(f"/api/corpus/{body['corpus_id']}").json()
    assert set(got["documents"]) == {"a", "b"}


def test_hostile_archive_is_422(tmp_path: Path) -> None:
    resp = _upload(_client(tmp_path), _zip({"../escape.png": _PNG}))
    assert resp.status_code == 422


def test_bad_zip_is_422(tmp_path: Path) -> None:
    resp = _upload(_client(tmp_path), b"not a zip")
    assert resp.status_code == 422


def test_unknown_corpus_is_404(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/corpus/absent").status_code == 404


def test_stem_collision_is_422_not_500(tmp_path: Path) -> None:
    # archive « sûre mais bancale » (deux images de même radical) → 422, jamais 500.
    jpeg = b"\xff\xd8\xff" + b"\x00" * 32
    resp = _upload(_client(tmp_path), _zip({"a.png": _PNG, "a.jpg": jpeg}))
    assert resp.status_code == 422
