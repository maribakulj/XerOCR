"""Métriques de structure par bloc (couche 3) — socle : ``region_cer``.

Mesure le texte **région par région** sur le ``CanonicalLayout`` neutre, puis
**agrège à la page** (micro : Σ erreurs / Σ caractères de référence). Appariement
des régions par ``id`` (le squelette segmentation conserve les id de la GT ; le
recouvrement géométrique IoU est un épaississement).

Convention métier (CLAUDE.md §3) : **niveau absent → métrique non applicable
(``None``)**. Une hypothèse *segmentation-seule* (régions sans lignes) n'a pas de
niveau texte → ``region_cer`` renvoie ``None`` plutôt qu'un faux 1.0.
"""

from __future__ import annotations

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.layout import CanonicalLayout, Region
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric
from xerocr.evaluation.metrics.text import _edit_distance

_MISSING = ""


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


#: Socle de métriques de structure, collecté explicitement par le registre.
LAYOUT_METRICS: tuple[DocumentMetric, ...] = (region_cer,)

__all__ = ["LAYOUT_METRICS", "region_cer"]
