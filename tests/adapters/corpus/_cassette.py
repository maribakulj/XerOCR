"""Transport **de replay** : rejoue une cassette HTTP enregistrée, hors-ligne.

Pendant du script de capture (``scripts/capture_cassettes.py``). Une cassette
(``tests/fixtures/cassettes/<nom>.json``) contient des interactions
``requête → réponse`` ; ``replaying(nom)`` branche ce transport dans la pile
``_http`` (via le seam ``_make_client``) et neutralise l'anti-SSRF, le temps d'un
bloc — les **vrais** importeurs tournent alors **sans réseau**, sur des réponses
réelles enregistrées. Match par ``(méthode, schéma, hôte, chemin, query triée)``.
"""

from __future__ import annotations

import base64
import contextlib
import json
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx

from xerocr.adapters.corpus import _http

_CASSETTES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "cassettes"

_RequestKey = tuple[str, str, str | None, str, tuple[tuple[str, str], ...]]


class CassetteMiss(AssertionError):
    """Une requête n'a pas d'interaction enregistrée dans la cassette."""


def _request_key(method: str, url: str) -> _RequestKey:
    parts = urlsplit(url)
    return (
        method.upper(),
        parts.scheme,
        parts.hostname,
        parts.path,
        tuple(sorted(parse_qsl(parts.query))),
    )


class _ReplayTransport(httpx.BaseTransport):
    def __init__(self, cassette: Path) -> None:
        data = json.loads(cassette.read_text(encoding="utf-8"))
        self._queues: dict[_RequestKey, list[dict[str, object]]] = {}
        for interaction in data["interactions"]:
            req = interaction["request"]
            key = _request_key(req["method"], req["url"])
            self._queues.setdefault(key, []).append(interaction["response"])

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        key = _request_key(request.method, str(request.url))
        queue = self._queues.get(key)
        if not queue:
            raise CassetteMiss(
                f"interaction absente de la cassette : {request.method} {request.url}"
            )
        response = queue.pop(0)
        headers = response.get("headers", {})
        body = base64.b64decode(str(response["body_b64"]))
        return httpx.Response(
            status_code=int(response["status_code"]),  # type: ignore[call-overload]
            headers=dict(headers),  # type: ignore[arg-type]
            content=body,
            request=request,
        )


@contextlib.contextmanager
def replaying(cassette_name: str) -> Iterator[None]:
    """Rejoue ``<cassette_name>.json`` dans la pile ``_http`` (sans réseau)."""
    transport = _ReplayTransport(_CASSETTES_DIR / f"{cassette_name}.json")
    orig_make_client = _http._make_client
    orig_assert = _http.assert_public_url

    def _make_client(pins: object, timeout: float) -> httpx.Client:
        return httpx.Client(transport=transport, follow_redirects=False)

    _http._make_client = _make_client  # type: ignore[assignment]
    _http.assert_public_url = lambda url: None  # type: ignore[assignment,return-value]
    try:
        yield
    finally:
        _http._make_client = orig_make_client  # type: ignore[assignment]
        _http.assert_public_url = orig_assert  # type: ignore[assignment]


__all__ = ["CassetteMiss", "replaying"]
