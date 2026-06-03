"""Recherche HuggingFace **réelle** contre un serveur loopback (déterministe, CI).

Exerce le vrai chemin `httpx` de l'appel API du Hub + le parsing de la réponse,
sans mock du transport.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus.huggingface import HuggingFaceCatalogue

_PAYLOAD = json.dumps(
    [
        {"id": "loopback/dataset-a", "downloads": 123},
        {"id": "loopback/dataset-b", "downloads": 7},
    ]
).encode()


@pytest.fixture
def server() -> Iterator[int]:
    holder: dict[str, int] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            if not self.path.startswith("/api/datasets"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(_PAYLOAD)))
            self.end_headers()
            self.wfile.write(_PAYLOAD)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    holder["port"] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield holder["port"]
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_real_api_search(server: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)
    catalogue = HuggingFaceCatalogue(api_base=f"http://127.0.0.1:{server}/api")
    results = catalogue.search("manuscrit", use_reference=False, include_api=True)
    assert [d.dataset_id for d in results] == [
        "loopback/dataset-a",
        "loopback/dataset-b",
    ]
    assert all(d.source == "api" for d in results)
    assert results[0].downloads == 123
