"""Transport HTTP **durci anti-SSRF** pour les importeurs de corpus (couche 5).

Un importeur va chercher des ressources à une URL **fournie par l'utilisateur** :
le risque est qu'on serve de proxy vers le réseau interne (SSRF) ou qu'on télécharge
sans borne (DoS mémoire/disque). Défenses, toutes testées :

- **schéma** ``http``/``https`` seuls (pas de ``file://``, ``gopher://``…) ;
- **pas de userinfo** dans l'URL ;
- **résolution DNS validée** : *toutes* les IP résolues doivent être **publiques**
  (rejet loopback / privé / link-local / réservé / multicast / non-spécifié) ;
- **redirections re-validées** à chaque saut (une 30x ne peut pas pointer vers
  l'interne) ; nombre de sauts borné ;
- **taille plafonnée** au fil de l'eau (on ne fait pas confiance à
  ``Content-Length``).

Limite résiduelle assumée : **TOCTOU/DNS-rebinding** (l'IP peut changer entre la
validation et la connexion) — acceptable pour un banc d'essai, documenté ici.
Une seule pile HTTP dans la couche (``httpx``, déjà dép. cœur via l'adapter
Ollama) ; **aucun état global** (pas d'``install_opener``).
"""

from __future__ import annotations

import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from xerocr.domain.errors import XerOCRError

#: Plafonds (généreux mais bornés — un Space gratuit n'est pas un entrepôt).
MANIFEST_MAX_BYTES = 16 * 1024 * 1024
IMAGE_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_TIMEOUT = 30.0
_MAX_REDIRECTS = 5
_ALLOWED_SCHEMES = frozenset({"http", "https"})


class CorpusHttpError(XerOCRError):
    """Échec de transport d'un importeur de corpus."""


class SsrfError(CorpusHttpError):
    """L'URL cible une ressource interdite (schéma, userinfo ou IP non publique)."""


class HttpFetchError(CorpusHttpError):
    """La requête a échoué (statut, redirection cassée, dépassement de taille)."""


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_public_url(url: str) -> None:
    """Lève ``SsrfError`` si ``url`` n'est pas une cible HTTP(S) publique.

    Résout l'hôte et exige que **toutes** les IP retournées soient publiques :
    un nom qui résout (même partiellement) vers l'interne est rejeté.
    """
    parts = urlsplit(url)
    if parts.scheme not in _ALLOWED_SCHEMES:
        raise SsrfError(f"schéma non autorisé : {parts.scheme!r} (http/https seuls).")
    if parts.username or parts.password:
        raise SsrfError("userinfo interdit dans l'URL.")
    host = parts.hostname
    if not host:
        raise SsrfError("URL sans hôte.")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise SsrfError(f"résolution DNS impossible pour {host!r} : {exc}.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not _is_public(ip):
            raise SsrfError(
                f"hôte {host!r} résout vers une IP non publique ({ip})."
            )


def _send_validated(
    client: httpx.Client, url: str, *, headers: dict[str, str] | None = None
) -> httpx.Response:
    """GET en streaming, SSRF re-validé à chaque redirection (bornée)."""
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        assert_public_url(current)
        request = client.build_request("GET", current, headers=headers)
        response = client.send(request, stream=True)
        if response.is_redirect:
            location = response.headers.get("location", "")
            response.close()
            if not location:
                raise HttpFetchError(f"redirection sans 'Location' depuis {current!r}.")
            current = str(request.url.join(location))
            continue
        return response
    raise HttpFetchError(f"trop de redirections (> {_MAX_REDIRECTS}) pour {url!r}.")


def _read_capped(response: httpx.Response, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise HttpFetchError(f"réponse dépasse le plafond de {max_bytes} octets.")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> object:
    """Récupère et parse un JSON ; anti-SSRF + plafond ``MANIFEST_MAX_BYTES``.

    ``headers`` permet l'authentification d'API (ex. ``Authorization: Token …``) ;
    il n'est jamais journalisé (les messages d'erreur ne portent que l'URL).
    """
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = _send_validated(client, url, headers=headers)
        try:
            response.raise_for_status()
            raw = _read_capped(response, MANIFEST_MAX_BYTES)
        except httpx.HTTPStatusError as exc:
            raise HttpFetchError(
                f"statut HTTP {exc.response.status_code} sur {url!r}."
            ) from exc
        finally:
            response.close()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HttpFetchError(f"réponse non-JSON depuis {url!r} : {exc}.") from exc


def download(url: str, dest: Path, *, timeout: float = DEFAULT_TIMEOUT) -> None:
    """Télécharge ``url`` vers ``dest`` ; anti-SSRF + plafond ``IMAGE_MAX_BYTES``."""
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = _send_validated(client, url)
        try:
            response.raise_for_status()
            data = _read_capped(response, IMAGE_MAX_BYTES)
        except httpx.HTTPStatusError as exc:
            raise HttpFetchError(
                f"statut HTTP {exc.response.status_code} sur {url!r}."
            ) from exc
        finally:
            response.close()
    dest.write_bytes(data)


__all__ = [
    "CorpusHttpError",
    "HttpFetchError",
    "IMAGE_MAX_BYTES",
    "MANIFEST_MAX_BYTES",
    "SsrfError",
    "assert_public_url",
    "download",
    "fetch_json",
]
