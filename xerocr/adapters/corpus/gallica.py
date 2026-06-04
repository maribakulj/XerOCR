"""Importeur de corpus **Gallica** (BnF) — couche 5.

Gallica expose ses images via un **manifeste IIIF** (réutilisé tel quel par
``IIIFImporter``) et son **OCR brut** par page via ``f{n}.texteBrut``. Cet adapter
ne porte donc que la logique propre à Gallica : normalisation de l'**ARK**, URL du
manifeste, et récupération de l'OCR d'une page (avec filtrage des réponses HTML
que Gallica renvoie pour les pages sans OCR).

Bug latent de la source **corrigé** : la numérotation page→``texteBrut`` ne passe
plus par une indirection ``selected_indices[i]+1`` (source d'un décalage) — c'est
la **position dans le manifeste** (1-based) qui *est* le numéro de vue Gallica. Le
mapping est fait par le service ``app`` et prouvé par un test transport réel.

⚠️ L'OCR Gallica **n'est pas une vérité-terrain manuelle** : c'est la transcription
automatique de la BnF, utilisable comme *référence* (baseline) à condition de
l'étiqueter (``gt_source=gallica_ocr`` dans les métadonnées du corpus).
"""

from __future__ import annotations

import logging
import re

from xerocr.adapters.corpus._http import DEFAULT_TIMEOUT, HttpFetchError, fetch_text
from xerocr.domain.errors import XerOCRError

logger = logging.getLogger(__name__)

#: Hôte Gallica de production (surchargeable pour les tests transport).
GALLICA_BASE = "https://gallica.bnf.fr"

#: ARK normalisé : ``naID/identifiant`` (ex. ``12148/btv1b8453561w``).
_ARK_RE = re.compile(r"^[0-9]+/[A-Za-z0-9_.\-]+$")

#: Numéro de **vue** Gallica dans une URL d'image IIIF (``…/ark:/12148/X/f3/…``).
_VUE_RE = re.compile(r"/f(\d+)/")


class GallicaArkError(XerOCRError):
    """ARK Gallica malformé."""


def normalize_ark(ark: str) -> str:
    """Normalise un ARK (``ark:/12148/x`` | ``12148/x`` → ``12148/x``). Pur."""
    value = ark.strip()
    if value.startswith("ark:/"):
        value = value[len("ark:/"):]
    value = value.strip("/")
    if not _ARK_RE.match(value):
        raise GallicaArkError(
            f"ARK invalide : {ark!r}. Forme attendue 'naID/identifiant' "
            "(ex. '12148/btv1b8453561w')."
        )
    return value


def vue_number(image_url: str) -> int | None:
    """Numéro de vue Gallica extrait d'une URL d'image (``/f{n}/``), sinon ``None``.

    C'est la source **autoritaire** pour apparier une image à son
    ``f{n}.texteBrut`` : se fier à la position dans la liste d'images est faux dès
    qu'un canvas sans image est sauté par le parseur IIIF (décalage de page).
    """
    match = _VUE_RE.search(image_url)
    return int(match.group(1)) if match else None


def _looks_like_html(text: str) -> bool:
    """Gallica renvoie une page HTML (et non du texte) pour une vue sans OCR."""
    head = text[:100].lower()
    return text.startswith("<!") or "<html" in head


class GallicaImporter:
    """Localise un document Gallica : URL de manifeste IIIF + OCR par page."""

    name = "gallica"

    def __init__(
        self,
        ark: str,
        *,
        base_url: str = GALLICA_BASE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.ark = normalize_ark(ark)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def manifest_url(self) -> str:
        return f"{self._base_url}/ark:/{self.ark}/manifest.json"

    def fetch_ocr_text(self, page: int) -> str:
        """OCR brut d'une vue (1-based). ``""`` si absent (404 ou page HTML)."""
        url = f"{self._base_url}/ark:/{self.ark}/f{page}.texteBrut"
        try:
            text = fetch_text(url, timeout=self._timeout).strip()
        except HttpFetchError as exc:
            logger.warning(
                "[gallica] OCR indisponible pour %s f%d : %s", self.ark, page, exc
            )
            return ""
        return "" if _looks_like_html(text) else text


__all__ = [
    "GALLICA_BASE",
    "GallicaArkError",
    "GallicaImporter",
    "normalize_ark",
    "vue_number",
]
