"""``AltoLayoutSource`` — ``IMAGE → LAYOUT`` depuis un ALTO déjà là (couche 5).

Le banc sait produire une mise en page (segmenteurs) et sait en consommer une
(``to_text``, ``assembler``, métriques de structure). Il ne savait pas **en
lire une qui existe déjà** : un corpus patrimonial arrive presque toujours
accompagné de son ALTO, et rien ne permettait de le faire entrer autrement
qu'aplati en texte.

Convention de ``PrecomputedLayoutSource`` reprise telle quelle — l'ALTO est
cherché **à côté de l'image**, ``<stem>.xml`` près de ``<stem>.png``. C'est la
façon dont les corpus de ce dépôt sont rangés, et ça évite d'ajouter un type
d'entrée initial au planificateur.

Ce que la lecture conserve, et qui n'a de valeur que conservé : l'identifiant
de ligne (une identité, pas un rang), la géométrie, la confiance du moteur
d'origine, et la césure (``SUBS_TYPE``/``SUBS_CONTENT`` + la marque portée par
``<HYP>``). Un post-correcteur qui recolle un mot coupé a besoin des quatre.
"""

from __future__ import annotations

from pathlib import Path

from cinoc.adapters._workspace import workspace_artifact_path
from cinoc.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from cinoc.domain.errors import AdapterStepError, CinocError
from cinoc.formats.alto.layout_map import alto_to_layout
from cinoc.formats.alto.parser import parse_alto
from cinoc.pipeline.protocols import ParamValue
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"

#: Extensions tentées à côté de l'image, dans l'ordre.
_SUFFIXES = (".xml", ".alto.xml")


class AltoLayoutSource:
    """Lit l'ALTO voisin de l'image et le projette en ``CanonicalLayout``."""

    @property
    def name(self) -> str:
        return "alto_source"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.IMAGE})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.LAYOUT})

    def _locate(self, image_path: Path) -> Path:
        for suffix in _SUFFIXES:
            candidate = image_path.with_name(image_path.stem + suffix)
            if candidate.is_file():
                return candidate
        attendus = " ou ".join(repr(image_path.stem + s) for s in _SUFFIXES)
        raise AdapterStepError(
            f"{self.name} : aucun ALTO près de {image_path.name!r} "
            f"({attendus} attendu dans {image_path.parent})."
        )

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],  # noqa: ARG002 — contrat Module
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        control.raise_if_cancelled()
        image = inputs.get(ArtifactType.IMAGE)
        if image is None or image.uri is None:
            raise AdapterStepError(
                f"{self.name} : artefact IMAGE manquant ou sans URI."
            )
        alto_path = self._locate(Path(image.uri))
        try:
            layout = alto_to_layout(parse_alto(alto_path.read_bytes()))
        except CinocError as exc:
            raise AdapterStepError(
                f"{self.name} : {alto_path.name!r} illisible — {exc}"
            ) from exc

        # Une ligne sans ``id`` n'a pas d'identité stable, et un post-correcteur
        # qui reçoit un tel layout ne peut pas rendre ses décisions ligne à
        # ligne. On le dit ici plutôt que de laisser l'étape suivante échouer
        # sur une cause qui n'est pas la sienne.
        sans_id = sum(
            1
            for page in layout.pages
            for region in page.regions
            for line in region.lines
            if not line.id
        )
        if sans_id:
            raise AdapterStepError(
                f"{self.name} : {alto_path.name!r} porte {sans_id} ligne(s) "
                "sans attribut ID. Sans identifiant, une ligne n'a pas "
                "d'identité stable d'un artefact à l'autre."
            )

        payload = layout.model_dump_json().encode("utf-8")
        # Sans espace de travail, on écrit près de la source — même repli que
        # ``alto_assembler``.
        out = (
            workspace_artifact_path(
                context.workspace_uri, context.document_id, self.name, "layout.json"
            )
            if context.workspace_uri
            else alto_path.with_name(f"{alto_path.stem}.{self.name}.layout.json")
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
        return StepOutput(
            artifacts={
                ArtifactType.LAYOUT: Artifact(
                    id=f"{context.document_id}:{self.name}:layout",
                    document_id=context.document_id,
                    type=ArtifactType.LAYOUT,
                    uri=str(out),
                    content_hash=compute_content_hash(payload),
                )
            }
        )


__all__ = ["AltoLayoutSource"]
