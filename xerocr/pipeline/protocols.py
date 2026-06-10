"""``Module`` — contrat unique d'une brique de pipeline exécutable.

Tout module (OCR, HTR, VLM, post-correcteur LLM, segmenteur, constructeur
d'ALTO…) implémente cette **même** forme, **directement** — un seul contrat
runtime, sans second contrat de module emballé par-dessus l'adapter (la dette
que la réécriture abandonne). C'est le **seul** point d'extension tierce du
produit (cf. CLAUDE.md §3).

Garanties (contrat runner ↔ module) :

- le runner garantit que ``inputs`` contient tous les types de ``input_types``,
  que ``params`` est une copie mutable, que ``context`` porte la ``Deadline`` et
  que ``control`` permet l'annulation coopérative ;
- le module garantit que ``StepOutput.artifacts`` contient tous ses
  ``output_types``, qu'aucune exception n'est avalée, et qu'il lève
  ``DeadlineExceeded`` à expiration de la deadline. ``StepOutput.usage`` est
  optionnel : seuls les modules qui consomment des jetons (LLM/VLM) le
  renseignent — la **durée** est mesurée par l'exécuteur, pas par le module.

``version`` (absent du contrat runtime hérité) alimente le ``RunManifest`` :
deux exécutions ne sont comparables qu'à version de module égale
(reproductibilité — CLAUDE.md §12).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

#: Valeur de paramètre admissible dans une spec (sérialisable YAML/JSON).
ParamValue = str | int | float | bool


@runtime_checkable
class Module(Protocol):
    """Brique de pipeline exécutable, typée par ses artefacts d'entrée/sortie."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def input_types(self) -> frozenset[ArtifactType]: ...

    @property
    def output_types(self) -> frozenset[ArtifactType]: ...

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput: ...


__all__ = ["Module", "ParamValue"]
