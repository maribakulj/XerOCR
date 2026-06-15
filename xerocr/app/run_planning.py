"""Planification d'un run : (concurrents, corpus) → ``RunSpec`` (couche 6).

Construire une spec d'exécution est de l'**orchestration**, pas du transport :
les routeurs (couche 8) délèguent ici et ne fabriquent **aucun** ``RunSpec``
eux-mêmes. Le dispatch est **exhaustif** — un moteur/mode non câblé est refusé
explicitement (``RunPlanningError``), jamais redirigé en silence vers un autre
moteur (anti-régression du défaut « ``mistral`` → tesseract »).

Un **benchmark** compare N **concurrents** sur le **même corpus**, en **un seul
run** : ``plan_benchmark_run`` assemble N ``PipelineSpec`` dans **un**
``RunSpec`` (l'orchestrateur les exécute toutes et calcule le cross-engine). Un
concurrent porte un **mode** :

- ``None``           — OCR seul (ex. tesseract) → ``RAW_TEXT`` ;
- ``text_only``      — OCR → LLM (post-correction texte) → ``CORRECTED_TEXT`` ;
- ``text_and_image`` — OCR → VLM (image + texte) → ``CORRECTED_TEXT`` ;
- ``zero_shot``      — VLM seul (image → texte), sans OCR amont → ``RAW_TEXT``.

La segmentation (``IMAGE → LAYOUT``, sans score texte) reste un run **à part**
(``plan_segmentation_run``), pas un concurrent de benchmark.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from xerocr.app.engines import EngineStatus
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.errors import XerOCRError
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import (
    INITIAL_STEP_ID,
    PipelineMode,
    PipelineSpec,
    PipelineStep,
)
from xerocr.domain.projection import ProjectionSpec
from xerocr.domain.run_spec import RunSpec
from xerocr.evaluation.archaic import resolve_archaic_list
from xerocr.formats.text import NORMALIZATION_PROFILES
from xerocr.prompts import PromptError, load_prompt

#: Segmenteur de mise en page du socle — **source unique** du *kind* (consommé
#: par la planification du run de segmentation ET par le gate du routeur).
SEGMENTER_KIND = "pp_doclayout"

#: Moteurs OCR câblés pour un run réel (amont d'une chaîne ou OCR seul).
_OCR_ENGINES = frozenset(
    {
        "tesseract", "kraken", "pero", "calamari",
        "mistral_ocr", "google_vision", "azure_di",
    }
)
#: Fournisseurs de post-correction LLM (mode ``text_only``).
_LLM_ENGINES = frozenset({"openai", "anthropic", "mistral", "ollama"})
#: Fournisseurs **vision** (modes ``text_and_image`` et ``zero_shot``).
_VLM_ENGINES = frozenset({"openai", "anthropic", "mistral"})


class RunPlanningError(XerOCRError):
    """Moteur/mode non câblé pour un run, ou incohérence concurrent⇄corpus."""


class Competitor(BaseModel):
    """Un concurrent de benchmark = un pipeline à exécuter (couche 6).

    ``engine`` est le moteur OCR (modes ``None``/``text_*``) **ou** le
    fournisseur VLM (mode ``zero_shot``). ``llm`` nomme le fournisseur de
    post-correction des modes ``text_*``. Validé exhaustivement à la
    planification (jamais de retombée muette).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    engine: str = Field(min_length=1, max_length=64)
    mode: PipelineMode | None = None
    llm: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    lang: str = Field(default="fra", max_length=64)
    #: Prompt de post-correction/transcription (modes LLM/VLM). ``None`` → prompt
    #: par défaut du rôle (``default_prompt_for_role``). Exposé à l'UI (texte libre).
    prompt: str | None = Field(default=None, max_length=8000)
    #: Nom d'un **prompt curé** (``xerocr.prompts``) à utiliser à la place du défaut.
    #: Mutuellement exclusif avec ``prompt`` (libre). Résolu au plan en son texte.
    prompt_name: str | None = Field(default=None, max_length=128)


#: Types de candidat scorés par toute vue benchmark : ``RAW_TEXT`` (OCR/zero-shot)
#: **et** ``CORRECTED_TEXT`` (OCR→LLM) — la précédence du runner évalue la sortie
#: la plus aboutie de chaque pipeline (cf. evaluation).
_CANDIDATES = frozenset({ArtifactType.RAW_TEXT, ArtifactType.CORRECTED_TEXT})

