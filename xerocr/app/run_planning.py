"""Planification d'un run : (moteur, corpus) → ``RunSpec`` (couche 6).

Construire une spec d'exécution est de l'**orchestration**, pas du transport :
les routeurs (couche 8) délèguent ici et ne fabriquent **aucun** ``RunSpec``
eux-mêmes. Le dispatch moteur est **exhaustif** — un moteur non câblé pour un run
est refusé explicitement (``RunPlanningError``), jamais redirigé en silence vers
un autre moteur (anti-régression du défaut « ``mistral`` → tesseract »).

Le ``precomputed`` (démonstration) reste planifié en couche 8 : il matérialise un
mini-corpus de *fixture* (``interfaces/demo``), hors du périmètre de planification
des moteurs réels traité ici.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.errors import XerOCRError
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.projection import ProjectionSpec
from xerocr.domain.run_spec import RunSpec

#: Segmenteur de mise en page du socle — **source unique** du *kind* (consommé
#: par la planification du run de segmentation ET par le gate du routeur).
SEGMENTER_KIND = "pp_doclayout"


class RunPlanningError(XerOCRError):
    """Moteur non câblé pour un run, ou incohérence moteur⇄corpus."""


_OCR_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer", "wer", "mer"),
)

#: Vue **référence OCR** (opt-in) : compare le candidat ``RAW_TEXT`` à une
#: référence ``REFERENCE_TEXT`` (ex. OCR Gallica) via une projection identité. Le
#: **nom de la vue porte l'avertissement** (rendu tel quel par le rapport) : ce
#: n'est PAS une vérité-terrain manuelle, le score mesure l'accord avec un autre
#: OCR. La vue ``text`` par défaut ne déclare pas cette projection → elle ignore
#: les GT ``REFERENCE_TEXT`` (pas de faux score d'exactitude).
_REFERENCE_VIEW = EvaluationView(
    name="référence OCR (pas une vérité-terrain manuelle)",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    projections_by_source_type={
        ArtifactType.REFERENCE_TEXT: ProjectionSpec(
            source_type=ArtifactType.REFERENCE_TEXT,
            target_type=ArtifactType.RAW_TEXT,
            projector_name="identity_text",
        )
    },
    metric_names=("cer", "wer", "mer"),
    ignored_dimensions=("exactitude (la référence est elle-même un OCR)",),
)


def _views_for_corpus(corpus: CorpusSpec) -> tuple[EvaluationView, ...]:
    """Vues à évaluer selon les **types de GT présents** dans le corpus.

    GT manuelle ``RAW_TEXT`` → vue ``text`` ; référence ``REFERENCE_TEXT`` (OCR
    Gallica) → vue *référence* distincte. Un corpus sans GT → vue ``text`` par
    défaut (le run reste OCR-able, simplement non scoré). On n'émet une vue que si
    elle a de quoi être renseignée : pas de vue vide spéculative.
    """
    gt_types = {gt.type for doc in corpus.documents for gt in doc.ground_truths}
    views: list[EvaluationView] = []
    if ArtifactType.RAW_TEXT in gt_types:
        views.append(_OCR_VIEW)
    if ArtifactType.REFERENCE_TEXT in gt_types:
        views.append(_REFERENCE_VIEW)
    if not views:
        # Aucune GT (ex. corpus IIIF images-seules) : vue OCR par défaut — le run
        # s'exécute et reste lisible, simplement non scoré (pas de référence).
        views.append(_OCR_VIEW)
    return tuple(views)


def _tesseract_spec(corpus: CorpusSpec, run_id: str, *, lang: str = "fra") -> RunSpec:
    label = "tesseract"
    step = PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name=f"tesseract:{label}",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )
    return RunSpec(
        corpus=corpus,
        pipelines=(
            PipelineSpec(
                name=label,
                initial_inputs=(ArtifactType.IMAGE,),
                steps=(step,),
            ),
        ),
        evaluation=EvaluationSpec(views=_views_for_corpus(corpus)),
        adapter_kwargs={f"tesseract:{label}": {"label": label, "lang": lang}},
        run_id=run_id,
    )


def plan_ocr_run(
    engine: str, corpus: CorpusSpec | None, run_id: str
) -> Callable[[Path], RunSpec]:
    """Builder de spec OCR pour ``engine`` (hors ``precomputed``).

    **Exhaustif** : seul ``tesseract`` est câblé pour un run réel ; tout autre
    moteur est refusé explicitement (``RunPlanningError``) — jamais de retombée
    silencieuse sur un autre moteur.
    """
    if engine == "tesseract":
        if corpus is None:
            raise RunPlanningError("tesseract : corpus requis.")
        return lambda _ws: _tesseract_spec(corpus, run_id)
    raise RunPlanningError(f"moteur non exécutable pour un run : {engine!r}")


def _segmentation_spec(corpus: CorpusSpec, run_id: str) -> RunSpec:
    """Pipeline de segmentation à 1 étape : ``pp_doclayout`` (IMAGE→LAYOUT).

    Aucune vue d'évaluation : un run de segmentation produit de la **géométrie**
    (captée par le sink), pas une métrique scalaire. Le ``RunResult`` reste
    l'output formel du run (sans score) ; la visualisation vit sur ``/segmentation``.
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
    "RunPlanningError",
    "plan_ocr_run",
    "plan_segmentation_run",
]
