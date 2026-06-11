"""Canal « analyses » du ``RunResult`` — résultats **non scalaires** (couche 3).

Contrat E2 (``PLAN_PARITE.md`` §1) : les scalaires ``MetricScore`` restent la
seule monnaie de classement/historique ; ``analyses`` porte le **contexte
structuré** (inférentiel, diagnostics…), calculé dans ``evaluation/`` et
seulement **lu** par les rapports. Chaque famille ajoute son payload Pydantic
figé ici, discriminé par ``kind``, dans le même commit que son calcul et son
consommateur (garde-fou « pas de consommateur = supprimé »).

Familles : ``inference`` (verdict statistique corrigé multi-comparaisons),
``economics`` (coûts, débit, Pareto), ``diagnostics`` (confusions, pires
lignes, documents difficiles), ``calibration`` (ECE/MCE), ``taxonomy``
(classes d'erreurs par règles pures — quelles erreurs, pas seulement combien).
"""

from __future__ import annotations

from typing import Annotated, Literal

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


class PipelineEconomics(BaseModel):
    """Ressources et coût estimé d'un pipeline sur le run (par vue : CER joint).

    ``cost_eur`` est **indicatif** : temps machine (durée mesurée × taux
    horaire) + jetons cloud au tarif de la table ; ``None`` si un étage cloud
    a un modèle absent de la table (jamais un zéro silencieux — ``basis`` le
    dit). Tous les nombres sont des fonctions auditables des mesures E1.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    n_documents: int = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    cost_eur: float | None = Field(default=None, ge=0)
    #: « machine » · « machine+jetons » · « tarif inconnu : <kind:model> ».
    basis: str = Field(min_length=1, max_length=256)
    cer: float | None = None
    #: Erreurs estimées sur la vue : Σ (cer_doc × poids_doc) — auditable.
    estimated_errors: float | None = Field(default=None, ge=0)
    pages_per_hour: float | None = Field(default=None, ge=0)
    #: Débit corrigé du temps de correction des erreurs résiduelles.
    pages_per_hour_effective: float | None = Field(default=None, ge=0)


class MarginalCost(BaseModel):
    """Coût marginal d'un pipeline vs le moins cher : € par erreur évitée."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    baseline: str = Field(min_length=1, max_length=128)
    cost_delta_eur: float
    errors_avoided: float
    #: ``None`` si le surcoût n'évite aucune erreur (dominé).
    eur_per_avoided_error: float | None = Field(default=None, ge=0)


class EconomicsPayload(BaseModel):
    """Économie d'un run sous une vue : coûts, débits, fronts de Pareto.

    La péremption de la table de tarifs est évaluée contre ``completed_at``
    du manifeste (déterministe — pas d'horloge au rendu).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["economics"] = "economics"
    #: Axe qualité des fronts de Pareto (la métrique phare de la vue).
    metric: str = Field(min_length=1, max_length=128)
    currency: str = Field(min_length=1, max_length=8)
    hourly_rate_eur: float = Field(ge=0)
    time_per_error_seconds: float = Field(ge=0)
    pricing_valid_until: str = Field(min_length=1, max_length=32)
    pricing_stale: bool
    pipelines: tuple[PipelineEconomics, ...] = ()
    #: Non-dominés sur (métrique, coût) puis (métrique, durée) — tri stable.
    pareto_cost: tuple[str, ...] = ()
    pareto_speed: tuple[str, ...] = ()
    marginal: tuple[MarginalCost, ...] = ()


class CharConfusion(BaseModel):
    """Substitution récurrente : caractère attendu → caractère produit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expected: str = Field(min_length=1, max_length=8)
    observed: str = Field(min_length=1, max_length=8)
    count: int = Field(ge=1)


class PipelineConfusions(BaseModel):
    """Top des confusions d'un pipeline sur le corpus (tri : -count, paire)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    pairs: tuple[CharConfusion, ...] = ()


class WorstLine(BaseModel):
    """Une des pires lignes du corpus : où ça casse, texte à l'appui.

    Les extraits sont **verbatim** (tronqués) des représentations normalisées
    déjà chargées pour le scoring — aucun re-calcul au rendu.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=256)
    line_index: int = Field(ge=0)
    cer: float = Field(ge=0)
    reference: str = Field(max_length=160)
    hypothesis: str = Field(max_length=160)