#: **Profils de métriques** : bundles curés de colonnes scalaires pour la vue
#: ``text`` (classement par défaut du rapport). Chaque nom ne référence que des
#: métriques **enregistrées** pour la signature ``(RAW_TEXT, RAW_TEXT)`` — un nom
#: non enregistré ferait lever le runner (couche 3 ; verrouillé par test). Changer
#: de profil n'allège **que** les colonnes de classement : les *collecteurs*
#: (taxonomy, structured_data, NER…) restent indépendants de ``metric_names``, la
#: donnée n'est jamais perdue. ``standard`` est le défaut **historique**
#: (byte-identique à l'ancienne vue par défaut).
DEFAULT_METRIC_PROFILE = "standard"
METRIC_PROFILES: dict[str, tuple[str, ...]] = {
    "standard": ("cer", "wer", "mer", "searchability", "hallucination", "air"),
    "essentiel": ("cer", "wer", "mer"),
    "philologie": ("cer", "cer_diplo", "mer", "diacritic_err", "mufi_err", "air"),
}


def _ocr_view(
    normalization: str | None,
    char_exclude: str | None,
    *,
    with_hcpr: bool = False,
    base_metrics: tuple[str, ...] = METRIC_PROFILES[DEFAULT_METRIC_PROFILE],
) -> EvaluationView:
    # ``base_metrics`` vient du **profil de métriques** choisi (défaut
    # ``standard``). ``air`` (apport net d'archaïsmes) y est d'office (Q4) ;
    # ``hcpr`` (préservation) n'est **ajouté** que sur une liste **explicitement**
    # configurée — sinon il doublonnerait ``mufi_err`` sur tout corpus médiéval.
    # ``numseq_strict``/``numseq_value`` restent **hors** des profils (D-130) :
    # adaptatifs (``None`` sans séquences) → colonnes vides « — » sur tout corpus
    # sans dates/folios/montants. Ils restent **enregistrés** (utilisables par une
    # vue custom qui voudrait classer dessus), et la **section `structured_data`
    # reste affichée** quand des séquences existent (le collecteur l'observe
    # indépendamment de ``metric_names``) — la donnée n'est pas perdue, seul le
    # classement scalaire par défaut s'allège.
    metric_names = base_metrics
    if with_hcpr:
        metric_names = (*metric_names, "hcpr")
    return EvaluationView(
        name="text",
        candidate_types=_CANDIDATES,
        metric_names=metric_names,
        normalization_profile=normalization,
        char_exclude=char_exclude,
    )


def _reference_view(
    normalization: str | None, char_exclude: str | None
) -> EvaluationView:
    """Vue **référence OCR** (opt-in) : compare le candidat à une référence
    ``REFERENCE_TEXT`` (ex. OCR Gallica) via une projection identité. Le **nom de
    la vue porte l'avertissement** : ce n'est PAS une vérité-terrain manuelle, le
    score mesure l'accord avec un autre OCR."""
    return EvaluationView(
        name="référence OCR (pas une vérité-terrain manuelle)",
        candidate_types=_CANDIDATES,
        projections_by_source_type={
            ArtifactType.REFERENCE_TEXT: ProjectionSpec(
                source_type=ArtifactType.REFERENCE_TEXT,
                target_type=ArtifactType.RAW_TEXT,
                projector_name="identity_text",
            )
        },
        metric_names=("cer", "wer", "mer"),
        ignored_dimensions=("exactitude (la référence est elle-même un OCR)",),
        normalization_profile=normalization,
        char_exclude=char_exclude,
    )


def _views_for_corpus(
    corpus: CorpusSpec,
    normalization: str | None = None,
    char_exclude: str | None = None,
    *,
    with_hcpr: bool = False,
    base_metrics: tuple[str, ...] = METRIC_PROFILES[DEFAULT_METRIC_PROFILE],
) -> tuple[EvaluationView, ...]:
    """Vues à évaluer selon les **types de GT présents**, sous ``normalization``.

    GT manuelle ``RAW_TEXT`` → vue ``text`` ; référence ``REFERENCE_TEXT`` (OCR
    Gallica) → vue *référence* distincte. Un corpus sans GT → vue ``text`` par
    défaut (le run reste exécutable, simplement non scoré). ``char_exclude``
    filtre des caractères des deux côtés (GT/hyp) avant le calcul (runner couche 3).
    ``with_hcpr`` ajoute la colonne ``hcpr`` à la vue ``text`` (liste archaïque
    configurée). ``base_metrics`` = colonnes scalaires du **profil de métriques**
    choisi (n'affecte que la vue ``text``, pas la vue *référence* fixe).
    """
    gt_types = {gt.type for doc in corpus.documents for gt in doc.ground_truths}
    views: list[EvaluationView] = []
    if ArtifactType.RAW_TEXT in gt_types:
        views.append(
            _ocr_view(
                normalization, char_exclude,
                with_hcpr=with_hcpr, base_metrics=base_metrics,
            )
        )
    if ArtifactType.REFERENCE_TEXT in gt_types:
        views.append(_reference_view(normalization, char_exclude))
    if not views:
        views.append(
            _ocr_view(
                normalization, char_exclude,
                with_hcpr=with_hcpr, base_metrics=base_metrics,
            )
        )
    return tuple(views)


