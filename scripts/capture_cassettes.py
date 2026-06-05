#!/usr/bin/env python3
"""Capture de **cassettes HTTP** pour les importeurs de corpus XerOCR (Lot E).

Rejoue les **vrais** importeurs (IIIF / Gallica / eScriptorium) et la recherche
de découverte HuggingFace contre les sources réelles, en interceptant chaque
requête ``httpx`` émise, et enregistre les interactions (requête → réponse) dans
des fichiers JSON sous ``tests/fixtures/cassettes/``. Un « transport de replay »
(écrit séparément, côté tests) rejouera ces cassettes **hors-ligne** pour prouver
le parsing réel — en particulier le mapping Gallica vue *i* ↔ ``…/f{i}/…texteBrut``.

À lancer dans un environnement **avec réseau** (le sandbox CI/dev de XerOCR a une
allowlist qui bloque la capture) :

    pip install -e ".[dev]"
    python scripts/capture_cassettes.py --only iiif,gallica,hf
    # eScriptorium (instance privée + token) :
    export XEROCR_ESCRIPTORIUM_BASE_URL=https://… XEROCR_ESCRIPTORIUM_TOKEN=… \
           XEROCR_ESCRIPTORIUM_DOC_PK=42
    python scripts/capture_cassettes.py --only escriptorium

Sécurité : **aucun en-tête de requête n'est enregistré** (le token eScriptorium
voyage en en-tête → il ne peut pas fuiter dans une cassette) ; les paramètres de
query sensibles (``token``/``key``/``api_key``) sont rédigés des URLs.

Hors périmètre : l'**import** d'un dataset HuggingFace passe par la lib
``datasets`` (streaming), pas par ``httpx`` → non capturable en cassette HTTP
(seule la **recherche** de découverte du Hub l'est).
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import logging
import os
import sys
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Permet de lancer le script depuis un checkout sans réinstaller le paquet, tant
# que les dépendances (httpx, pydantic, …) sont présentes dans l'environnement.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import httpx

    import xerocr.adapters.corpus._http as _http
    from xerocr.app.corpus_import import (
        import_gallica_corpus,
        import_iiif_corpus,
    )
except ModuleNotFoundError as exc:  # paquet ou dépendance non installé
    raise SystemExit(
        f"Dépendance introuvable : {exc.name!r}.\n"
        "Installe XerOCR et ses deps depuis la racine du repo :\n"
        '    pip install -e ".[dev]"\n'
        "puis relance le script."
    ) from exc

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("capture")

#: En-têtes de réponse conservés dans la cassette (suffisent au rejeu :
#: ``location`` pour suivre une 30x, ``content-type`` pour le diagnostic).
_KEPT_RESPONSE_HEADERS = ("content-type", "location")
#: Query params rédigés des URLs enregistrées (défense en profondeur).
_SECRET_QUERY_KEYS = frozenset({"token", "key", "api_key", "apikey", "access_token"})
#: Au-delà, un corps **image** est remplacé par un PNG 1×1 dans la cassette
#: (le test vérifie le parsing/mapping, pas la fidélité de l'image).
_DEFAULT_PLACEHOLDER_THRESHOLD = 256 * 1024
#: PNG 1×1 transparent, valide (placeholder déterministe).
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

#: Défauts publics & stables (override en CLI). Gallica = à remplacer par un ARK
#: réel **portant de l'OCR** (``texteBrut``) pour figer le mapping ``/f{n}/``.
_DEFAULT_IIIF_MANIFEST = "https://iiif.io/api/cookbook/recipe/0009-book-1/manifest.json"
_DEFAULT_GALLICA_ARK = "ark:/12148/bpt6k5619759j"


def _redact_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = [
        (k, "<redacted>" if k.lower() in _SECRET_QUERY_KEYS else v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(parts._replace(query=urlencode(pairs)))


class _Recorder:
    """Collecte les interactions d'un scénario."""

    def __init__(self, placeholder_threshold: int) -> None:
        self.interactions: list[dict[str, object]] = []
        self._threshold = placeholder_threshold

    def record(
        self,
        method: str,
        url: str,
        status_code: int,
        headers: httpx.Headers,
        body: bytes,
    ) -> None:
        kept = {
            name: headers[name]
            for name in _KEPT_RESPONSE_HEADERS
            if name in headers
        }
        content_type = kept.get("content-type", "")
        placeholder = (
            len(body) > self._threshold and content_type.startswith("image/")
        )
        stored = _PNG_1X1 if placeholder else body
        self.interactions.append(
            {
                "request": {"method": method, "url": _redact_url(url)},
                "response": {
                    "status_code": status_code,
                    "headers": kept,
                    "body_b64": base64.b64encode(stored).decode("ascii"),
                    "image_placeholder": placeholder,
                },
            }
        )


