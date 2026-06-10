"""Module de pipeline **tiers**, réellement empaqueté et pip-installable.

Un segmenteur ``IMAGE → LAYOUT`` qui n'importe que les types de contrat publics
de XerOCR — exactement ce qu'écrirait un tiers branchant un YOLO. Découvert via
l'entry-point ``xerocr.modules`` déclaré dans ``pyproject.toml``, sans forker.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.layout import CanonicalLayout, LayoutPage, Region
from xerocr.pipeline.types import StepOutput


class PkgSegmenter:
    """Segmenteur tiers empaqueté : une région pleine page (stub déterministe)."""

    name = "sample_pkg_seg"
    version = "1.0-pkg"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.LAYOUT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, str | int | float | bool],
        context: object,
        control: object,
    ) -> StepOutput:
        workspace = getattr(context, "workspace_uri", None)
        document_id = getattr(context, "document_id", "doc")
        if workspace is None:
            raise AdapterStepError("sample_pkg_seg : workspace requis.")
        layout = CanonicalLayout(
            pages=(
                LayoutPage(
                    width=100,
                    height=100,
                    regions=(Region(id="r1", region_type="text"),),
                ),
            )
        )
        payload = layout.model_dump_json().encode("utf-8")
        out = Path(workspace) / f"{document_id}.sample_pkg_seg.json"
        out.write_bytes(payload)
        return StepOutput(
            artifacts={
                ArtifactType.LAYOUT: Artifact(
                    id=f"{document_id}:sample_pkg_seg:layout",
                    document_id=document_id,
                    type=ArtifactType.LAYOUT,
                    uri=str(out),
                    content_hash=compute_content_hash(payload),
                )
            }
        )


def build_sample_pkg_segmenter(kwargs: Mapping[str, object]) -> PkgSegmenter:
    """``ModuleBuilder`` pointé par l'entry-point ``xerocr.modules``."""
    return PkgSegmenter()
