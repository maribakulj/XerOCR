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
from xerocr.formats.text import NORMALIZATION_PROFILES

#: Segmenteur de mise en page du socle — **source unique** du *kind* (consommé
#: par la planification du run de segmentation ET par le gate du routeur).
SEGMENTER_KIND = "pp_doclayout"

#: Moteurs OCR câblés pour un run réel (amont d'une chaîne ou OCR seul).
_OCR_ENGINES = frozenset(
    {"tesseract", "kraken", "mistral_ocr", "google_vision", "azure_di"}
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
    #: par défaut du rôle (``default_prompt_for_role``). Exposé à l'UI.
    prompt: str | None = Field(default=None, max_length=8000)


#: Types de candidat scorés par toute vue benchmark : ``RAW_TEXT`` (OCR/zero-shot)
#: **et** ``CORRECTED_TEXT`` (OCR→LLM) — la précédence du runner évalue la sortie
#: la plus aboutie de chaque pipeline (cf. evaluation).
_CANDIDATES = frozenset({ArtifactType.RAW_TEXT, ArtifactType.CORRECTED_TEXT})


def _ocr_view(normalization: str | None) -> EvaluationView:
    return EvaluationView(
        name="text",
        candidate_types=_CANDIDATES,
        metric_names=("cer", "wer", "mer", "searchability", "hallucination"),
        normalization_profile=normalization,
    )


def _reference_view(normalization: str | None) -> EvaluationView:
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
    )


def _views_for_corpus(
    corpus: CorpusSpec, normalization: str | None = None
) -> tuple[EvaluationView, ...]:
    """Vues à évaluer selon les **types de GT présents**, sous ``normalization``.

    GT manuelle ``RAW_TEXT`` → vue ``text`` ; référence ``REFERENCE_TEXT`` (OCR
    Gallica) → vue *référence* distincte. Un corpus sans GT → vue ``text`` par
    défaut (le run reste exécutable, simplement non scoré).
    """
    gt_types = {gt.type for doc in corpus.documents for gt in doc.ground_truths}
    views: list[EvaluationView] = []
    if ArtifactType.RAW_TEXT in gt_types:
        views.append(_ocr_view(normalization))
    if ArtifactType.REFERENCE_TEXT in gt_types:
        views.append(_reference_view(normalization))
    if not views:
        views.append(_ocr_view(normalization))
    return tuple(views)


def _llm_kwargs(
    label: str, comp: Competitor, role: PipelineMode
) -> dict[str, str | int | float | bool]:
    kwargs: dict[str, str | int | float | bool] = {"label": label, "role": role}
    if comp.model:
        kwargs["model"] = comp.model
    if comp.prompt:
        kwargs["prompt"] = comp.prompt
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
) -> Callable[[Path], RunSpec]:
    """Builder de spec d'un **benchmark** : N concurrents → un ``RunSpec``.

    Exhaustif : tout moteur/mode non câblé est refusé (``RunPlanningError``).
    Les noms de pipeline sont rendus **uniques** (suffixe ``#n`` en cas de
    doublon) pour ne pas se piétiner dans les sorties indexées par nom.
    """
    if not competitors:
        raise RunPlanningError("benchmark : au moins un concurrent requis.")
    if corpus is None:
        raise RunPlanningError("benchmark : corpus requis.")
    if normalization is not None and normalization not in NORMALIZATION_PROFILES:
        raise RunPlanningError(
            f"profil de normalisation inconnu : {normalization!r}."
        )
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
        evaluation=EvaluationSpec(views=_views_for_corpus(corpus, normalization)),
        adapter_kwargs=adapter_kwargs,
        run_id=run_id,
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
    "SEGMENTER_KIND",
    "Competitor",
    "RunPlanningError",
    "benchmark_engine_catalog",
    "plan_benchmark_run",
    "plan_segmentation_run",
]
