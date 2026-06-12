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


class PipelineConformity(BaseModel):
    """Scores de conformité HIPE d'un pipeline (vue ``hipe``).

    ``cmer``/``wmer`` micro = somme des comptes puis ratio ; macro = moyenne des
    scores par-document (``None``-exclus) — les deux conventions du scorer
    (SPEC_HIPE §4.1). ``delta_norm = cmer(raw) − cmer(hipe)`` : part d'erreur
    imputable à casse/ponctuation/formes mappées ; ``delta_heritage =
    cmer(heritage) − cmer(hipe)`` : part des seuls mappings patrimoniaux.
    ``n_missing`` = documents sans sortie scorée sur la vue ``hipe`` — exposé
    (jamais un silence) ; leur matérialisation « sortie vide = erreur max »
    (R-1.8) arrive avec le bilan de correction (les textes y sont disponibles).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    cmer_micro: float | None = None
    cmer_macro: float | None = None
    wmer_micro: float | None = None
    wmer_macro: float | None = None
    delta_norm: float | None = None
    delta_heritage: float | None = None
    n_missing: int = Field(default=0, ge=0)


class ConformityPayload(BaseModel):
    """Conformité HIPE d'un run : scores officiels + deltas de normalisation.

    Les noms exportés (``cmer_micro``…) suivent le scorer ; les vues sources
    sont nommées — chaque nombre a son profil (SPEC_HIPE §7.2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["hipe"] = "hipe"
    hipe_view: str = Field(min_length=1, max_length=128)
    raw_view: str | None = Field(default=None, max_length=128)
    heritage_view: str | None = Field(default=None, max_length=128)
    pipelines: tuple[PipelineConformity, ...] = ()


class RegressionSample(BaseModel):
    """Une régression de correction : le LLM a dégradé ce document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    cmer_raw: float = Field(ge=0, le=1)
    cmer_corrected: float = Field(ge=0, le=1)
    delta: float


class OverNormalizedWord(BaseModel):
    """Un mot juste à l'OCR, dégradé par le correcteur (``∅`` = supprimé)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    reference: str = Field(max_length=64)
    corrected: str = Field(max_length=64)


class PipelineCorrection(BaseModel):
    """Bilan de correction d'un pipeline 2 étages (brut → corrigé), une vue.

    Tous les nombres dérivent de ``cmer`` par document sur les paires
    (GT, brut) et (GT, corrigé) — mêmes textes préparés que le scoring.
    R-1.8 : un étage absent est **matérialisé vide** (erreur maximale) et
    compté (``n_missing_*``) — jamais une exclusion silencieuse. Les taux
    valent ``None`` quand leur dénominateur est nul (jamais un faux zéro).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    n_documents: int = Field(ge=1)
    n_missing_raw: int = Field(default=0, ge=0)
    n_missing_corrected: int = Field(default=0, ge=0)
    #: Triplet de non-régression (Σ = 1) + pref = improvement − regression.
    improvement_rate: float = Field(ge=0, le=1)
    regression_rate: float = Field(ge=0, le=1)
    no_change_rate: float = Field(ge=0, le=1)
    pref_score: float = Field(ge=-1, le=1)
    n_catastrophic: int = Field(default=0, ge=0)
    catastrophic_rate: float = Field(ge=0, le=1)
    #: pcis (SPEC §4.2) : non borné → macro accompagnée de la médiane robuste
    #: et du compte des valeurs extrêmes (|pcis| > 1).
    pcis_macro: float | None = None
    pcis_median: float | None = None
    n_pcis_extreme: int = Field(default=0, ge=0)
    #: Ampleur d'intervention (Koynov 2025) : CCR = MER(brut ↔ corrigé).
    ccr: float | None = None
    change_ratio: float | None = None
    length_ratio: float | None = None
    n_overedited: int = Field(default=0, ge=0)
    #: Volume de texte inséré vs GT (R-1.3) : I/(H+S+D+I) sur (GT, corrigé).
    char_ins_ratio: float | None = None
    n_hallucination_heavy: int = Field(default=0, ge=0)
    #: Absorption d'erreurs (multiset de mots GT) : flux corrigé vs introduit.
    errors_before: int = Field(default=0, ge=0)
    errors_after: int = Field(default=0, ge=0)
    corrected: int = Field(default=0, ge=0)
    introduced: int = Field(default=0, ge=0)
    kept_wrong: int = Field(default=0, ge=0)
    correction_rate: float | None = None
    introduction_rate: float | None = None
    net_improvement: int = 0
    corrected_samples: tuple[str, ...] = ()
    introduced_samples: tuple[str, ...] = ()
    #: Sur-normalisation (positionnelle) : mots OCR-justes dégradés.
    n_correct_ocr_words: int = Field(default=0, ge=0)
    n_over_normalized: int = Field(default=0, ge=0)
    over_normalization: float | None = None
    over_normalized_samples: tuple[OverNormalizedWord, ...] = ()
    #: Localité des modifications (R-2.6) : séquences d'éditions consécutives
    #: sur (GT, corrigé) — longues séquences = réécriture de passages.
    edit_run_median: float | None = None
    edit_run_max: int = Field(default=0, ge=0)
    edit_run_share: float | None = None
    worst_regressions: tuple[RegressionSample, ...] = ()


class CorrectionPayload(BaseModel):
    """Bilan de correction d'une vue : que vaut l'étage LLM des pipelines ?

    Présent seulement si la vue a scoré au moins un pipeline **2 étages**
    (un ``CORRECTED_TEXT`` produit) — un pipeline mono-étage n'a pas de
    « bilan de correction » (absence ≠ zéro muet). Les seuils sont portés
    par le payload : chaque drapeau est auditable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["correction"] = "correction"
    metric: str = Field(min_length=1, max_length=128)
    catastrophic_threshold: float = Field(gt=0)
    overedit_threshold: float = Field(gt=0)
    insertion_threshold: float = Field(gt=0)
    edit_run_threshold: int = Field(gt=0)
    pipelines: tuple[PipelineCorrection, ...] = ()


class CategoryBreakdown(BaseModel):
    """Restitution d'une catégorie de séquences (années, folios, montants…)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str = Field(min_length=1, max_length=32)
    n_total: int = Field(ge=1)
    n_strict: int = Field(ge=0)
    n_value: int = Field(ge=0)
    strict_score: float = Field(ge=0, le=1)
    value_score: float = Field(ge=0, le=1)
    #: Formes GT perdues (lentille *value*), échantillon borné.
    lost: tuple[str, ...] = ()


class PipelineStructuredData(BaseModel):
    """Séquences numériques restituées par un pipeline, par catégorie présente."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    #: Catégories **présentes dans la GT** seulement, ordre canonique.
    categories: tuple[CategoryBreakdown, ...] = ()


class StructuredDataPayload(BaseModel):
    """Données structurées d'une vue : la survie des dates/folios/montants.

    Absent si la GT du corpus ne porte aucune séquence (adaptatif — la
    famille ne pollue pas un corpus moderne sans signal).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["structured_data"] = "structured_data"
    pipelines: tuple[PipelineStructuredData, ...] = ()


class MarkerPreservation(BaseModel):
    """Préservation d'un signe (ou d'une catégorie) sur le corpus (micro).

    ``sign`` porte soit le signe abréviatif (familles containment/positional),
    soit le **nom de catégorie** (familles agrégées par catégorie : imprimé
    ancien, archives modernes — ex. ``typographic_punctuation``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sign: str = Field(min_length=1, max_length=32)
    n_total: int = Field(ge=1)
    n_strict: int = Field(ge=0)
    n_expansion: int = Field(ge=0)


class PipelinePhilology(BaseModel):
    """Préservation d'une famille de marqueurs par un pipeline (signes présents).

    ``n_strict`` = forme exacte reproduite ; ``n_expansion`` = forme **ou**
    développement (``≥ n_strict``, borne optimiste — un mot courant peut compter
    comme développement, capé au total GT).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: str = Field(min_length=1, max_length=128)
    family: str = Field(min_length=1, max_length=32)
    n_total: int = Field(ge=1)
    n_strict: int = Field(ge=0)
    n_expansion: int = Field(ge=0)
    markers: tuple[MarkerPreservation, ...] = ()


class PhilologyPayload(BaseModel):
    """Préservation des marqueurs philologiques d'une vue (diplomatique vs
    modernisant). Absent si la GT du corpus n'en porte aucun (adaptatif)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["philology"] = "philology"
    pipelines: tuple[PipelinePhilology, ...] = ()


