"""`download` en flux disque (Lot B) : `.part` au fil de l'eau, `os.replace`
atomique, plafond, aucun fichier partiel ; auth transmise à l'hôte d'origine.

Serveur loopback réel (vrai chemin httpx) ; le garde-fou SSRF est neutralisé
*ici seulement* (`assert_public_url` → no-op) pour viser 127.0.0.1.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus._http import HttpFetchError, download

_seen_auth: dict[str, str | None] = {}


@pytest.fixture
def server() -> Iterator[int]:
    """Sert ``/big`` (1000 octets) et ``/img`` (petit corps), journalise l'auth."""
    _seen_auth.clear()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a: object) -> None:
            pass

        def do_GET(self) -> None:
            _seen_auth[self.path] = self.headers.get("Authorization")
            body = b"x" * 1000 if self.path == "/big" else b"PNGDATA"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _no_ssrf(monkeypatch: pytest.MonkeyPatch) -> None:
    # Vise le loopback : on lève le garde-fou SSRF pour CES tests seulement.
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)


def test_download_streams_atomic_no_partial(server: int, tmp_path: Path) -> None:
    dest = tmp_path / "out.bin"
    download(f"http://127.0.0.1:{server}/img", dest)
    assert dest.read_bytes() == b"PNGDATA"
    # Renommage atomique : aucun `.part` ne subsiste.
    assert not dest.with_name(dest.name + ".part").exists()
    assert list(tmp_path.iterdir()) == [dest]


def test_download_over_cap_leaves_no_file(
    server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_http, "IMAGE_MAX_BYTES", 10)
    dest = tmp_path / "out.bin"
    with pytest.raises(HttpFetchError, match="plafond"):
        download(f"http://127.0.0.1:{server}/big", dest)
    # Ni destination, ni fichier partiel : rien laissé derrière.
    assert not dest.exists()
    assert not dest.with_name(dest.name + ".part").exists()
    assert list(tmp_path.iterdir()) == []


def test_download_forwards_auth_to_origin(server: int, tmp_path: Path) -> None:
    download(
        f"http://127.0.0.1:{server}/img",
        tmp_path / "out.bin",
        headers={"Authorization": "Token SECRET"},
    )
    assert _seen_auth["/img"] == "Token SECRET"
