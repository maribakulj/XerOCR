"""Vignettes du rapport : image → data-URI redimensionné (couche 5, adapter).

Le redimensionnement utilise **Pillow** (interdit en ``reports`` — couche 7) ; il
vit donc ici et produit un **data-URI** que le rapport embarque tel quel (les
octets ne touchent jamais le ``RunResult``). **Dégradé gracieux** : si Pillow
n'est pas installé (extra ``[images]``), si le fichier manque ou est illisible →
``None`` (le rapport retombe sur l'aperçu synthétique). Aucune exception large.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def thumbnail_data_uri(source: str | Path, *, max_px: int = 280) -> str | None:
    """Vignette JPEG **data-URI** d'une image locale ; ``None`` si indisponible.

    Redimensionne pour que le plus grand côté ≤ ``max_px`` (jamais agrandi),
    convertit en RGB, encode JPEG. ``None`` (avec ``logger.warning``) si Pillow
    absent, fichier introuvable, ou image illisible — le rendu reste fonctionnel."""
    path = Path(source)
    if not path.is_file():
        return None
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        logger.warning(
            "[images] Pillow indisponible (%s) — vignettes omises, aperçu "
            "synthétique. Installer l'extra ``[images]``.",
            exc,
        )
        return None
    try:
        with Image.open(path) as opened:
            rgb = opened.convert("RGB")
            rgb.thumbnail((max_px, max_px))
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=82, optimize=True)
    except (UnidentifiedImageError, OSError) as exc:
        logger.warning("[images] image illisible %s : %s — vignette omise.", path, exc)
        return None
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


__all__ = ["thumbnail_data_uri"]
