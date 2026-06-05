"""Transport Gallica **réel** contre un serveur loopback (déterministe, CI).

Sert un manifeste **IIIF** (préfixe ``/iiif/``) + images + OCR **ALTO**
(``RequestDigitalElement``), et fait tourner ``import_gallica_corpus`` sur le
**vrai chemin httpx**. Prouve sur transport réel :

- l'URL de manifeste **IIIF correcte** (``/iiif/…`` — l'ancienne renvoyait 403) ;
- le **mapping vue→OCR** lu dans l'URL d'image (``/f{n}/``), **pas la position** :
  les vues f8 et f10 sont aux positions 1 et 2 → docs ``f0008``/``f0010`` (la
  régression ``selected_indices[i]+1`` aurait produit f1/f2) ;
- l'extraction **ALTO** (``String/@CONTENT``) à la bonne vue ;
- l'absence d'ALTO (404) → page **image-seule**.
"""

from __future__ import annotations

import base64
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from xerocr.adapters.corpus import _http
from xerocr.app.corpus_import import import_gallica_corpus

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HBOwAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)
ARK = "12148/btv1bTEST"


def _alto(*words: str) -> bytes:
    strings = "".join(f'<String CONTENT="{w}"/>' for w in words)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<alto xmlns="http://www.loc.gov/standards/alto/ns-v2#"><Layout><Page>'
        f"<PrintSpace><TextBlock><TextLine>{strings}</TextLine>"
        "</TextBlock></PrintSpace></Page></Layout></alto>"
    ).encode()


def _manifest(port: int) -> bytes:
    base = f"http://127.0.0.1:{port}"
    # Vues f8 et f10 AUX POSITIONS 1 et 2 (la vue ≠ la position).
    img = "{b}/iiif/ark:/{a}/f{n}/full/max/0/default.jpg"
    return json.dumps(
        {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": f"{base}/iiif/ark:/{ARK}/manifest.json",
            "sequences": [
                {
                    "canvases": [
                        {
                            "label": "f8",
                            "images": [
                                {"resource": {"@id": img.format(b=base, a=ARK, n=8)}}
                            ],
                        },
                        {
                            "label": "f10",
                            "images": [
                                {"resource": {"@id": img.format(b=base, a=ARK, n=10)}}
                            ],
                        },
                    ]
                }
            ],
        }
    ).encode()


@pytest.fixture
def server() -> Iterator[int]:
    holder: dict[str, int] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            path = parts.path
            body: bytes
            ctype = "application/xml"
            if path == f"/iiif/ark:/{ARK}/manifest.json":
                body, ctype = _manifest(holder["port"]), "application/json"
            elif path == "/RequestDigitalElement":
                deb = parse_qs(parts.query).get("Deb", [""])[0]
                if deb == "8":
                    body = _alto("Texte", "vue", "huit")
                else:  # f10 : pas d'OCR disponible → 404 → image-seule
                    self.send_error(404)
                    return
            elif path.endswith("default.jpg"):
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
    holder["port"] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield holder["port"]
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_real_transport_iiif_manifest_and_alto_ocr(
    server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)

    spec = import_gallica_corpus(ARK, tmp_path, base_url=f"http://127.0.0.1:{server}")

    # vue lue dans l'URL (/f{n}/), pas la position : f8 et f10 (pas f1/f2)
    assert [d.id for d in spec.documents] == ["f0008", "f0010"]
    # vue 8 → ALTO Deb=8 → texte extrait (String/@CONTENT en ordre de lecture)
    gt8 = spec.documents[0].ground_truths
    assert len(gt8) == 1
    assert Path(gt8[0].uri).read_text(encoding="utf-8") == "Texte vue huit"
    # vue 10 → ALTO 404 → image-seule
    assert spec.documents[1].ground_truths == ()
    # images réellement téléchargées via le vrai chemin httpx
    assert Path(spec.documents[0].image_uri).read_bytes() == _PNG  # type: ignore[arg-type]
    assert spec.metadata["source"] == "gallica"
    assert spec.metadata["gt_source"] == "gallica_ocr"
