"""Canal « analyses » du ``RunResult`` — résultats **non scalaires** (couche 3).

Contrat E2 (``PLAN_PARITE.md`` §1) : les scalaires ``MetricScore`` restent la
seule monnaie de classement/historique ; ``analyses`` porte le **contexte
structuré** (inférentiel, diagnostics…), calculé dans ``evaluation/`` et
seulement **lu** par les rapports. Chaque famille ajoute son payload Pydantic
figé ici, discriminé par ``kind``, dans le même commit que son calcul et son
consommateur (garde-fou « pas de consommateur = supprimé »).

Première famille : ``inference`` — le verdict statistique corrigé
multi-comparaisons (rangs moyens, distance critique de Nemenyi, groupes
d'ex-aequo, IC bootstrap par pipeline).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PipelineRank(BaseModel):
    """Rang moyen d'un pipeline sur les cas complets (petit = meilleur)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    mean_rank: float = Field(ge=1)


class PipelineInterval(BaseModel):
    """IC bootstrap (percentile, graine fixe) de la moyenne d'un pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    mean: float
    lower: float
    upper: float
    #: Nombre de documents valides du pipeline (marginal, ≠ cas complets).
    n_documents: int = Field(ge=1)


class PairwiseDifference(BaseModel):
    """Verdict Nemenyi d'une paire : écart de rangs vs distance critique."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    a: str = Field(min_length=1, max_length=128)
    b: str = Field(min_length=1, max_length=128)
    rank_gap: float = Field(ge=0)
    significant: bool


class InferencePayload(BaseModel):
    """Inférentiel d'une (vue × métrique) : rangs, Nemenyi, IC bootstrap.

    ``critical_distance``/``tied_groups``/``pairwise`` ne sont renseignés qu'à
    **k ≥ 3 pipelines** (le post-hoc corrige les comparaisons multiples après
    Friedman) ; à k = 2 le scalaire ``significance_p`` (Wilcoxon) reste le
    verdict, et seuls rangs + intervalles sont portés.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["inference"] = "inference"
    metric: str = Field(min_length=1, max_length=128)
    alpha: float = Field(gt=0, lt=1)
    #: Cas complets (documents où tous les pipelines ont une valeur).
    n_documents: int = Field(ge=0)
    critical_distance: float | None = Field(default=None, ge=0)
    q_alpha: float | None = Field(default=None, ge=0)
    #: Transparence : q_α extrapolé au-delà de la table (k > 50).
    q_alpha_extrapolated: bool = False
    #: Triés par (rang, pipeline) croissants — ordre déterministe.
    mean_ranks: tuple[PipelineRank, ...] = ()
    #: Groupes maximaux d'indiscernables (fenêtre ≤ CD sur les rangs triés).
    tied_groups: tuple[tuple[str, ...], ...] = ()
    #: Paires triées (a < b par nom).
    pairwise: tuple[PairwiseDifference, ...] = ()
    #: Triés par pipeline — ordre déterministe.
    intervals: tuple[PipelineInterval, ...] = ()


#: Union des payloads, discriminée par ``kind`` — s'élargit d'un membre par
#: famille (``Union[InferencePayload, …]`` + ``Field(discriminator="kind")``
#: dès le 2ᵉ membre).
AnalysisPayload = InferencePayload


class Analysis(BaseModel):
    """Une analyse adressée : portée + vue (+ pipeline/document si local)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scope: Literal["corpus", "pipeline", "document"]
    view: str = Field(min_length=1, max_length=128)
    pipeline: str | None = Field(default=None, max_length=128)
    document_id: str | None = Field(default=None, max_length=256)
    payload: AnalysisPayload


__all__ = [
    "Analysis",
    "AnalysisPayload",
    "InferencePayload",
    "PairwiseDifference",
    "PipelineInterval",
    "PipelineRank",
]
