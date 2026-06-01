"""``RunSpec`` — description déclarative complète d'un run.

Compose les types déclaratifs du domaine (corpus + pipelines + vues) en **une**
entrée auto-suffisante : un run est entièrement décrit par son ``RunSpec`` (+ le
``code_version``). **Pas de ``StepSpec`` distinct** — ``PipelineStep`` (déjà en
domain) est l'étape déclarative ; en introduire un second serait une 2ᵉ
représentation de pipeline (la dette qu'on abandonne, cf. journal D-010).

``adapter_kwargs`` (``adapter_name → kwargs de construction``) alimente la
factory de modules **et** le ``RunManifest`` (reproductibilité).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.evaluation import EvaluationSpec
from xerocr.domain.pipeline import PipelineSpec


class RunSpec(BaseModel):
    """Ce qu'il faut exécuter : corpus, pipelines candidats, vues d'évaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    corpus: CorpusSpec
    pipelines: tuple[PipelineSpec, ...] = Field(min_length=1)
    evaluation: EvaluationSpec
    adapter_kwargs: dict[str, dict[str, str | int | float | bool]] = Field(
        default_factory=dict
    )
    run_id: str | None = Field(default=None, max_length=256)
    metadata: dict[str, str] = Field(default_factory=dict)


__all__ = ["RunSpec"]
