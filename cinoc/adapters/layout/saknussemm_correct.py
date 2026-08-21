"""``SaknussemmCorrector`` — ``LAYOUT → LAYOUT + CORRECTED_TEXT`` (couche 5).

La post-correction du banc était **texte plat → texte plat** : on aplatissait
avant de corriger, donc l'identité de ligne, la géométrie et la césure étaient
détruites *avant* que le modèle voie quoi que ce soit. Cette étape corrige
**dans** la mise en page : chaque ligne garde son identifiant d'un bout à
l'autre, et l'appariement avant/après est **connu** au lieu d'être deviné.

Deux sorties, et c'est délibéré :

* ``LAYOUT`` — la mise en page corrigée, que ``alto_assembler`` sait rendre en
  ALTO et que les métriques de structure savent noter ;
* ``CORRECTED_TEXT`` — le même contenu aplati, **pour que le bilan de correction
  existant fonctionne sans être modifié**. Il cherche un ``RAW_TEXT`` et un
  ``CORRECTED_TEXT`` dans les sorties du pipeline ; les lui donner coûte une
  projection et évite d'inventer un type d'artefact dont personne n'a besoin.

Ce que la bibliothèque décide, l'étape le rapporte sans le retoucher : une ligne
refusée par une garde ressort **avec son texte d'origine**. C'est le principe de
`saknussemm` — l'application décide, le modèle informe — et le contredire ici
reviendrait à réintroduire en aval ce que les gardes ont écarté.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cinoc.adapters._workspace import workspace_artifact_path
from cinoc.adapters.layout.to_text import _page_text
from cinoc.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import CanonicalLayout, Line, Region
from cinoc.pipeline.protocols import ParamValue
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"

#: Producteurs câblés. ``rules`` ne demande rien (déterministe, hors ligne) ;
#: ``ollama`` parle à un serveur local, sans clé d'API. Les fournisseurs
#: distants s'ajouteront quand un run les demandera — pas avant.
_PRODUCERS = ("rules", "ollama")


def _require_saknussemm() -> Any:
    try:
        import saknussemm  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - dépend de l'installation
        raise AdapterStepError(
            "saknussemm_correct : la bibliothèque 'saknussemm' n'est pas "
            "installée — `pip install cinoc[saknussemm]`."
        ) from exc
    return saknussemm


class SaknussemmCorrector:
    """Corrige un ``CanonicalLayout`` ligne à ligne, identités préservées."""

    def __init__(
        self,
        *,
        label: str,
        producer: str = "rules",
        model: str = "",
        host: str = "http://localhost:11434",
    ) -> None:
        if producer not in _PRODUCERS:
            raise AdapterStepError(
                f"SaknussemmCorrector : producteur {producer!r} inconnu "
                f"(attendu : {', '.join(_PRODUCERS)})."
            )
        if producer == "ollama" and not model:
            raise AdapterStepError(
                "SaknussemmCorrector : le producteur 'ollama' exige un `model`."
            )
        self._label = label
        self._producer = producer
        self._model = model
        self._host = host

    @property
    def name(self) -> str:
        return f"saknussemm:{self._label}"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.LAYOUT})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.LAYOUT, ArtifactType.CORRECTED_TEXT})

    # -- producteur ---------------------------------------------------------

    def _build_producer(self) -> Any:
        if self._producer == "rules":
            from saknussemm.producers.rules import (  # type: ignore[import-not-found]  # noqa: PLC0415
                RulesProducer,
                default_french_ocr_rules,
            )

            return RulesProducer(default_french_ocr_rules())

        from saknussemm.producers.llm_edit import (  # type: ignore[import-not-found]  # noqa: PLC0415, E501
            LLMEditProducer,
        )

        from cinoc.adapters.llm.ollama_structured import (  # noqa: PLC0415
            OllamaStructuredClient,
        )

        return LLMEditProducer(
            OllamaStructuredClient(host=self._host), api_key="", model=self._model
        )

    # -- exécution ----------------------------------------------------------

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],  # noqa: ARG002 — contrat Module
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        control.raise_if_cancelled()
        artifact = inputs.get(ArtifactType.LAYOUT)
        if artifact is None or artifact.uri is None:
            raise AdapterStepError(f"{self.name} : artefact LAYOUT sans URI.")
        try:
            layout = CanonicalLayout.model_validate_json(
                Path(artifact.uri).read_bytes()
            )
        except (OSError, ValueError) as exc:
            raise AdapterStepError(
                f"{self.name} : {artifact.uri!r} n'est pas un CanonicalLayout "
                f"lisible — {exc}"
            ) from exc
        _require_saknussemm()

        from saknussemm.core.pipeline import (  # type: ignore[import-not-found]  # noqa: PLC0415, E501
            CorrectionPipeline,
        )

        from cinoc.adapters.layout._saknussemm_bridge import (  # noqa: PLC0415
            layout_to_manifest,
            manifest_page_ids,
        )

        manifest = layout_to_manifest(layout, document_id=context.document_id)
        control.raise_if_cancelled()

        class _Observer:
            def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
                pass

        pipeline = CorrectionPipeline(
            producer=self._build_producer(), observer=_Observer()
        )
        # ``source_files`` vide : on ne réécrit aucun XML. L'artefact de sortie
        # est la mise en page, et ``alto_assembler`` sait en faire un ALTO — le
        # moteur n'a donc rien à rendre lui-même.
        result = pipeline.run_sync(document_manifest=manifest, source_files={})

        decided = {
            (outcome.page_id, outcome.line_id): outcome.decision.final_text
            for outcome in result.report.lines
        }
        corrected = _apply(layout, decided, manifest_page_ids(manifest))
        return self._emit(corrected, context)

    def _emit(self, layout: CanonicalLayout, context: RunContext) -> StepOutput:
        payload = layout.model_dump_json().encode("utf-8")
        text = _flatten(layout).encode("utf-8")
        layout_path = self._out(context, "layout.json")
        text_path = self._out(context, "corrected.txt")
        layout_path.parent.mkdir(parents=True, exist_ok=True)
        layout_path.write_bytes(payload)
        text_path.write_bytes(text)
        return StepOutput(
            artifacts={
                ArtifactType.LAYOUT: Artifact(
                    id=f"{context.document_id}:{self.name}:layout",
                    document_id=context.document_id,
                    type=ArtifactType.LAYOUT,
                    uri=str(layout_path),
                    content_hash=compute_content_hash(payload),
                ),
                ArtifactType.CORRECTED_TEXT: Artifact(
                    id=f"{context.document_id}:{self.name}:text",
                    document_id=context.document_id,
                    type=ArtifactType.CORRECTED_TEXT,
                    uri=str(text_path),
                    content_hash=compute_content_hash(text),
                ),
            }
        )

    def _out(self, context: RunContext, suffix: str) -> Path:
        if context.workspace_uri:
            return workspace_artifact_path(
                context.workspace_uri, context.document_id, self._label, suffix
            )
        return Path(f"{context.document_id.replace('/', '_')}.{self._label}.{suffix}")


def _apply(
    layout: CanonicalLayout,
    decided: dict[tuple[str, str], str],
    page_ids: list[str],
) -> CanonicalLayout:
    """Repose les textes décidés sur la mise en page, identités à l'appui.

    Les mots sont **abandonnés sur une ligne modifiée** : leur géométrie décrit
    des caractères qui ne sont plus là. Les garder ferait dire à l'artefact une
    position que rien ne soutient — le contraire de ce que la structure sert à
    porter.
    """

    def region(reg: Region, page_id: str) -> Region:
        lines = []
        for line in reg.lines:
            texte = decided.get((page_id, line.id or ""))
            if texte is None or texte == line.text:
                lines.append(line)
                continue
            lines.append(
                Line(
                    id=line.id,
                    text=texte,
                    geometry=line.geometry,
                    baseline=line.baseline,
                    words=(),
                    confidence=line.confidence,
                )
            )
        return reg.model_copy(
            update={
                "lines": tuple(lines),
                "regions": tuple(region(r, page_id) for r in reg.regions),
            }
        )

    pages = tuple(
        page.model_copy(
            update={"regions": tuple(region(r, page_ids[i]) for r in page.regions)}
        )
        for i, page in enumerate(layout.pages)
    )
    return layout.model_copy(update={"pages": pages})


def _flatten(layout: CanonicalLayout) -> str:
    """Aplatit **avec la fonction de ``to_text``**, pas avec une copie.

    Le bilan de correction compare le ``RAW_TEXT`` produit par ``to_text`` au
    ``CORRECTED_TEXT`` produit ici : deux conventions d'aplatissement
    différentes fausseraient la comparaison sans rien casser de visible. Une
    première version réécrivait la boucle et ajoutait 41 lignes vides sur le
    corpus BnF — les régions sans texte — ce qui aurait décalé tout
    l'appariement de lignes.
    """
    return "\n".join(_page_text(page) for page in layout.pages)


__all__ = ["SaknussemmCorrector"]
