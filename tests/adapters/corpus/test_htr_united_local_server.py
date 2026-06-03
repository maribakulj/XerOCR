"""Fetch HTR-United **réel** contre un serveur loopback (déterministe, CI)."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus.htr_united import fetch_catalogue

_YAML = b"""
- title: Loopback Corpus
  url: https://github.com/HTR-United/loopback
  description: servi en local
  language: [fr]
"""


@pytest.fixture
def server() -> Iterator[int]:
    holder: dict[str, int] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            if not self.path.endswith(".yml"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/yaml")
            self.send_header("Content-Length", str(len(_YAML)))
            self.end_headers()
            self.wfile.write(_YAML)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    holder["port"] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield holder["port"]
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_fetch_real_catalogue(server: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)
    cat = fetch_catalogue(catalogue_url=f"http://127.0.0.1:{server}/htr-united.yml")
    assert not cat.is_demo and cat.source == "remote"
    assert [e.id for e in cat.entries] == ["loopback"]
    assert cat.entries[0].languages == ("fr",)