#: Union des payloads, discriminée par ``kind`` — s'élargit d'un membre par
#: famille, dans le même commit que le calcul et le consommateur.
AnalysisPayload = Annotated[
    InferencePayload
    | EconomicsPayload
    | DiagnosticsPayload
    | CalibrationPayload
    | TaxonomyPayload
    | DocumentTextsPayload
    | ConformityPayload
    | CorrectionPayload
    | StructuredDataPayload
    | PhilologyPayload,
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
    "CategoryBreakdown",
    "CharConfusion",
    "ConformityPayload",
    "CorrectionPayload",
    "DiagnosticsPayload",
    "EconomicsPayload",
    "HardDocument",
    "InferencePayload",
    "MarginalCost",
    "MarkerPreservation",
    "OverNormalizedWord",
    "PairwiseDifference",
    "PhilologyPayload",
    "PipelineCalibration",
    "PipelineConformity",
    "PipelineConfusions",
    "PipelineCorrection",
    "PipelineEconomics",
    "PipelineInterval",
    "PipelinePhilology",
    "PipelineRank",
    "PipelineStructuredData",
    "PipelineTaxonomy",
    "RegressionSample",
    "StructuredDataPayload",
    "TaxonomyCount",
    "TaxonomyPayload",
    "WorstLine",
]
