"""Importeur de corpus **IIIF** (Presentation API v2 & v3) — couche 5.

Rôle : **localiser** les pages d'un manifeste (parsing du schéma → URLs d'image).
La **matérialisation disque** (téléchargement → ``CorpusSpec``) vit en couche
``app`` (``app/corpus_import.py``) : un adapter parle protocole, pas filesystem.

Périmètre : **images seules**. Un manifeste IIIF porte des pages numérisées, pas
de transcription ; le corpus importé est donc sans vérité-terrain (OCR exécutable,
métriques non applicables tant qu'une GT n'est pas appariée). C'est un choix
assumé de la tranche, pas un manque.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xerocr.adapters.corpus._http import DEFAULT_TIMEOUT, HttpFetchError, fetch_json


@dataclass(frozen=True)
class IIIFImage:
    """Une page du manifeste : son URL d'image + un label lisible."""

    image_url: str
    label: str


def _extract_label(raw: object) -> str:
    """Aplati les formats de label IIIF (str, liste, map de langue v3)."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list) and raw:
        return _extract_label(raw[0])
    if isinstance(raw, dict):
        for lang in ("fr", "en", "none", "@value"):
            val = raw.get(lang)
            if val:
                return val[0] if isinstance(val, list) and val else str(val)
        for val in raw.values():
            return _extract_label(val)
    return str(raw) if raw else ""


def _service_image_url(service: object) -> str:
    """Construit ``{service}/full/max/0/default.jpg`` depuis un service Image API."""
    if isinstance(service, list):
        service = service[0] if service else {}
    if not isinstance(service, dict):
        return ""
    svc_id = service.get("@id") or service.get("id") or ""
    if not isinstance(svc_id, str) or not svc_id:
        return ""
    return f"{svc_id.rstrip('/')}/full/max/0/default.jpg"


def _image_url_v2(canvas: dict[str, Any]) -> str:
    images = canvas.get("images") or []
    if not images or not isinstance(images[0], dict):
        return ""
    resource = images[0].get("resource", {})
    if not isinstance(resource, dict):
        return ""
    direct = resource.get("@id", "")
    if isinstance(direct, str) and direct and not direct.endswith("/info.json"):
        return direct
    return _service_image_url(resource.get("service", {}))


def _image_url_v3(canvas: dict[str, Any]) -> str:
    for annotation_page in canvas.get("items") or []:
        for annotation in annotation_page.get("items") or []:
            body = annotation.get("body", {})
            if isinstance(body, list):
                body = body[0] if body else {}
            if not isinstance(body, dict):
                continue
            url = body.get("id") or body.get("@id") or ""
            if isinstance(url, str) and url and body.get("type") == "Image":
                return url
            service_url = _service_image_url(body.get("service", []))
            if service_url:
                return service_url
            if isinstance(url, str) and url:
                return url
    return ""


def _detect_version(manifest: dict[str, Any]) -> int:
    context = manifest.get("@context", "")
    contexts = context if isinstance(context, list) else [context]
    if any(isinstance(c, str) and "presentation/3" in c for c in contexts):
        return 3
    if manifest.get("type") == "Manifest" and "items" in manifest:
        return 3
    return 2


def parse_manifest(manifest: dict[str, Any]) -> tuple[IIIFImage, ...]:
    """Parse un manifeste IIIF (v2/v3 auto-détecté) → pages avec image. Pur."""
    if _detect_version(manifest) == 3:
        canvases = manifest.get("items") or []
        extract = _image_url_v3
    else:
        sequences = manifest.get("sequences") or []
        canvases = sequences[0].get("canvases", []) if sequences else []
        extract = _image_url_v2
    images: list[IIIFImage] = []
    for i, canvas in enumerate(canvases, start=1):
        if not isinstance(canvas, dict):
            continue
        url = extract(canvas)
        if not url:
            continue
        label = _extract_label(canvas.get("label", f"canvas_{i}")) or f"canvas_{i}"
        images.append(IIIFImage(image_url=url, label=label))
    return tuple(images)


class IIIFImporter:
    """Localise les pages d'un manifeste IIIF (fetch + parse, **sans disque**)."""

    name = "iiif"

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def fetch_images(self, manifest_url: str) -> tuple[IIIFImage, ...]:
        manifest = fetch_json(manifest_url, timeout=self._timeout)
        if not isinstance(manifest, dict):
            raise HttpFetchError(
                f"manifeste IIIF {manifest_url!r} : objet JSON attendu."
            )
        return parse_manifest(manifest)


__all__ = ["IIIFImage", "IIIFImporter", "parse_manifest"]
