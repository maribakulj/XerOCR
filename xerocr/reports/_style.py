"""Polices du rapport autonome **incorporées en data-URI** (couche 7).

Décision **D-019** (option (a), préparée par D-018) : plutôt que des polices système
(identité partielle) ou ``/static`` (perd l'autonomie du *standalone*), on
**incorpore** les woff2 du design en ``data:`` URI. Le rapport garde son identité
typographique — titres **Fluxisch Else**, corps + données **OCR-A** — **tout en
restant 100 % autonome** (aucun CDN, ``@import`` ni ``<link>``) et **octet-stable**
(le base64 d'octets figés est déterministe).

Les woff2 vivent en ``reports/_assets/`` (couche 7) : le rapport **ne dépend pas**
de la couche 8 (``interfaces/web/static``) pour ses polices.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from importlib.resources import files

#: (famille CSS, plage de poids, fichier woff2) — sous-ensemble réellement
#: utilisé par le rapport : Fluxisch Else (titres) + OCR-A (corps/données).
_FONTS: tuple[tuple[str, str, str], ...] = (
    ("Fluxisch Else", "400", "FluxischElse-Regular.woff2"),
    ("Fluxisch Else", "600 700", "FluxischElse-Bold.woff2"),
    ("OCRA", "400", "OCRA.woff2"),
)


def _face(family: str, weight: str, filename: str) -> str:
    data = (files("xerocr.reports").joinpath("_assets", filename)).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return (
        f"@font-face{{font-family:'{family}';font-weight:{weight};"
        f"font-style:normal;font-display:swap;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
    )


@lru_cache(maxsize=1)
def font_face_css() -> str:
    """Blocs ``@font-face`` (data-URI) des polices du rapport. Déterministe."""
    return "".join(_face(*f) for f in _FONTS)


__all__ = ["font_face_css"]