def _resolve_metric_profile(name: str | None) -> tuple[str, ...]:
    """Colonnes scalaires d'un profil nommé (défaut : ``standard``).

    Un nom inconnu → ``RunPlanningError`` (jamais un défaut muet ; le routeur le
    remonte en 422), comme pour un profil de normalisation inconnu.
    """
    if name is None:
        return METRIC_PROFILES[DEFAULT_METRIC_PROFILE]
    try:
        return METRIC_PROFILES[name]
    except KeyError:
        raise RunPlanningError(
            f"profil de métriques inconnu : {name!r}."
        ) from None


def _resolve_prompt(comp: Competitor) -> str | None:
    """Texte du prompt : libre (prioritaire) > curé (par nom) > défaut du rôle.

    ``prompt`` (texte libre saisi) et ``prompt_name`` (prompt curé) sont
    **mutuellement exclusifs** : les fournir tous deux est une erreur de plan
    (jamais un choix silencieux). Un nom curé inconnu → ``RunPlanningError`` (422).
    """
    if comp.prompt and comp.prompt_name:
        raise RunPlanningError(
            "prompt : choisir un prompt libre OU un prompt curé, pas les deux."
        )
    if comp.prompt:
        return comp.prompt
    if comp.prompt_name:
        try:
            return load_prompt(comp.prompt_name)
        except PromptError as exc:
            raise RunPlanningError(str(exc)) from exc
    return None


def _llm_kwargs(
    label: str, comp: Competitor, role: PipelineMode
) -> dict[str, str | int | float | bool]:
    kwargs: dict[str, str | int | float | bool] = {"label": label, "role": role}
    if comp.model:
        kwargs["model"] = comp.model
    prompt = _resolve_prompt(comp)
    if prompt:
        kwargs["prompt"] = prompt
    return kwargs


