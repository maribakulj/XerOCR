"""Importeurs de corpus first-party (couche 5).

Chaque importeur **localise** des ressources (transport + parsing de schéma) et
retourne un type neutre ; la **matérialisation disque → ``CorpusSpec``** vit en
couche ``app``. Module mince, aucun effet de bord à l'import.
"""

from __future__ import annotations

from xerocr.adapters.corpus.escriptorium import (
    EScriptoriumImporter,
    EScriptoriumPage,
)
from xerocr.adapters.corpus.gallica import GallicaImporter, normalize_ark
from xerocr.adapters.corpus.iiif import IIIFImage, IIIFImporter, parse_manifest

__all__ = [
    "EScriptoriumImporter",
    "EScriptoriumPage",
    "GallicaImporter",
    "IIIFImage",
    "IIIFImporter",
    "normalize_ark",
    "parse_manifest",
]
