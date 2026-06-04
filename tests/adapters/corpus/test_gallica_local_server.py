"""Transport Gallica **réel** contre un serveur loopback (déterministe, CI).

Sert un manifeste IIIF v2 Gallica + des images + l'OCR brut par vue, et fait
tourner `import_gallica_corpus` sur le **vrai chemin httpx** (IIIF + download +
`texteBrut`). Prouve sur transport réel :

- le **mapping page→OCR corrigé** (vue 1 ↔ ``f1``, vue 2 ↔ ``f2``) — la régression
  ``selected_indices[i]+1`` aurait décalé l'OCR ;
- le **filtrage HTML** : une vue dont ``texteBrut`` renvoie du HTML (pas d'OCR)
  reste image-seule.
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
from xerocr.app.corpus_import import import_gallica_corpus

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HBOwAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)
ARK = "12148/btv1bTEST"
_OCR_VUE_1 = "Texte OCR de la vue 1."
_HTML_NO_OCR = "<!DOCTYPE html><html><body>pas d'OCR</body></html>"


def _manifest(port: int) -> bytes:
    base = f"http://127.0.0.1:{port}"
    return json.dumps(
        {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": f"{base}/ark:/{ARK}/manifest.json",
            "sequences": [
                {
                    "canvases": [
                        {
                            "label": "f1",
                            "images": [{"resource": {"@id": f"{base}/iiif/1.png"}}],
                        },
                        {
                            "label": "f2",
                            "images": [{"resource": {"@id": f"{base}/iiif/2.png"}}],
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
            path = self.path
            body: bytes
            ctype = "text/plain; charset=utf-8"
            if path == f"/ark:/{ARK}/manifest.json":
                body, ctype = _manifest(holder["port"]), "application/json"
            elif path == f"/ark:/{ARK}/f1.texteBrut":
                body = _OCR_VUE_1.encode("utf-8")
            elif path == f"/ark:/{ARK}/f2.texteBrut":
                body, ctype = _HTML_NO_OCR.encode("utf-8"), "text/html"
            elif path.startswith("/iiif/"):
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


def test_real_transport_images_and_mapped_ocr(
    server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_http, "assert_public_url", lambda url: None)

    spec = import_gallica_corpus(
        ARK, tmp_path, base_url=f"http://127.0.0.1:{server}"
    )

    assert [d.id for d in spec.documents] == ["f0001", "f0002"]
    # vue 1 → f1.texteBrut (mapping correct, transport réel)
    gt1 = spec.documents[0].ground_truths
    assert len(gt1) == 1
    assert Path(gt1[0].uri).read_text(encoding="utf-8") == _OCR_VUE_1
    # vue 2 → f2.texteBrut renvoie du HTML → filtré → image seule
    assert spec.documents[1].ground_truths == ()
    # images réellement téléchargées
    assert Path(spec.documents[0].image_uri).read_bytes() == _PNG  # type: ignore[arg-type]
    assert spec.metadata["source"] == "gallica"
    assert spec.metadata["ark"] == ARK
    assert spec.metadata["gt_source"] == "gallica_ocr"