def _pipeline_for_competitor(
    comp: Competitor, index: int,
) -> tuple[PipelineSpec, dict[str, dict[str, str | int | float | bool]]]:
    """Construit le ``PipelineSpec`` + ``adapter_kwargs`` d'**un** concurrent.

    Labels d'adapter suffixés par l'index (``c0``, ``c1``…) : chaque concurrent a
    ses propres instances de modules — pas de collision entre concurrents.
    """
    suffix = f"c{index}"
    if comp.mode is None:
        if comp.engine not in _OCR_ENGINES:
            raise RunPlanningError(f"OCR seul : moteur non câblé : {comp.engine!r}.")
        if comp.llm:
            raise RunPlanningError("OCR seul : aucun LLM attendu.")
        name = f"{comp.engine}:{suffix}"
        step = PipelineStep(
            id="ocr",
            kind="ocr",
            adapter_name=name,
            input_types=(ArtifactType.IMAGE,),
            output_types=(ArtifactType.RAW_TEXT,),
        )
        pipeline = PipelineSpec(
            name=comp.engine, initial_inputs=(ArtifactType.IMAGE,), steps=(step,)
        )
        ocr_kwargs: dict[str, dict[str, str | int | float | bool]] = {
            name: {"label": suffix, "lang": comp.lang}
        }
        # En OCR seul, ``model`` est le **modèle du moteur** (chemin .mlmodel
        # kraken, config PERO, checkpoint Calamari, nom Mistral OCR) — requis par
        # ces moteurs. Tesseract/Google/Azure ignorent ce kwarg. (En chaîne,
        # ``model`` désigne le LLM aval, cf. ``_llm_kwargs``.)
        if comp.model:
            ocr_kwargs[name]["model"] = comp.model
        return pipeline, ocr_kwargs

    if comp.mode == "zero_shot":
        if comp.engine not in _VLM_ENGINES:
            raise RunPlanningError(
                f"zero_shot : {comp.engine!r} n'a pas de VLM (vision)."
            )
        if comp.llm:
            raise RunPlanningError(
                "zero_shot : pas de LLM séparé (le moteur EST le VLM)."
            )
        name = f"{comp.engine}:{suffix}"
        step = PipelineStep(
            id="vlm",
            kind="transcription",
            adapter_name=name,
            input_types=(ArtifactType.IMAGE,),
            output_types=(ArtifactType.RAW_TEXT,),
        )
        pipeline = PipelineSpec(
            name=f"{comp.engine} (zero-shot)",
            initial_inputs=(ArtifactType.IMAGE,),
            steps=(step,),
        )
        return pipeline, {name: _llm_kwargs(suffix, comp, "zero_shot")}

    # text_only / text_and_image : OCR amont → LLM/VLM.
    if comp.engine not in _OCR_ENGINES:
        raise RunPlanningError(
            f"{comp.mode} : moteur OCR amont non câblé : {comp.engine!r}."
        )
    if not comp.llm:
        raise RunPlanningError(f"{comp.mode} : un fournisseur LLM est requis.")
    allowed = _LLM_ENGINES if comp.mode == "text_only" else _VLM_ENGINES
    if comp.llm not in allowed:
        raise RunPlanningError(
            f"{comp.mode} : fournisseur {comp.llm!r} indisponible pour ce mode."
        )
    ocr_name = f"{comp.engine}:{suffix}"
    llm_name = f"{comp.llm}:{suffix}"
    ocr_step = PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name=ocr_name,
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )
    llm_inputs: tuple[ArtifactType, ...]
    inputs_from: dict[ArtifactType, str]
    if comp.mode == "text_only":
        llm_inputs = (ArtifactType.RAW_TEXT,)
        inputs_from = {ArtifactType.RAW_TEXT: "ocr"}
    else:  # text_and_image — le VLM reçoit l'image initiale ET le texte OCR.
        llm_inputs = (ArtifactType.RAW_TEXT, ArtifactType.IMAGE)
        inputs_from = {
            ArtifactType.RAW_TEXT: "ocr",
            ArtifactType.IMAGE: INITIAL_STEP_ID,
        }
    llm_step = PipelineStep(
        id="llm",
        kind="post_correction",
        adapter_name=llm_name,
        input_types=llm_inputs,
        output_types=(ArtifactType.CORRECTED_TEXT,),
        inputs_from=inputs_from,
    )
    pipeline = PipelineSpec(
        name=f"{comp.engine}→{comp.llm}",
        initial_inputs=(ArtifactType.IMAGE,),
        steps=(ocr_step, llm_step),
    )
    kwargs: dict[str, dict[str, str | int | float | bool]] = {
        ocr_name: {"label": suffix, "lang": comp.lang},
        llm_name: _llm_kwargs(suffix, comp, comp.mode),
    }
    return pipeline, kwargs


def plan_benchmark_run(
    competitors: tuple[Competitor, ...],
    corpus: CorpusSpec | None,
    run_id: str,
    *,
    normalization: str | None = None,
    char_exclude: str | None = None,
    archaic_list: str | None = None,
    metric_profile: str | None = None,
) -> Callable[[Path], RunSpec]:
    """Builder de spec d'un **benchmark** : N concurrents → un ``RunSpec``.

    Exhaustif : tout moteur/mode non câblé est refusé (``RunPlanningError``).
    Les noms de pipeline sont rendus **uniques** (suffixe ``#n`` en cas de
    doublon) pour ne pas se piétiner dans les sorties indexées par nom.

    ``archaic_list`` (nom d'une liste curée, cf. ``ARCHAIC_LISTS``) **active
    ``hcpr``** (préservation des archaïsmes) et **relie ``air``/``hcpr`` à cette
    liste** ; sans lui, seul ``air`` reste actif sur la liste par défaut. Le nom
    et l'empreinte de la liste effective entrent au ``RunManifest.metadata``
    (reproductibilité) ; un nom inconnu est refusé (``RunPlanningError``).

    ``metric_profile`` (nom d'un :data:`METRIC_PROFILES`) choisit le **bundle de
    colonnes scalaires** de la vue ``text`` (défaut ``standard``, byte-identique à
    l'historique) ; un nom inconnu est refusé (``RunPlanningError`` → 422). Il
    n'affecte **que** le classement par défaut — les collecteurs restent intacts.
    """
    if not competitors:
        raise RunPlanningError("benchmark : au moins un concurrent requis.")
    if corpus is None:
        raise RunPlanningError("benchmark : corpus requis.")
    if normalization is not None and normalization not in NORMALIZATION_PROFILES:
        raise RunPlanningError(
            f"profil de normalisation inconnu : {normalization!r}."
        )
    base_metrics = _resolve_metric_profile(metric_profile)
    try:
        resolved = resolve_archaic_list(archaic_list)
    except XerOCRError as exc:
        raise RunPlanningError(str(exc)) from exc
    pipelines: list[PipelineSpec] = []
    adapter_kwargs: dict[str, dict[str, str | int | float | bool]] = {}
    seen: dict[str, int] = {}
    for index, comp in enumerate(competitors):
        pipeline, kwargs = _pipeline_for_competitor(comp, index)
        if pipeline.name in seen:
            seen[pipeline.name] += 1
            pipeline = pipeline.model_copy(
                update={"name": f"{pipeline.name} #{seen[pipeline.name]}"}
            )
        else:
            seen[pipeline.name] = 1
        pipelines.append(pipeline)
        adapter_kwargs.update(kwargs)
    spec = RunSpec(
        corpus=corpus,
        pipelines=tuple(pipelines),
        evaluation=EvaluationSpec(
            views=_views_for_corpus(
                corpus, normalization, char_exclude,
                with_hcpr=archaic_list is not None,
                base_metrics=base_metrics,
            )
        ),
        adapter_kwargs=adapter_kwargs,
        run_id=run_id,
        metadata={
            "archaic_list": resolved.name,
            "archaic_list_hash": resolved.list_hash,
        },
    )
    return lambda _ws: spec


