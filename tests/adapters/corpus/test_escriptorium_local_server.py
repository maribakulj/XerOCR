"""Transport eScriptorium **réel** contre un serveur loopback (déterministe, CI).

Exerce le *vrai* chemin `httpx` de bout en bout — auth par token, **pagination**
(`next`), fetch des transcriptions, download des images, écriture GT, construction
du `CorpusSpec` **scorable** — sans aucun mock du transport. C'est le test qui
**ferme R-7** : Picarones plantait au 1ᵉʳ appel réel (`Corpus(source=…)` →
`TypeError`, masqué par les mocks) ; ici la construction `CorpusSpec` (où `source`
est une simple clé de `metadata`) est prouvée sur la vraie donnée servie.

Le garde-fou anti-SSRF rejette le loopback par conception → neutralisé *seulement
ici* (`assert_public_url` → no-op) ; sa logique propre est couverte ailleurs.
"""

from __future__ import annotations

import base64
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from xerocr.adapters.corpus import _http
from xerocr.app.corpus_import import import_escriptorium_corpus
from xerocr.domain.artifacts import ArtifactType

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HBOwAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)
TOKEN = "testtoken"


def _json(port: int, path: str) -> bytes | None:
    base = f"http://127.0.0.1:{port}"
    if path == "/api/documents/5/parts/":
        return json.dumps(
            {
                "count": 2,
                "next": f"{base}/api/documents/5/parts/?page=2",
                "results": [
                    {"pk": 42, "title": "f.1", "image": {"uri": "/media/p42.png"}}
                ],
            }
        ).encode()
    if path == "/api/documents/5/parts/?page=2":
        return json.dumps(
            {
                "count": 2,
                "next": None,
                "results": [
                    {"pk": 43, "title": "f.2", "image": {"uri": "/media/p43.png"}}
                ],
            }
        ).encode()
    if path == "/api/documents/5/parts/42/transcriptions/":
        return json.dumps(
            {
                "results": [
                    {
                        "transcription": {"name": "manual"},
                        "lines": [{"content": "hello"}, {"content": "world"}],
                    }
                ]
            }
        ).encode()
    if path == "/api/documents/5/parts/43/transcriptions/":
        return json.dumps(
            {"results": [{"transcription": {"name": "manual"}, "content": "page two"}]}
        ).encode()
    return None


@pytest.fixture
def server() -> Iterator[ThreadingHTTPServer]:
    holder: dict[str, int] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            if self.path.startswith("/api/"):
                self.server.auth_seen.append(self.headers.get("Authorization"))  # type: ignore[attr-defined]
            body = _json(holder["port"], self.path)
            ctype = "application/json"
            if body is None and self.path.startswith("/media/"):
                body, ctype = _PNG, "image/png"
            if body is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.auth_seen = []  # type: ignore[attr-defined]
    holder["port"] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_real_transport_scorable_corpus(
    server: ThreadingHTTPServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)
    port = server.server_address[1]

    spec = import_escriptorium_corpus(
        f"http://127.0.0.1:{port}", TOKEN, 5, tmp_path
    )

    # pagination (2 pages) traversée sur le vrai transport
    assert [d.id for d in spec.documents] == ["part_00042", "part_00043"]

    # GT extraite des deux formes (lignes / content) et écrite sur disque
    gt0 = spec.documents[0].ground_truths
    assert len(gt0) == 1 and gt0[0].type == ArtifactType.RAW_TEXT
    assert Path(gt0[0].uri).read_text(encoding="utf-8") == "hello\nworld"
    assert Path(spec.documents[1].ground_truths[0].uri).read_text() == "page two"

    # images réellement téléchargées (octet-exact)
    assert Path(spec.documents[0].image_uri).read_bytes() == _PNG  # type: ignore[arg-type]

    # auth : toutes les requêtes API ont porté le token
    auth = server.auth_seen  # type: ignore[attr-defined]
    assert auth and all(h == f"Token {TOKEN}" for h in auth)

    # CorpusSpec construit sans TypeError (R-7) — source en metadata, pas en kwarg
    assert spec.metadata["source"] == "escriptorium"
    assert spec.metadata["doc_pk"] == "5"
