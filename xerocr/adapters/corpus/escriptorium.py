"""Importeur de corpus **eScriptorium** (API REST) — couche 5.

Rôle : **localiser** les pages d'un document eScriptorium (auth par token →
liste paginée des *parts* + leur transcription) et retourner un type neutre. La
**matérialisation disque** (download image + écriture GT → ``CorpusSpec``) vit en
couche ``app`` (``app/corpus_import.py``).

Contrairement à IIIF, eScriptorium porte une **vérité-terrain** (la couche de
transcription choisie) → le corpus importé est **scorable** (CER/WER).

API consommée (lecture seule) :

- ``GET /api/documents/{pk}/parts/``                       → pages (paginé) ;
- ``GET /api/documents/{pk}/parts/{pk}/transcriptions/``   → transcriptions.

Dette de la source **non reprise** : l'export distant de couche OCR, le listing
projets/connexion (surface morte ~40 %), et surtout le bug latent
``Corpus(source=…)`` — ici la sortie est un ``CorpusSpec`` (``source`` va dans
``metadata``), structurellement à l'abri.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

from xerocr.adapters.corpus._http import DEFAULT_TIMEOUT, HttpFetchError, fetch_json

logger = logging.getLogger(__name__)

#: Couche de transcription par défaut (libellé eScriptorium usuel pour la GT).
DEFAULT_LAYER = "manual"
#: Borne de pagination (un document = au plus quelques milliers de pages).
_MAX_PAGES = 10_000


@dataclass(frozen=True)
class EScriptoriumPage:
    """Une page (*part*) : son URL d'image absolue + son texte GT (peut être vide)."""

    pk: int
    image_url: str
    gt_text: str
    title: str


def _image_uri(item: dict[str, Any], base_url: str) -> str:
    """Extrait l'URL d'image d'une *part* (champ ``image`` : str ou objet)."""
    img = item.get("image")
    if isinstance(img, dict):
        img = img.get("uri") or img.get("url") or ""
    if not isinstance(img, str) or not img:
        return ""
    return urljoin(base_url, img)


def _layer_name(transcription: dict[str, Any]) -> str:
    nested = transcription.get("transcription")
    if isinstance(nested, dict):
        return str(nested.get("name", ""))
    return str(transcription.get("name", ""))


def extract_gt_text(transcriptions: list[dict[str, Any]], layer: str) -> str:
    """Texte GT de la couche ``layer`` (lignes jointes, ou ``content``). Pur.

    ``layer`` vide → première transcription rencontrée. Renvoie ``""`` si la
    couche demandée est absente.
    """
    for transcription in transcriptions:
        if layer and _layer_name(transcription) != layer:
            continue
        lines = transcription.get("lines") or []
        if lines:
            return "\n".join(
                str(line.get("content", ""))
                for line in lines
                if isinstance(line, dict) and line.get("content")
            )
        return str(transcription.get("content", "") or "")
    return ""


class EScriptoriumImporter:
    """Localise les pages d'un document eScriptorium (auth + API, **sans disque**)."""

    name = "escriptorium"

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        layer: str = DEFAULT_LAYER,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._layer = layer
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        # Le token n'est jamais journalisé (cf. _http : erreurs sans en-têtes).
        return {"Authorization": f"Token {self._token}", "Accept": "application/json"}

    def _get(self, url: str) -> dict[str, Any]:
        data = fetch_json(url, timeout=self._timeout, headers=self._headers())
        if not isinstance(data, dict):
            raise HttpFetchError(
                f"réponse eScriptorium inattendue (objet JSON attendu) : {url!r}."
            )
        return data

    def _paginate(self, path: str) -> list[dict[str, Any]]:
        """Suit les liens ``next`` jusqu'à épuisement, **sans quitter l'hôte**.

        Le ``next`` est contrôlé par le serveur : on **n'envoie jamais le jeton**
        vers un hôte différent de ``base_url`` (un ``next`` cross-hôte est ignoré).
        """
        base_host = urlsplit(self._base_url).hostname
        results: list[dict[str, Any]] = []
        url: str | None = f"{self._base_url}/api/{path.lstrip('/')}"
        for _ in range(_MAX_PAGES):
            if not url:
                break
            data = self._get(url)
            page = data.get("results")
            results.extend(page if isinstance(page, list) else [])
            nxt = data.get("next")
            if not (isinstance(nxt, str) and nxt):
                break
            if urlsplit(nxt).hostname != base_host:
                logger.warning(
                    "[escriptorium] lien 'next' hors hôte ignoré (pas de jeton "
                    "envoyé à un tiers) : %s",
                    nxt,
                )
                break
            url = nxt
        return results

    def _transcriptions(self, doc_pk: int, part_pk: int) -> list[dict[str, Any]]:
        url = f"{self._base_url}/api/documents/{doc_pk}/parts/{part_pk}/transcriptions/"
        data = fetch_json(url, timeout=self._timeout, headers=self._headers())
        if isinstance(data, list):
            return [t for t in data if isinstance(t, dict)]
        if isinstance(data, dict):
            page = data.get("results")
            if isinstance(page, list):
                return [t for t in page if isinstance(t, dict)]
        return []

    def fetch_pages(self, doc_pk: int) -> tuple[EScriptoriumPage, ...]:
        pages: list[EScriptoriumPage] = []
        for item in self._paginate(f"documents/{doc_pk}/parts/"):
            pk = item.get("pk")
            if not isinstance(pk, int):
                continue
            transcriptions = self._transcriptions(doc_pk, pk)
            pages.append(
                EScriptoriumPage(
                    pk=pk,
                    image_url=_image_uri(item, self._base_url),
                    gt_text=extract_gt_text(transcriptions, self._layer),
                    title=str(item.get("title", "") or f"part {pk}"),
                )
            )
        return tuple(pages)


__all__ = [
    "DEFAULT_LAYER",
    "EScriptoriumImporter",
    "EScriptoriumPage",
    "extract_gt_text",
]