class _RecordingTransport(httpx.BaseTransport):
    """Transport ``httpx`` qui **enregistre** puis transmet au vrai réseau.

    Le corps réel est rendu à l'appelant (l'import réussit) ; seule la cassette
    peut recevoir un placeholder pour les grosses images.
    """

    def __init__(self, recorder: _Recorder, *, user_agent: str | None = None) -> None:
        self._recorder = recorder
        self._user_agent = user_agent
        self._inner = httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # Demande une réponse **non compressée** : évite le piège content-encoding
        # quand on reconstruit la réponse (sinon double décompression côté
        # appelant → « incorrect header check »).
        request.headers["accept-encoding"] = "identity"
        if self._user_agent:
            request.headers["user-agent"] = self._user_agent
        inner = self._inner.handle_request(request)
        try:
            raw = inner.read()
        finally:
            inner.close()
        self._recorder.record(
            request.method, str(request.url), inner.status_code, inner.headers, raw
        )
        # ``read()`` a déjà décodé le corps : on retire content-encoding/length
        # (et transfer-encoding) pour que l'appelant ne re-décompresse pas, puis
        # on recale content-length sur le corps réel.
        headers = httpx.Headers(inner.headers)
        for name in ("content-encoding", "content-length", "transfer-encoding"):
            if name in headers:
                del headers[name]
        headers["content-length"] = str(len(raw))
        return httpx.Response(
            status_code=inner.status_code,
            headers=headers,
            content=raw,
            request=request,
            extensions=inner.extensions,
        )

    def close(self) -> None:
        self._inner.close()


@contextlib.contextmanager
def _recording(
    placeholder_threshold: int, *, user_agent: str | None = None
) -> Iterator[_Recorder]:
    """Installe le transport enregistreur dans ``_http`` le temps d'un scénario.

    Neutralise aussi l'anti-SSRF pendant la capture (on cible des hôtes publics
    de confiance, fournis par l'opérateur) — sinon identique au chemin de prod.
    """
    recorder = _Recorder(placeholder_threshold)
    orig_make_client = _http._make_client
    orig_assert = _http.assert_public_url

    def _make_client(pins: object, timeout: float) -> httpx.Client:
        return httpx.Client(
            transport=_RecordingTransport(recorder, user_agent=user_agent),
            timeout=timeout,
            follow_redirects=False,
        )

    _http._make_client = _make_client  # type: ignore[assignment]
    _http.assert_public_url = lambda url: None  # type: ignore[assignment,return-value]
    try:
        yield recorder
    finally:
        _http._make_client = orig_make_client  # type: ignore[assignment]
        _http.assert_public_url = orig_assert  # type: ignore[assignment]


def _write_cassette(out_dir: Path, scenario: str, recorder: _Recorder) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario": scenario,
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interactions": recorder.interactions,
    }
    path = out_dir / f"{scenario}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    total = 0
    for interaction in recorder.interactions:
        response = interaction["response"]
        assert isinstance(response, dict)
        total += len(str(response["body_b64"]))
    logger.info(
        "  ✓ %s : %d interactions (~%d Ko base64) → %s",
        scenario,
        len(recorder.interactions),
        total // 1024,
        path,
    )


def _run_scenario(
    scenario: str,
    out_dir: Path,
    placeholder_threshold: int,
    body: Callable[[Path], None],
    *,
    user_agent: str | None = None,
) -> bool:
    """Exécute ``body`` (l'import réel) sous enregistrement → écrit la cassette."""
    logger.info("• %s …", scenario)
    try:
        with _recording(
            placeholder_threshold, user_agent=user_agent
        ) as recorder, TemporaryDirectory(
            prefix=f"xerocr-cassette-{scenario}-"
        ) as workspace:
            body(Path(workspace))
    except Exception as exc:  # un scénario raté ne bloque pas les autres
        logger.warning("  ✗ %s échoué : %s", scenario, exc)
        return False
    if not recorder.interactions:
        logger.warning("  ✗ %s : aucune interaction capturée (rien écrit).", scenario)
        return False
    _write_cassette(out_dir, scenario, recorder)
    return True


