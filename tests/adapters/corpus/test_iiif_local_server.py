"""Transport IIIF **réel** contre un serveur loopback (déterministe, CI-friendly).

Exerce le *vrai* chemin ``httpx`` de bout en bout — fetch du manifeste, parsing du
schéma servi, download de l'image, écriture disque, ``CorpusSpec`` — sans mock du
transport (ce que masquaient les mocks, finding F9). Complément du test ``live``
distant (bloqué par l'allowlist réseau de certains environnements) : ici, aucun
hôte externe, donc reproductible partout.

Le garde-fou anti-SSRF rejette le loopback **par conception** ; on le neutralise
*uniquement dans ce test* (``assert_public_url`` → no-op) pour pouvoir viser
127.0.0.1. Sa logique propre est couverte ailleurs (``test_http_ssrf.py``).
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
from xerocr.app.corpus_import import import_iiif_corpus

# PNG 1×1 valide (suffit à prouver le download octet-exact).
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HBOwAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)


def _manifest(port: int) -> bytes:
    base = f"http://127.0.0.1:{port}"
    return json.dumps(
        {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "id": f"{base}/manifest.json",
            "type": "Manifest",
            "label": {"en": ["Local"]},
            "items": [
                {
                    "id": f"{base}/canvas/1",
                    "type": "Canvas",
                    "label": {"en": ["p1"]},
                    "items": [
                        {
                            "type": "AnnotationPage",
                            "items": [
                                {
                                    "type": "Annotation",
                                    "motivation": "painting",
                                    "body": {
                                        "id": f"{base}/img.png",
                                        "type": "Image",
                                        "format": "image/png",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ).encode("utf-8")


@pytest.fixture
def server() -> Iterator[int]:
    port_holder: dict[str, int] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:  # silence
            pass

        def do_GET(self) -> None:
            if self.path.endswith("/manifest.json"):
                body, ctype = _manifest(port_holder["port"]), "application/json"
            elif self.path.endswith("/img.png"):
                body, ctype = _PNG, "image/png"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port_holder["port"] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port_holder["port"]
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_real_transport_end_to_end(
    server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Vise le loopback : on lève le garde-fou SSRF pour CE test seulement.
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)

    spec = import_iiif_corpus(
        f"http://127.0.0.1:{server}/manifest.json",
        tmp_path,
        name="local",
    )
    assert len(spec.documents) == 1
    image_path = Path(spec.documents[0].image_uri)
    assert image_path.exists()
    # download octet-exact via le vrai chemin httpx (stream + plafond)
    assert image_path.read_bytes() == _PNG
    assert spec.documents[0].ground_truths == ()
