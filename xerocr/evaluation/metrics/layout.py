"""Métriques de structure par bloc (couche 3) — ``region_cer`` + ``region_detection``.

- ``region_cer`` : texte **région par région** (apparié par ``id``), micro-agrégé
  page (Σ erreurs / Σ caractères).
- ``region_detection`` : qualité de la **segmentation géométrique** — F1 des
  régions appariées par **IoU de boîte** (≥ 0.5), en coordonnées **relatives à la
  page** (donc robuste aux unités : mm10 ALTO vs pixels). Pas de ``shapely`` :
  IoU de boîtes (boîte dérivée du polygone pour PAGE) ; l'IoU polygonal exact est
  un épaississement (aucun consommateur ne l'exige encore).

Convention métier (CLAUDE.md §3) : **niveau absent → métrique non applicable
(``None``)**. ``region_cer`` : pas de niveau texte → ``None``. ``region_detection`` :
aucune région géo-localisable côté référence → ``None``.
"""

from __future__ import annotations

from collections.abc import Iterator

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.layout import CanonicalLayout, Region
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric
from xerocr.evaluation.metrics.text import _edit_distance

_MISSING = ""

#: Seuil d'IoU standard pour qu'une région hypothèse compte comme détectée.
_IOU_THRESHOLD = 0.5

#: Boîte en coordonnées relatives ``(x0, y0, x1, y1)`` ∈ [0, 1].
_RelBox = tuple[float, float, float, float]


def _walk(regions: tuple[Region, ...]) -> list[Region]:
    """Aplati les régions imbriquées en parcours profondeur d'abord."""
    flat: list[Region] = []
    for region in regions:
        flat.append(region)
        flat.extend(_walk(region.regions))
    return flat


def _region_texts(layout: CanonicalLayout) -> dict[str, str]:
    """``{region_id: texte}`` (lignes jointes) sur toutes les pages."""
    texts: dict[str, str] = {}
    for page in layout.pages:
        for region in _walk(page.regions):
            texts[region.id] = "\n".join(line.text for line in region.lines)
    return texts


def _has_text_level(layout: CanonicalLayout) -> bool:
    """Vrai si au moins une région porte une ligne (≠ segmentation-seule)."""
    return any(
        region.lines
        for page in layout.pages
        for region in _walk(page.regions)
    )


def _layout_pair(ctx: DocContext) -> tuple[CanonicalLayout, CanonicalLayout]:
    if not isinstance(ctx.reference, CanonicalLayout) or not isinstance(
        ctx.hypothesis, CanonicalLayout
    ):
        raise EvaluationError(
            "métrique structure : reference et hypothesis doivent être des "
            "CanonicalLayout."
        )
    return ctx.reference, ctx.hypothesis


@document_metric(
    name="region_cer",
    input_types=(ArtifactType.LAYOUT, ArtifactType.LAYOUT),
    description="CER par région agrégé à la page (micro) sur le CanonicalLayout.",
    higher_is_better=False,
    tags=frozenset({"structure", "edit_distance", "layout"}),
)
def region_cer(ctx: DocContext) -> Observation | None:
    reference, hypothesis = _layout_pair(ctx)
    if not _has_text_level(hypothesis) or not _has_text_level(reference):
        return None
    ref_texts = _region_texts(reference)
    hyp_texts = _region_texts(hypothesis)
    total_edits = 0
    total_chars = 0
    for region_id, ref_text in ref_texts.items():
        hyp_text = hyp_texts.get(region_id, _MISSING)
        total_edits += _edit_distance(ref_text, hyp_text)
        total_chars += len(ref_text)
    if total_chars == 0:
        return None
    return Observation(value=total_edits / total_chars, weight=total_chars)


def _leaf_regions(regions: tuple[Region, ...]) -> Iterator[Region]:
    """Régions **atomiques** (sans sous-région) — la granularité segmentée."""
    for region in regions:
        if region.regions:
            yield from _leaf_regions(region.regions)
        else:
            yield region


def _abs_bbox(region: Region) -> tuple[int, int, int, int] | None:
    """Boîte absolue ``(x0, y0, x1, y1)`` depuis la bbox, sinon le polygone."""
    geometry = region.geometry
    if geometry is None:
        return None
    if geometry.bbox is not None:
        b = geometry.bbox
        return b.x, b.y, b.x + b.width, b.y + b.height
    if geometry.polygon:
        xs = [p[0] for p in geometry.polygon]
        ys = [p[1] for p in geometry.polygon]
        return min(xs), min(ys), max(xs), max(ys)
    return None


def _detection_boxes(layout: CanonicalLayout) -> list[_RelBox]:
    """Boîtes des régions atomiques, **relatives** à la page (unités neutralisées).

    Une page sans dimensions est ignorée (normalisation impossible).
    """
    boxes: list[_RelBox] = []
    for page in layout.pages:
        width, height = page.width, page.height
        if not width or not height:
            continue
        for region in _leaf_regions(page.regions):
            bbox = _abs_bbox(region)
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox
            boxes.append((x0 / width, y0 / height, x1 / width, y1 / height))
    return boxes


def _iou(a: _RelBox, b: _RelBox) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _true_positives(ref: list[_RelBox], hyp: list[_RelBox], threshold: float) -> int:
    """Appariement glouton déterministe : chaque réf prend sa meilleure hyp libre."""
    used: set[int] = set()
    matched = 0
    for ref_box in ref:
        best_iou, best_idx = threshold, -1
        for index, hyp_box in enumerate(hyp):
            if index in used:
                continue
            value = _iou(ref_box, hyp_box)
            if value >= best_iou:
                best_iou, best_idx = value, index
        if best_idx >= 0:
            used.add(best_idx)
            matched += 1
    return matched


@document_metric(
    name="region_detection",
    input_types=(ArtifactType.LAYOUT, ArtifactType.LAYOUT),
    description="F1 des régions appariées par IoU de boîte (≥0.5), coords relatives.",
    higher_is_better=True,
    tags=frozenset({"structure", "layout", "geometry", "detection"}),
)
def region_detection(ctx: DocContext) -> Observation | None:
    reference, hypothesis = _layout_pair(ctx)
    ref_boxes = _detection_boxes(reference)
    if not ref_boxes:
        return None  # rien de géo-localisable côté référence → non applicable
    hyp_boxes = _detection_boxes(hypothesis)
    tp = _true_positives(ref_boxes, hyp_boxes, _IOU_THRESHOLD)
    precision = tp / len(hyp_boxes) if hyp_boxes else 0.0
    recall = tp / len(ref_boxes)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return Observation(value=f1, weight=len(ref_boxes))


#: Socle de métriques de structure, collecté explicitement par le registre.
LAYOUT_METRICS: tuple[DocumentMetric, ...] = (region_cer, region_detection)

__all__ = ["LAYOUT_METRICS", "region_cer", "region_detection"]
