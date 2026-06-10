"""Persistance + démo de **segmentation** (couche 6) pour la vitrine.

Un run de segmentation produit un ``CanonicalLayout`` (géométrie des régions) que
le ``RunResult`` (métriques scalaires) **ne porte pas** et que le workspace
temporaire du run **détruit**. Ce store le **persiste** (layout JSON + image
source optionnelle) pour qu'une vue web le relise et le visualise.

Squelette : un layout de **démo** déterministe alimente toute
l'enveloppe de visualisation. La Tranche 2 (vrai segmenteur) écrira son
``CanonicalLayout`` produit **via le même** ``save`` — l'infra ne bouge pas.
"""

from __future__ import annotations

import struct
import threading
import uuid
import zlib
from pathlib import Path

from xerocr.app.security import PathSecurityError, validated_path
from xerocr.domain.layout import BBox, CanonicalLayout, Geometry, LayoutPage, Region

_LAYOUT_FILE = "layout.json"
_IMAGE_STEM = "page"

#: Dimensions de la page de démo (image **et** layout partagent ces côtes).
_DEMO_W = 520
_DEMO_H = 520
#: Fond parchemin clair (les boîtes SVG se lisent par-dessus).
_DEMO_RGB = (245, 243, 238)


def demo_layout() -> CanonicalLayout:
    """Layout de démonstration **déterministe** : une page, 3 régions étiquetées."""
    regions = (
        Region(
            id="r1", region_type="title",
            geometry=Geometry(bbox=BBox(x=40, y=30, width=440, height=70)),
        ),
        Region(
            id="r2", region_type="paragraph",
            geometry=Geometry(bbox=BBox(x=40, y=130, width=210, height=350)),
        ),
        Region(
            id="r3", region_type="figure",
            geometry=Geometry(bbox=BBox(x=270, y=130, width=210, height=350)),
        ),
    )
    return CanonicalLayout(
        pages=(
            LayoutPage(
                width=_DEMO_W, height=_DEMO_H, regions=regions,
                reading_order=("r1", "r2", "r3"),
            ),
        )
    )


def demo_page_image() -> bytes:
    """Image PNG **déterministe** de la page de démo (fond parchemin uni).

    Donne un fond raster à l'``<image>`` du SVG et **exerce** réellement la
    persistance + l'endpoint image (≠ infra dormante). Encodée à la main via la
    stdlib (``zlib``/``struct``) — pas de PIL en couche 6 ; mêmes octets à chaque
    appel (invariant §12 : déterminisme).
    """

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", _DEMO_W, _DEMO_H, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = b"\x00" + bytes(_DEMO_RGB) * _DEMO_W  # filtre 0 (None) + pixels
    idat = zlib.compress(row * _DEMO_H, 9)
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"IDAT", idat),
            _chunk(b"IEND", b""),
        )
    )


class SegmentationStore:
    """Registre disque des layouts de segmentation (id → dossier sous ``base_dir``)."""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir
        self._lock = threading.Lock()

    def save(
        self,
        layout: CanonicalLayout,
        *,
        image_ext: str | None = None,
        image_bytes: bytes | None = None,
    ) -> str:
        """Persiste un layout (+ image source optionnelle) ; renvoie son id."""
        seg_id = uuid.uuid4().hex
        with self._lock:
            folder = self._base / seg_id
            folder.mkdir(parents=True, exist_ok=True)
            (folder / _LAYOUT_FILE).write_text(
                layout.model_dump_json(), encoding="utf-8"
            )
            if image_bytes is not None and image_ext:
                (folder / f"{_IMAGE_STEM}{image_ext}").write_bytes(image_bytes)
        return seg_id

    def get_layout(self, seg_id: str) -> CanonicalLayout | None:
        """Relit le ``CanonicalLayout`` persisté, ou ``None`` (absent/invalide)."""
        folder = self._folder(seg_id)
        if folder is None:
            return None
        path = folder / _LAYOUT_FILE
        if not path.exists():
            return None
        return CanonicalLayout.model_validate_json(path.read_text(encoding="utf-8"))

    def latest(self) -> str | None:
        """Id du layout le plus récemment écrit (mtime), ou ``None`` si vide.

        Consommé par ``/segmentation`` : un **run réel** persisté par le sink est
        plus récent que la graine de démo → il s'affiche automatiquement. (Un
        sélecteur multi-runs est une amélioration ultérieure.)
        """
        if not self._base.is_dir():
            return None
        folders = [
            child
            for child in self._base.iterdir()
            if child.is_dir() and (child / _LAYOUT_FILE).is_file()
        ]
        if not folders:
            return None
        return max(folders, key=lambda child: child.stat().st_mtime).name

    def image_path(self, seg_id: str) -> Path | None:
        """Chemin de l'image source persistée (``None`` si aucune)."""
        folder = self._folder(seg_id)
        if folder is None:
            return None
        for path in sorted(folder.glob(f"{_IMAGE_STEM}.*")):
            return path
        return None

    def _folder(self, seg_id: str) -> Path | None:
        """Dossier du layout, **chemin validé** (anti path-traversal sur l'id URL)."""
        try:
            return validated_path(seg_id, self._base)
        except PathSecurityError:
            return None


__all__ = ["SegmentationStore", "demo_layout", "demo_page_image"]
