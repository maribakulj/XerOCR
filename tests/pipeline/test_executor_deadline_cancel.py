"""Ancrage Phase 1 — invariant §12 *timeout/annulation coopératifs* de l'exécuteur.

Ces tests **figent le comportement actuel** de l'enchaînement deadline/annulation
**avant** que la Phase 4 ne touche à ``Deadline`` (et décide de remplir ou de
trimmer l'enveloppe). Ils couvrent deux choses que la suite ne testait pas :

1. la ``Deadline`` est bien **propagée** au module, et un module qui la **sonde**
   avorte (``DeadlineExceeded``) ;
2. l'exécuteur **ne fait pas respecter** lui-même la deadline (il délègue) — c'est
   une *caractérisation* du trou actuel, pas une approbation : la décision
   « l'exécuteur doit-il avorter sur deadline expirée ? » est explicitement
   renvoyée à la Phase 4. Le commentaire de chaque test le signale.

Côté annulation : on figeait seulement l'annulation **avant** démarrage ; on ajoute
ici l'annulation **entre deux étapes** et **pendant le fan-out** (une région sur
deux), plus la caractérisation du fait qu'une ``DeadlineExceeded`` levée *dans* le
fan-out est **absorbée** comme un échec de région (saut), pas propagée.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.deadline import Deadline
from cinoc.domain.errors import DeadlineExceeded, RunCancelledError
from cinoc.domain.layout import CanonicalLayout, LayoutPage, Region
from cinoc.domain.pipeline import PipelineSpec, PipelineStep
from cinoc.pipeline.executor import PipelineExecutor
from cinoc.pipeline.fanout import run_region_fanout
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput

CODE_VERSION = "test-1.0"


def _image() -> Artifact:
    return Artifact(
        id="doc1:init:image",
        document_id="doc1",
        type=ArtifactType.IMAGE,
        uri="img://doc1.png",
    )


def _ocr_step() -> PipelineStep:
    return PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name="fake:mod",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )


def _raw_text(document_id: str, name: str) -> StepOutput:
    return StepOutput(
        artifacts={
            ArtifactType.RAW_TEXT: Artifact(
                id=f"{document_id}:{name}:raw_text",
                document_id=document_id,
                type=ArtifactType.RAW_TEXT,
                uri="mem://raw",
            )
        }
    )


# ── Modules de test ──────────────────────────────────────────────────────────


class _DeadlineAwareModule:
    """Sonde ``context.deadline.is_expired()`` et lève ``DeadlineExceeded``."""

    name = "fake:deadline_aware"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        if context.deadline.is_expired():
            raise DeadlineExceeded("fake:deadline_aware : deadline expirée.")
        return _raw_text(context.document_id, self.name)


class _DeadlineIgnoringModule:
    """Ignore la deadline (façon module non coopératif) et produit toujours."""

    name = "fake:deadline_ignoring"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        return _raw_text(context.document_id, self.name)


class _DeadlineCaptureModule:
    """Capture l'état de la deadline reçue (par défaut)."""

    name = "fake:capture"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def __init__(self) -> None:
        self.seen: dict[str, bool] = {}

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        self.seen["is_infinite"] = context.deadline.is_infinite
        self.seen["is_expired"] = context.deadline.is_expired()
        return _raw_text(context.document_id, self.name)


class _CancelThenEmit:
    """Étape 1 : déclenche l'annulation puis produit son artefact normalement."""

    name = "fake:cancel"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        control.trigger_cancel()
        return _raw_text(context.document_id, self.name)


class _RecordingModule:
    """Étape 2 : enregistre qu'elle a été exécutée."""

    name = "fake:recording"
    version = "0.1"
    input_types = frozenset({ArtifactType.RAW_TEXT})
    output_types = frozenset({ArtifactType.CORRECTED_TEXT})

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        self.calls += 1
        return StepOutput(
            artifacts={
                ArtifactType.CORRECTED_TEXT: Artifact(
                    id=f"{context.document_id}:{self.name}:corrected",
                    document_id=context.document_id,
                    type=ArtifactType.CORRECTED_TEXT,
                    uri="mem://corrected",
                )
            }
        )


# ── 1. Deadline propagée + module coopératif ────────────────────────────────


