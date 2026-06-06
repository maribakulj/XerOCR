"""Routeur **segmentation** (couche 8) : sert l'image source d'un layout.

``GET /api/segmentation/{id}/image`` restitue l'image de page persistée d'un run
de segmentation, que la vue ``/segmentation`` place en fond du SVG de régions
(``<image href>``). L'``id`` d'URL est **validé** (anti path-traversal) en amont
par ``SegmentationStore.image_path`` (chemin confiné sous la base via
``validated_path`` → ``None`` hors zone) ; introuvable ou hors zone → même ``404``
(pas de fuite). Pas d'upload ici : la persistance vient du pipeline (ou de la
graine de démo) — la prise reste **lecture seule**.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from xerocr.app.segmentation import SegmentationStore

#: Type MIME par extension d'image persistée (défaut binaire opaque).
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def build_segmentation_router(store: SegmentationStore) -> APIRouter:
    """Construit le routeur segmentation (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/api/segmentation/{seg_id}/image")
    def segmentation_image(seg_id: str) -> FileResponse:
        path = store.image_path(seg_id)  # id validé en amont → None hors zone
        if path is None:
            raise HTTPException(status_code=404, detail="image introuvable")
        media = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return FileResponse(path, media_type=media)

    return router


__all__ = ["build_segmentation_router"]
