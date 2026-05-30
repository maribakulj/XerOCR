"""Lecture de texte brut (``.gt.txt``, transcriptions plates).

Centralise le décodage : encodage, BOM, fins de ligne. Ne **produit** jamais de
texte (pas d'écrivain) ; distinct de la normalisation (préparation à la
comparaison), qui vient après. Opère sur des ``bytes`` (zéro I/O ici).
"""

from __future__ import annotations

_UTF8_BOM = b"\xef\xbb\xbf"


def read_plaintext(data: bytes, encoding: str = "utf-8") -> str:
    """Décode des octets de texte brut en chaîne.

    - retire le BOM UTF-8 en tête (octets) et tout U+FEFF résiduel ;
    - normalise les fins de ligne (``\\r\\n`` / ``\\r`` → ``\\n``).
    """
    if data.startswith(_UTF8_BOM):
        data = data[len(_UTF8_BOM):]
    text = data.decode(encoding).lstrip("﻿")
    return text.replace("\r\n", "\n").replace("\r", "\n")
