"""``PipelineExecutor`` — exécute une ``PipelineSpec`` sur un document.

Mono-document, séquentiel : résout les entrées de chaque étape (DAG via
``inputs_from``, sinon dernière version par type), appelle ``Module.execute``,
puis **estampille la provenance** (``code_version`` + ``parameters_hash``) et le
``produced_by_step`` sur chaque artefact produit — le module n'a pas à connaître
ces concerns. L'annulation coopérative est vérifiée avant chaque étape.

Le fan-out par région (segmentation) et l'orchestration multi-documents
(threads, timeout, backpressure) sont des tranches ultérieures — pas ici.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import XerOCRError
from xerocr.domain.pipeline import INITIAL_STEP_ID, PipelineSpec, PipelineStep
from xerocr.domain.provenance import ProvenanceRecord
from xerocr.pipeline.protocols import Module
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


class PipelineStepError(XerOCRError):
    """Une étape n'a pas pu s'exécuter (module, entrée ou sortie manquante)."""


def _parameters_hash(params: Mapping[str, object]) -> str:
    payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return compute_content_hash(payload.encode("utf-8"))


class PipelineExecutor:
    """Exécute les pipelines déclaratives sur des artefacts initiaux."""

    def __init__(self, code_version: str) -> None:
        if not code_version:
            raise XerOCRError("PipelineExecutor : code_version vide.")
        self._code_version = code_version

    def execute_document(
        self,
        spec: PipelineSpec,
        modules: Mapping[str, Module],
        initial_inputs: Mapping[ArtifactType, Artifact],
        *,
        document_id: str,
        deadline: Deadline | None = None,
        control: RunControl | None = None,
    ) -> dict[ArtifactType, Artifact]:
        """Exécute ``spec`` ; renvoie le pool d'artefacts (dernier par type)."""
        ctrl = control if control is not None else RunControl()
        dl = deadline if deadline is not None else Deadline.infinite()
        pool: dict[ArtifactType, Artifact] = dict(initial_inputs)
        by_step: dict[str, dict[ArtifactType, Artifact]] = {}

        for step in spec.steps:
            ctrl.raise_if_cancelled()
            module = modules.get(step.adapter_name)
            if module is None:
                raise PipelineStepError(
                    f"étape {step.id!r} : module {step.adapter_name!r} "
                    "absent du registre."
                )
            inputs = self._resolve_inputs(step, pool, by_step)
            context = RunContext(
                document_id=document_id,
                code_version=self._code_version,
                pipeline_name=spec.name,
                deadline=dl,
            )
            outputs = module.execute(inputs, dict(step.params), context, ctrl)
            stamped = self._stamp(outputs, step)
            self._check_outputs(step, stamped)
            by_step[step.id] = stamped
            pool.update(stamped)
        return pool

    def _resolve_inputs(
        self,
        step: PipelineStep,
        pool: Mapping[ArtifactType, Artifact],
        by_step: Mapping[str, dict[ArtifactType, Artifact]],
    ) -> dict[ArtifactType, Artifact]:
        resolved: dict[ArtifactType, Artifact] = {}
        for t in step.input_types:
            src = step.inputs_from.get(t)
            if src is None or src == INITIAL_STEP_ID:
                art = pool.get(t)
            else:
                art = by_step.get(src, {}).get(t)
            if art is None:
                raise PipelineStepError(
                    f"étape {step.id!r} : entrée {t.value!r} introuvable."
                )
            resolved[t] = art
        return resolved

    def _stamp(
        self, outputs: Mapping[ArtifactType, Artifact], step: PipelineStep
    ) -> dict[ArtifactType, Artifact]:
        provenance = ProvenanceRecord(
            code_version=self._code_version,
            parameters_hash=_parameters_hash(dict(step.params)),
        )
        return {
            t: art.model_copy(
                update={"produced_by_step": step.id, "provenance": provenance}
            )
            for t, art in outputs.items()
        }

    def _check_outputs(
        self, step: PipelineStep, outputs: Mapping[ArtifactType, Artifact]
    ) -> None:
        for t in step.output_types:
            if t not in outputs:
                raise PipelineStepError(
                    f"étape {step.id!r} : sortie déclarée {t.value!r} "
                    "non produite."
                )


__all__ = ["PipelineExecutor", "PipelineStepError"]
