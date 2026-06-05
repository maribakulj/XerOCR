"""Importeur de corpus **Gallica** (BnF) — couche 5.

Gallica expose ses images via un **manifeste IIIF** (réutilisé tel quel par
``IIIFImporter``) et son OCR par page via l'endpoint **ALTO** officiel
``RequestDigitalElement``. Cet adapter ne porte que la logique propre à Gallica :
normalisation de l'**ARK**, URL du manifeste IIIF, et récupération de l'OCR d'une
page (ALTO → texte en ordre de lecture).

Choix : **ALTO** plutôt que ``texteBrut``. L'endpoint ``f{n}.texteBrut`` est
désormais protégé par un challenge anti-bot (ALTCHA) en accès automatisé, donc
inutilisable en import ; ``RequestDigitalElement?...&E=ALTO`` reste accessible et
plus riche (on en extrait le texte via le parseur ALTO de la couche 2).

Bug latent de la source **corrigé** : la numérotation page→OCR ne passe plus par
une indirection ``selected_indices[i]+1`` (source d'un décalage) — c'est la
**vue Gallica** lue dans l'URL d'image IIIF (``/f{n}/``) qui *est* le ``Deb`` de
la requête ALTO. Le mapping est fait par le service ``app`` et prouvé par test.

⚠️ L'OCR Gallica **n'est pas une vérité-terrain manuelle** : c'est la transcription
automatique de la BnF, utilisable comme *référence* (baseline) à condition de
l'étiqueter (``gt_source=gallica_ocr`` dans les métadonnées du corpus).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlencode

from xerocr.adapters.corpus._http import DEFAULT_TIMEOUT, HttpFetchError, fetch_bytes
from xerocr.domain.errors import FormatError, XerOCRError
from xerocr.formats.alto import (
    AltoBlock,
    AltoComposedBlock,
    AltoDocument,
    AltoTextBlock,
    parse_alto,
)

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

    C'est la source **autoritaire** pour apparier une image à son OCR : se fier à
    la position dans la liste d'images est faux dès qu'un canvas sans image est
    sauté par le parseur IIIF (décalage de page).
    """
    match = _VUE_RE.search(image_url)
    return int(match.group(1)) if match else None


def _block_lines(blocks: tuple[AltoBlock, ...], out: list[str]) -> None:
    """Aplatit les ``<TextBlock>`` (récursif sur les ``<ComposedBlock>``) en lignes."""
    for block in blocks:
        if isinstance(block, AltoTextBlock):
            for line in block.lines:
                text = " ".join(s.content for s in line.strings if s.content)
                if text:
                    out.append(text)
        elif isinstance(block, AltoComposedBlock):
            _block_lines(block.blocks, out)


def alto_to_text(document: AltoDocument) -> str:
    """Texte d'un ALTO en **ordre de lecture** : lignes (``String/@CONTENT``) jointes.

    Pas de dé-césure (le ``texteBrut`` historique n'en faisait pas non plus) : on
    rend le contenu brut, ligne par ligne.
    """
    lines: list[str] = []
    for page in document.pages:
        _block_lines(page.blocks, lines)
    return "\n".join(lines)


class GallicaImporter:
    """Localise un document Gallica : URL de manifeste IIIF + OCR ALTO par page."""

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
    def _identifier(self) -> str:
        """Identifiant de la numérisation (ARK sans le naID) — param ``O`` de l'ALTO."""
        return self.ark.split("/", 1)[1]

    @property
    def manifest_url(self) -> str:
        return f"{self._base_url}/iiif/ark:/{self.ark}/manifest.json"

    def alto_url(self, page: int) -> str:
        """URL ALTO officielle d'une vue (``RequestDigitalElement``)."""
        query = urlencode({"O": self._identifier, "E": "ALTO", "Deb": page})
        return f"{self._base_url}/RequestDigitalElement?{query}"

    def fetch_ocr_text(self, page: int) -> str:
        """OCR d'une vue (1-based) via ALTO → texte. ``""`` si absent ou illisible."""
        try:
            data = fetch_bytes(self.alto_url(page), timeout=self._timeout)
        except HttpFetchError as exc:
            logger.warning(
                "[gallica] ALTO indisponible pour %s f%d : %s", self.ark, page, exc
            )
            return ""
        try:
            return alto_to_text(parse_alto(data))
        except FormatError as exc:  # ALTO malformé ou XML invalide
            logger.warning(
                "[gallica] ALTO illisible pour %s f%d : %s", self.ark, page, exc
            )
            return ""


__all__ = [
    "GALLICA_BASE",
    "GallicaArkError",
    "GallicaImporter",
    "alto_to_text",
    "normalize_ark",
    "vue_number",
]
