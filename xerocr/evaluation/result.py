"""``RunResult`` — contrat de sortie **unique** d'un run (plein-scope, dégonflé).

Un seul format (pas de double représentation héritée). Dimensionné pour porter
toute métrique **scalaire** (texte/structure/NER/taxonomy…) et le détail
**par-document** dès sa conception, même quand seul un CER est écrit : ajouter
une métrique ou une vue est **additif**, jamais un changement d'enveloppe.
``schema_version`` couvre les évolutions structurelles ; les **clés** (``metric``,
``value``, ``support``, ``pipeline``, ``view``) sont un **contrat dur** avec le
rapport — renommer une clé est interdit (CLAUDE.md §12, déterminisme).

Contrat « analyses » (enveloppe, cf. ``PLAN_PARITE.md`` §1/E2) : les résultats
**non scalaires** (matrice de significativité, fronts de Pareto, paires de
confusion, bins de calibration…) entreront par un canal unique
``RunResult.analyses`` — payloads Pydantic figés, **union discriminée par nom**.
Règles dures : (1) les scalaires ``MetricScore`` restent la seule monnaie de
classement/historique ; (2) tout est calculé en ``evaluation/`` et écrit ici,
les rapports lisent sans recalculer ; (3) chaque payload naît **avec** son
calcul et son consommateur (même commit) — le champ lui-même n'est créé qu'avec
son premier payload (garde-fou « pas de consommateur = supprimé »).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from xerocr.domain.run import RunManifest
from xerocr.domain.usage import ResourceUsage


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


class DocumentUsage(BaseModel):
    """Ressources consommées par un pipeline sur un document (hors vues).

    L'exécution a lieu une fois par (pipeline × document) — les vues sont des
    lentilles d'évaluation, sans coût d'exécution propre. Les durées sont du
    wall-clock (mesure d'environnement, comme les horodatages du manifeste).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    pipeline: str = Field(min_length=1, max_length=128)
    usage: ResourceUsage


class RunResult(BaseModel):
    """Sortie complète d'un run : manifeste + agrégats + détail par-document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 2
    manifest: RunManifest
    pipelines: tuple[PipelineResult, ...] = Field(default_factory=tuple)
    documents: tuple[RunDocumentResult, ...] = Field(default_factory=tuple)
    #: Écrit par la passe inter-moteurs ; vide tant qu'un seul pipeline court.
    cross_engine: tuple[MetricScore, ...] = Field(default_factory=tuple)
    #: Ressources mesurées par (pipeline × document), triées (pipeline,
    #: document_id) — ordre déterministe. Vide pour un résultat reconstruit
    #: sans exécution (ex. chargement d'un JSON v1).
    usage: tuple[DocumentUsage, ...] = Field(default_factory=tuple)


__all__ = [
    "DocumentUsage",
    "MetricScore",
    "PipelineResult",
    "RunDocumentResult",
    "RunResult",
]