def benchmark_engine_catalog(
    statuses: tuple[EngineStatus, ...],
) -> dict[str, list[dict[str, object]]]:
    """Moteurs proposables au composeur, **par rôle** (``ocr``/``llm``/``vlm``).

    Source unique des rôles : les mêmes ensembles que ``plan_benchmark_run``
    accepte (anti-vide — on n'offre jamais une option sans branche serveur). Un
    moteur indisponible **reste listé** (grisé côté UI) : son backend existe, il
    manque seulement une clé/un binaire.
    """
    by_kind = {status.kind: status for status in statuses}

    def role(kinds: frozenset[str]) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for kind in sorted(kinds):
            status = by_kind.get(kind)
            if status is not None:
                entries.append(
                    {
                        "kind": kind,
                        "label": status.label,
                        "available": status.available,
                    }
                )
        return entries

    return {
        "ocr": role(_OCR_ENGINES),
        "llm": role(_LLM_ENGINES),
        "vlm": role(_VLM_ENGINES),
    }


def metric_profile_catalog() -> tuple[dict[str, object], ...]:
    """Profils de métriques proposables au lanceur — **source unique** de l'UI.

    ``standard`` (défaut) d'abord, puis les autres triés (ordre déterministe).
    Chaque entrée porte la liste **ordonnée** de ses métriques : le formulaire
    s'en sert pour un libellé self-documenté (les noms de métriques sont neutres
    en langue, pas d'i18n par profil). Anti-vide : on n'offre jamais une option
    sans branche serveur — chaque nom est résolu par ``_resolve_metric_profile``.
    """
    others = sorted(name for name in METRIC_PROFILES if name != DEFAULT_METRIC_PROFILE)
    return tuple(
        {"name": name, "metrics": list(METRIC_PROFILES[name])}
        for name in (DEFAULT_METRIC_PROFILE, *others)
    )


def _segmentation_spec(corpus: CorpusSpec, run_id: str) -> RunSpec:
    """Pipeline de segmentation à 1 étape : ``pp_doclayout`` (IMAGE→LAYOUT).

    Aucune vue d'évaluation : un run de segmentation produit de la **géométrie**
    (captée par le sink), pas une métrique scalaire. Le ``RunResult`` reste
    l'output formel du run ; la visualisation vit sur ``/segmentation``.
    """
    step = PipelineStep(
        id="seg",
        kind="layout",
        adapter_name=SEGMENTER_KIND,
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.LAYOUT,),
    )
    return RunSpec(
        corpus=corpus,
        pipelines=(
            PipelineSpec(
                name=SEGMENTER_KIND,
                initial_inputs=(ArtifactType.IMAGE,),
                steps=(step,),
            ),
        ),
        evaluation=EvaluationSpec(views=()),
        run_id=run_id,
    )


def plan_segmentation_run(
    corpus: CorpusSpec, run_id: str
) -> Callable[[Path], RunSpec]:
    """Builder de spec d'un run de **segmentation** (``pp_doclayout``)."""
    return lambda _ws: _segmentation_spec(corpus, run_id)


__all__ = [
    "DEFAULT_METRIC_PROFILE",
    "METRIC_PROFILES",
    "SEGMENTER_KIND",
    "Competitor",
    "RunPlanningError",
    "benchmark_engine_catalog",
    "metric_profile_catalog",
    "plan_benchmark_run",
    "plan_segmentation_run",
]
