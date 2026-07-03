"""``BlockChainRecognizer`` — reconnaissance **par bloc** OCR puis LLM (couche 5).

Reconnaisseur composite pour le **fan-out** d'un pipeline hybride : sur le bloc
découpé (``IMAGE``), il enchaîne **deux** modules du socle —

1. un **recognizer** OCR (``IMAGE → RAW_TEXT``) : le texte brut du bloc ;
2. un **correcteur** LLM en rôle ``text_only`` (``RAW_TEXT → CORRECTED_TEXT``) :
   la post-correction du **seul** texte du bloc.

Le texte corrigé ressort **re-typé ``RAW_TEXT``** (le fan-out lit un ``RAW_TEXT``
par région) : l'ALTO assemblé porte donc, ligne par ligne, le texte **corrigé**,
**ancré à la géométrie du bloc** — aucun ré-alignement page↔correction n'est requis
(le texte corrigé ne quitte jamais son bloc). C'est « segmentation puis OCR **et**
LLM », impossible tant que l'hybride refusait un LLM séparé.

Un seul contrat (``Module``), implémenté directement : ce module **compose** deux
modules du registre, il n'emballe pas un second contrat (cf. CLAUDE.md §3).
"""

from __future__ import annotations

from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.errors import AdapterStepError
from cinoc.pipeline.protocols import Module, ParamValue
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"


class BlockChainRecognizer:
    """OCR par bloc puis correction LLM, ré-exposée en ``RAW_TEXT`` (fan-out)."""

    def __init__(self, *, label: str, recognizer: Module, corrector: Module) -> None:
        self._label = label
        self._recognizer = recognizer
        self._corrector = corrector
        # Contrats vérifiés à la construction (échoue tôt, pas au run) : le
        # recognizer lit une IMAGE et sort du RAW_TEXT ; le correcteur lit ce
        # RAW_TEXT et sort du CORRECTED_TEXT (rôle ``text_only``).
        if ArtifactType.IMAGE not in recognizer.input_types:
            raise AdapterStepError(
                f"{self.name} : le recognizer {recognizer.name!r} ne lit pas d'IMAGE."
            )
        if ArtifactType.RAW_TEXT not in recognizer.output_types:
            raise AdapterStepError(
                f"{self.name} : le recognizer {recognizer.name!r} ne produit "
                "pas de RAW_TEXT."
            )
        if ArtifactType.RAW_TEXT not in corrector.input_types:
            raise AdapterStepError(
                f"{self.name} : le correcteur {corrector.name!r} ne lit pas "
                "de RAW_TEXT."
            )
        if ArtifactType.CORRECTED_TEXT not in corrector.output_types:
            raise AdapterStepError(
                f"{self.name} : le correcteur {corrector.name!r} ne produit pas de "
                "CORRECTED_TEXT (rôle text_only attendu)."
            )

    @property
    def name(self) -> str:
        return f"block_chain:{self._label}"

    @property
    def version(self) -> str:
        # Reproductibilité : la version compose celles des deux sous-modules.
        return f"{_VERSION}+{self._recognizer.version}+{self._corrector.version}"

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.IMAGE})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.RAW_TEXT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        control.raise_if_cancelled()
        ocr_out = self._recognizer.execute(inputs, dict(params), context, control)
        raw = ocr_out.artifacts.get(ArtifactType.RAW_TEXT)
        if raw is None:
            raise AdapterStepError(
                f"{self.name} : OCR par bloc sans RAW_TEXT exploitable."
            )
        control.raise_if_cancelled()
        corr_out = self._corrector.execute(
            {ArtifactType.RAW_TEXT: raw}, dict(params), context, control
        )
        corrected = corr_out.artifacts.get(ArtifactType.CORRECTED_TEXT)
        if corrected is None:
            raise AdapterStepError(
                f"{self.name} : correcteur LLM sans CORRECTED_TEXT exploitable."
            )
        # Le fan-out lit un RAW_TEXT par région : on ré-expose le texte corrigé
        # (même contenu, même fichier) sous le type RAW_TEXT — pas d'écriture en
        # plus, le texte reste ancré au bloc.
        raw_out = corrected.model_copy(
            update={
                "id": f"{context.document_id}:{self.name}:raw_text",
                "type": ArtifactType.RAW_TEXT,
            }
        )
        usage = ocr_out.usage
        if corr_out.usage is not None:
            usage = (
                corr_out.usage
                if usage is None
                else usage.merged_with(corr_out.usage)
            )
        return StepOutput(artifacts={ArtifactType.RAW_TEXT: raw_out}, usage=usage)


__all__ = ["BlockChainRecognizer"]
