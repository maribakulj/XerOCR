"""``RunResult`` — contrat de sortie **unique** d'un run (plein-scope, dégonflé).

Un seul format (pas de double représentation héritée). Dimensionné pour porter
toute métrique **scalaire** (texte/structure/NER/taxonomy…) et le détail
**par-document** dès sa conception, même si T1 n'écrit qu'un CER : ajouter une
métrique ou une vue est **additif**, jamais un changement d'enveloppe.
``schema_version`` couvre les évolutions structurelles ; les **clés** (``metric``,
``value``, ``support``, ``pipeline``, ``view``) sont un **contrat dur** avec le
rapport — renommer une clé est interdit (CLAUDE.md §12, déterminisme).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from xerocr.domain.run import RunManifest


class MetricScore(BaseModel):
    """Valeur d'une métrique (agrégat ou par-doc). ``None`` = non applicable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str = Field(min_length=1, max_length=128)
    value: float | None = None
    #: « Poids de preuve » de ``value`` : par-document = le **dénominateur** de la
    #: métrique (longueur de réf…), qui pondère le micro-agrégat ; en agrégat = le
    #: **nombre de documents** applicables. Deux lectures, même intention (taille).
    support: int | None = Field(default=None, ge=0)


class RunDocumentResult(BaseModel):
    """Scores d'un pipeline sur un document, sous une vue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    pipeline: str = Field(min_length=1, max_length=128)
    view: str = Field(min_length=1, max_length=128)
    scores: tuple[MetricScore, ...] = Field(default_factory=tuple)


class PipelineResult(BaseModel):
    """Agrégat d'un pipeline sous une vue (moyennes ``None``-exclues + support)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    view: str = Field(min_length=1, max_length=128)
    aggregate: tuple[MetricScore, ...] = Field(default_factory=tuple)


class RunResult(BaseModel):
    """Sortie complète d'un run : manifeste + agrégats + détail par-document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    manifest: RunManifest
    pipelines: tuple[PipelineResult, ...] = Field(default_factory=tuple)
    documents: tuple[RunDocumentResult, ...] = Field(default_factory=tuple)
    #: Écrit par la passe inter-moteurs (tranche T2) ; vide en T1.
    cross_engine: tuple[MetricScore, ...] = Field(default_factory=tuple)


__all__ = ["MetricScore", "PipelineResult", "RunDocumentResult", "RunResult"]