def test_module_aborts_on_expired_deadline() -> None:
    """Une deadline déjà expirée, sondée par le module, lève ``DeadlineExceeded``.
    Pin : la ``Deadline`` est bien threadée jusqu'au module."""
    spec = PipelineSpec(
        name="p", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    with pytest.raises(DeadlineExceeded):
        PipelineExecutor(CODE_VERSION).execute_document(
            spec,
            {"fake:mod": _DeadlineAwareModule()},
            {ArtifactType.IMAGE: _image()},
            document_id="doc1",
            deadline=Deadline.at_monotonic(0.0),
        )


def test_executor_does_not_self_enforce_deadline() -> None:
    """CARACTÉRISATION (≠ approbation) : avec une deadline expirée mais un module
    qui l'ignore, l'exécuteur **n'avorte pas** — l'application est entièrement
    déléguée aux modules. La Phase 4 décidera si l'exécuteur doit la faire
    respecter lui-même ; ce test fige l'état actuel pour rendre ce changement
    visible."""
    spec = PipelineSpec(
        name="p", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    execution = PipelineExecutor(CODE_VERSION).execute_document(
        spec,
        {"fake:mod": _DeadlineIgnoringModule()},
        {ArtifactType.IMAGE: _image()},
        document_id="doc1",
        deadline=Deadline.at_monotonic(0.0),
    )
    assert ArtifactType.RAW_TEXT in execution.artifacts


def test_default_deadline_is_infinite_and_not_expired() -> None:
    """Sans argument ``deadline``, le module reçoit une deadline infinie."""
    module = _DeadlineCaptureModule()
    spec = PipelineSpec(
        name="p", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    PipelineExecutor(CODE_VERSION).execute_document(
        spec,
        {"fake:mod": module},
        {ArtifactType.IMAGE: _image()},
        document_id="doc1",
    )
    assert module.seen == {"is_infinite": True, "is_expired": False}


# ── 2. Annulation entre étapes ──────────────────────────────────────────────


def test_cancellation_between_steps_skips_remaining() -> None:
    """L'étape 1 déclenche l'annulation ; l'étape 2 ne doit pas s'exécuter.
    Pin : l'exécuteur sonde l'annulation **au début de chaque étape**."""
    step2 = PipelineStep(
        id="llm",
        kind="post_correction",
        adapter_name="fake:recording",
        input_types=(ArtifactType.RAW_TEXT,),
        output_types=(ArtifactType.CORRECTED_TEXT,),
        inputs_from={ArtifactType.RAW_TEXT: "ocr"},
    )
    spec = PipelineSpec(
        name="p2", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(), step2)
    )
    recording = _RecordingModule()
    with pytest.raises(RunCancelledError):
        PipelineExecutor(CODE_VERSION).execute_document(
            spec,
            {"fake:mod": _CancelThenEmit(), "fake:recording": recording},
            {ArtifactType.IMAGE: _image()},
            document_id="doc1",
        )
    assert recording.calls == 0


# ── 3. Annulation et deadline pendant le fan-out par région ──────────────────


class _RegionRecognizer:
    """Reconnaisseur de région paramétrable (annule / lève DeadlineExceeded / OK)."""

    name = "fake:recognizer"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def __init__(self, out_dir: Path, *, mode: str) -> None:
        self._out_dir = out_dir
        self._mode = mode
        self.calls = 0

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        self.calls += 1
        if self._mode == "deadline":
            raise DeadlineExceeded("fake:recognizer : deadline expirée.")
        region_id = inputs[ArtifactType.IMAGE].region_id or "page"
        out = self._out_dir / f"{region_id}.txt"
        out.write_text("ocr", encoding="utf-8")
        if self._mode == "cancel":
            control.trigger_cancel()
        return StepOutput(
            artifacts={
                ArtifactType.RAW_TEXT: Artifact(
                    id=f"{context.document_id}:{region_id}:raw_text",
                    document_id=context.document_id,
                    type=ArtifactType.RAW_TEXT,
                    uri=str(out),
                )
            }
        )


def _two_region_layout() -> CanonicalLayout:
    page = LayoutPage(regions=(Region(id="r1"), Region(id="r2")))
    return CanonicalLayout(pages=(page,))


def _ctx() -> RunContext:
    return RunContext(document_id="doc1", code_version=CODE_VERSION, pipeline_name="p")


def test_fanout_cancellation_between_regions(tmp_path: Path) -> None:
    """Annulation déclenchée pendant la 1re région : la 2e n'est pas traitée.
    Pin : ``_fill_region`` sonde l'annulation au début de chaque région."""
    recognizer = _RegionRecognizer(tmp_path, mode="cancel")
    with pytest.raises(RunCancelledError):
        run_region_fanout(
            layout=_two_region_layout(),
            page_image=_image(),
            recognizer=recognizer,
            context=_ctx(),
            control=RunControl(),
        )
    assert recognizer.calls == 1  # 2e région jamais atteinte


def test_fanout_swallows_deadline_exceeded_as_region_skip(tmp_path: Path) -> None:
    """CARACTÉRISATION : une ``DeadlineExceeded`` (sous-classe d'``AdapterStepError``)
    levée *dans* le fan-out est **absorbée** comme un échec de région (la page n'est
    pas abattue, la région reste vide). À revoir en Phase 4 : un timeout de page
    devrait-il avorter tout le fan-out plutôt que sauter une région ?"""
    recognizer = _RegionRecognizer(tmp_path, mode="deadline")
    filled, _usage = run_region_fanout(
        layout=_two_region_layout(),
        page_image=_image(),
        recognizer=recognizer,
        context=_ctx(),
        control=RunControl(),
    )
    regions = filled.pages[0].regions
    assert len(regions) == 2
    assert all(region.lines == () for region in regions)
    assert recognizer.calls == 2  # les deux régions tentées, aucune n'abat la page
