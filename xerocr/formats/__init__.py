"""Couche 2 — Formats documentaires.

Frontière entre les formats de fil (ALTO XML, PAGE XML, texte brut) et le reste du
système. N'opère que sur des ``bytes`` / des chaînes ; jamais sur un résultat
d'OCR ou un calcul de métrique. Peut importer ``lxml`` et ``pyyaml`` ; jamais une
lib de métrique (``jiwer``, ``rapidfuzz``) ni un moteur OCR.

Surface publique (s'étoffera avec les parsers/writers ALTO et PAGE) :

- sécurité XML (``safe_parse_xml``) — point d'entrée unique de tout parsing XML ;
- normalisation de comparaison (``NormalizationProfile`` & profils) ;
- lecture de texte brut (``read_plaintext``).
"""

from __future__ import annotations

from xerocr.formats._xml import safe_parse_xml
from xerocr.formats.text import (
    DEFAULT_PROFILE,
    NORMALIZATION_PROFILES,
    NormalizationProfile,
    get_builtin_profile,
    read_plaintext,
)

__all__ = [
    "safe_parse_xml",
    "NormalizationProfile",
    "NORMALIZATION_PROFILES",
    "DEFAULT_PROFILE",
    "get_builtin_profile",
    "read_plaintext",
]
