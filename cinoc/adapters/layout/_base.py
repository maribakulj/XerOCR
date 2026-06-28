"""Contrat **partagé** des segmenteurs de mise en page (couche 5).

Tout segmenteur (PP-DocLayout maison, segmenteur distant HF, futurs) produit la
même forme : un détecteur rend des **régions brutes** (``LayoutDetection``), qu'on
convertit en ``CanonicalLayout`` neutre (``to_canonical_layout``) puis qu'on
sérialise en artefact ``LAYOUT`` (``layout_step_output``, la *queue* d'``execute``).

Ces pièces sont **agnostiques du moteur** : elles vivaient dans ``pp_doclayout``
(le segmenteur maison), ce qui forçait le segmenteur distant à importer un module
PaddleX-spécifique pour les réutiliser. Extraites ici, les deux adapters en
dépendent sans se coupler l'un à l'autre.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cinoc.adapters._workspace import workspace_artifact_path
from cinoc.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import BBox, CanonicalLayout, Geometry, LayoutPage, Region
from cinoc.pipeline.types import RunContext, StepOutput


@dataclass(frozen=True)
class DetectedRegion:
    """Une région détectée : étiquette, boîte (pixels) et score de confiance."""

    label: str
    x: int
    y: int
    width: int
    height: int
    score: float


@dataclass(frozen=True)
class LayoutDetection:
    """Sortie brute d'un détecteur : dimensions de page + régions détectées."""

    page_width: int
    page_height: int
    regions: tuple[DetectedRegion, ...]


#: Détecteur **injectable** : chemin image → détection. Le défaut (PaddleX, appel
#: distant…) est résolu paresseusement à l'exécution ; les tests injectent un faux.
DetectorFn = Callable[[str], LayoutDetection]


def to_canonical_layout(
    detection: LayoutDetection, *, min_score: float
) -> CanonicalLayout:
    """Détections → ``CanonicalLayout`` (1 page, régions **sans lignes**).

    Filtre au seuil de score, **trie** par position (haut→bas puis gauche→droite)
    pour un ordre de lecture **déterministe** indépendant de l'ordre de détection,
    et numérote les régions ``r1..rN``. Le ``label`` du modèle devient le
    ``region_type`` neutre (``None`` si vide).
    """
    kept = [r for r in detection.regions if r.score >= min_score]
    ordered = sorted(kept, key=lambda r: (r.y, r.x))
    regions = tuple(
        Region(
            id=f"r{index + 1}",
            region_type=r.label or None,
            geometry=Geometry(
                bbox=BBox(x=r.x, y=r.y, width=r.width, height=r.height)
            ),
        )
        for index, r in enumerate(ordered)
    )
    page = LayoutPage(
        width=detection.page_width or None,
        height=detection.page_height or None,
        regions=regions,
        reading_order=tuple(region.id for region in regions),
    )
    return CanonicalLayout(pages=(page,))


def layout_step_output(
    layout: CanonicalLayout, context: RunContext, name: str
) -> StepOutput:
    """Sérialise un ``CanonicalLayout`` → artefact ``LAYOUT`` (tail d'``execute``
    partagé par tous les segmenteurs : PP-DocLayout, segmenteur distant…)."""
    if context.workspace_uri is None:
        raise AdapterStepError(f"{name} : workspace requis (RunContext.workspace_uri).")
    payload = layout.model_dump_json().encode("utf-8")
    output_path = workspace_artifact_path(
        context.workspace_uri, context.document_id, name, "layout.json"
    )
    output_path.write_bytes(payload)
    return StepOutput(
        artifacts={
            ArtifactType.LAYOUT: Artifact(
                id=f"{context.document_id}:{name}:layout",
                document_id=context.document_id,
                type=ArtifactType.LAYOUT,
                uri=str(output_path),
                content_hash=compute_content_hash(payload),
            )
        }
    )


__all__ = [
    "DetectedRegion",
    "DetectorFn",
    "LayoutDetection",
    "layout_step_output",
    "to_canonical_layout",
]