class HardDocument(BaseModel):
    """Document le plus difficile : CER moyen sur les pipelines scorés."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    mean_cer: float = Field(ge=0)
    n_pipelines: int = Field(ge=1)


class DiagnosticsPayload(BaseModel):
    """Diagnostic d'erreurs d'une vue : confusions, pires lignes, difficulté."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["diagnostics"] = "diagnostics"
    metric: str = Field(min_length=1, max_length=128)
    confusions: tuple[PipelineConfusions, ...] = ()
    worst_lines: tuple[WorstLine, ...] = ()
    hardest_documents: tuple[HardDocument, ...] = ()


class CalibrationBin(BaseModel):
    """Bin de fiabilité : confiance moyenne vs exactitude observée."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lower: float = Field(ge=0, le=1)
    upper: float = Field(ge=0, le=1)
    mean_confidence: float = Field(ge=0, le=1)
    accuracy: float = Field(ge=0, le=1)
    count: int = Field(ge=1)


class PipelineCalibration(BaseModel):
    """Calibration des confidences d'un pipeline sur le corpus.

    ECE = Σ (n_b/N)·|acc_b − conf_b| ; MCE = max |acc_b − conf_b| sur les bins
    non vides. « Correct » = le mot du jeton apparaît (multi-ensemble, exact)
    dans la référence du document — proxy auditable, documenté.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    n_tokens: int = Field(ge=1)
    ece: float = Field(ge=0, le=1)
    mce: float = Field(ge=0, le=1)
    bins: tuple[CalibrationBin, ...] = ()


class CalibrationPayload(BaseModel):
    """Fiabilité des auto-estimations moteur, par pipeline (vue texte)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["calibration"] = "calibration"
    n_bins: int = Field(ge=2)
    pipelines: tuple[PipelineCalibration, ...] = ()


class TaxonomyCount(BaseModel):
    """Occurrences d'une classe d'erreur."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=64)
    count: int = Field(ge=1)


class PipelineTaxonomy(BaseModel):
    """Répartition des classes d'erreurs d'un pipeline sur le corpus."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    total_errors: int = Field(ge=1)
    #: Classes présentes seulement, dans l'ordre canonique de ``CLASSES``.
    counts: tuple[TaxonomyCount, ...] = ()


class TaxonomyPayload(BaseModel):
    """Taxonomie d'erreurs d'une vue (classification par règles pures)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["taxonomy"] = "taxonomy"
    #: Ordre canonique de rendu (vocabulaire fermé, cf. ``evaluation.taxonomy``).
    classes: tuple[str, ...] = ()
    pipelines: tuple[PipelineTaxonomy, ...] = ()


#: Plafond de caractères des textes embarqués (borne le payload ; au-delà, tronqué).
_MAX_TEXT_CHARS = 8000


class DocumentTexts(BaseModel):
    """Textes complets d'**un** document (vérité-terrain + sortie par moteur).

    Bornés : seuls les **top-N pires documents** sont embarqués, chaque texte
    tronqué à ``_MAX_TEXT_CHARS``. Normalisés (mêmes représentations que le
    scoring) → le diff pleine page reflète ce qui est mesuré.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    reference: str = Field(max_length=_MAX_TEXT_CHARS)
    #: ``(pipeline, hypothèse)`` ordonnés — pour le sélecteur de moteur du diff.
    hypotheses: tuple[tuple[str, str], ...] = ()


class DocumentTextsPayload(BaseModel):
    """Textes complets des pires documents d'une vue (diff pleine page, borné)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["document_texts"] = "document_texts"
    documents: tuple[DocumentTexts, ...] = ()


#: Union des payloads, discriminée par ``kind`` — s'élargit d'un membre par
#: famille, dans le même commit que le calcul et le consommateur.
AnalysisPayload = Annotated[
    InferencePayload
    | EconomicsPayload
    | DiagnosticsPayload
    | CalibrationPayload
    | TaxonomyPayload
    | DocumentTextsPayload,
    Field(discriminator="kind"),
]


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
    "CalibrationBin",
    "CalibrationPayload",
    "CharConfusion",
    "DiagnosticsPayload",
    "EconomicsPayload",
    "HardDocument",
    "InferencePayload",
    "MarginalCost",
    "PairwiseDifference",
    "PipelineCalibration",
    "PipelineConfusions",
    "PipelineEconomics",
    "PipelineInterval",
    "PipelineRank",
    "PipelineTaxonomy",
    "TaxonomyCount",
    "TaxonomyPayload",
    "WorstLine",
]