def _capture_iiif(manifest_url: str, max_pages: int) -> Callable[[Path], None]:
    def _body(dest: Path) -> None:
        import_iiif_corpus(manifest_url, dest, name="iiif", limit=max_pages)

    return _body


def _capture_gallica(ark: str, max_pages: int) -> Callable[[Path], None]:
    def _body(dest: Path) -> None:
        import_gallica_corpus(ark, dest, name="gallica", limit=max_pages)

    return _body


def _capture_escriptorium(max_pages: int) -> Callable[[Path], None] | None:
    base_url = os.environ.get("XEROCR_ESCRIPTORIUM_BASE_URL")
    token = os.environ.get("XEROCR_ESCRIPTORIUM_TOKEN")
    doc_pk = os.environ.get("XEROCR_ESCRIPTORIUM_DOC_PK")
    if not (base_url and token and doc_pk):
        logger.info(
            "• escriptorium … ignoré (XEROCR_ESCRIPTORIUM_{BASE_URL,TOKEN,DOC_PK} "
            "absents)."
        )
        return None

    def _body(dest: Path) -> None:
        # Import paresseux : eScriptorium n'est dans le scope que si configuré.
        from xerocr.app.corpus_import import import_escriptorium_corpus

        import_escriptorium_corpus(
            base_url, token, int(doc_pk), dest, name="escriptorium", limit=max_pages
        )

    return _body


def _capture_hf() -> Callable[[Path], None]:
    def _body(_dest: Path) -> None:
        # Recherche de découverte du Hub (GET httpx) — l'import de dataset
        # (lib `datasets`, streaming) est hors périmètre cassette.
        from xerocr.adapters.corpus.huggingface import HuggingFaceCatalogue

        HuggingFaceCatalogue().search("manuscript")

    return _body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iiif-manifest", default=_DEFAULT_IIIF_MANIFEST)
    parser.add_argument(
        "--gallica-ark",
        default=_DEFAULT_GALLICA_ARK,
        help="ARK Gallica RÉEL portant de l'OCR (texteBrut) — remplace le défaut.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("tests/fixtures/cassettes"),
    )
    parser.add_argument(
        "--only",
        default="iiif,gallica,escriptorium,hf",
        help="Scénarios à capturer (CSV parmi iiif,gallica,escriptorium,hf).",
    )
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument(
        "--placeholder-threshold", type=int, default=_DEFAULT_PLACEHOLDER_THRESHOLD
    )
    parser.add_argument(
        "--user-agent",
        default=None,
        help="User-Agent à envoyer (un UA navigateur peut débloquer certaines "
        "sources ; un 403 Gallica sur IP cloud peut toutefois persister).",
    )
    args = parser.parse_args(argv)

    selected = {s.strip() for s in args.only.split(",") if s.strip()}
    out_dir: Path = args.out_dir
    ok: list[str] = []
    failed: list[str] = []

    plans: list[tuple[str, Callable[[Path], None] | None]] = [
        ("iiif", _capture_iiif(args.iiif_manifest, args.max_pages)),
        ("gallica", _capture_gallica(args.gallica_ark, args.max_pages)),
        ("escriptorium", _capture_escriptorium(args.max_pages)),
        ("hf", _capture_hf()),
    ]
    for scenario, body in plans:
        if scenario not in selected:
            continue
        if body is None:  # escriptorium non configuré → skip propre
            continue
        if _run_scenario(
            scenario,
            out_dir,
            args.placeholder_threshold,
            body,
            user_agent=args.user_agent,
        ):
            ok.append(scenario)
        else:
            failed.append(scenario)

    logger.info("")
    logger.info("Résumé : %d capturé(s) [%s]", len(ok), ", ".join(ok) or "—")
    if failed:
        logger.warning("        %d échec(s) [%s]", len(failed), ", ".join(failed))
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
