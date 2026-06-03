"""Plugin de référence (out-of-tree) : un **segmenteur tiers** minimal.

Démontre qu'un module de pipeline tiers — un YOLO de segmentation en vrai, ici un
stub déterministe — se branche via le **même** ``Module`` Protocol, découvert par
entry-point ``xerocr.modules``. Vit en fixture de test (= ce qu'un tiers
écrirait, hors de l'arbre livré).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.layout import BBox, CanonicalLayout, Geometry, LayoutPage, Region
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


def _band(region_id: str, y: int) -> Region:
    """Région-bande pleine largeur (segmentation stub déterministe)."""
    return Region(
        id=region_id,
        region_type="text",
        geometry=Geometry(bbox=BBox(x=0, y=y, width=100, height=50)),
    )


class SampleSegmenter:
    """Segmenteur tiers : ``IMAGE → LAYOUT`` (deux régions, sans lignes)."""

    name = "sample_seg"
    version = "9.9-demo"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.LAYOUT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> dict[ArtifactType, Artifact]:
        control.raise_if_cancelled()
        if inputs.get(ArtifactType.IMAGE) is None:
            raise AdapterStepError("sample_seg : artefact IMAGE requis.")
        if context.workspace_uri is None:
            raise AdapterStepError("sample_seg : workspace requis.")
        layout = CanonicalLayout(
            pages=(
                LayoutPage(
                    width=100,
                    height=100,
                    regions=(_band("r1", 0), _band("r2", 50)),
                    reading_order=("r1", "r2"),
                ),
            )
        )
        payload = layout.model_dump_json().encode("utf-8")
        out = Path(context.workspace_uri) / f"{context.document_id}.sample_seg.json"
        out.write_bytes(payload)
        return {
            ArtifactType.LAYOUT: Artifact(
                id=f"{context.document_id}:sample_seg:layout",
                document_id=context.document_id,
                type=ArtifactType.LAYOUT,
                uri=str(out),
                content_hash=compute_content_hash(payload),
            )
        }


def build_sample_segmenter(kwargs: Mapping[str, ParamValue]) -> SampleSegmenter:
    """``ModuleBuilder`` exposé par l'entry-point ``xerocr.modules``."""
    return SampleSegmenter()
