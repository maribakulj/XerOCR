"""``JobRunner`` : run de fond → ``RunResult`` écrit, échec tracé, annulation."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from xerocr.adapters.storage import JobState, JobStore
from xerocr.adapters.storage.history_store import HistoryStore
from xerocr.app.jobs import JobRunner
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.app.results import load_run_result
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.domain.errors import XerOCRError
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.run_spec import RunSpec
from xerocr.interfaces.demo import demo_run_spec, write_demo_corpus
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput


def _runner(tmp_path: Path) -> JobRunner:
    registry = ModuleRegistry()
    register_default_modules(registry)
    return JobRunner(
        store=JobStore(),
        registry=registry,
        reports_dir=tmp_path,
        code_version="1.0",
    )


def test_run_completes_and_writes_result(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="web-ok")
    )
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None
    assert job.state is JobState.DONE
    assert job.report_name == "web-ok"
    result_path = tmp_path / "web-ok.json"
    assert result_path.exists()
    # le JSON écrit est un RunResult relisable (bout-en-bout réel)
    assert load_run_result(result_path).manifest.run_id == "web-ok"


def test_domain_error_marks_failed(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    def build(_ws: Path) -> RunSpec:
        raise XerOCRError("spec invalide")

    job_id = runner.launch(build)
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.FAILED
    assert job.error == "spec invalide"


def test_unexpected_error_marks_failed(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    def build(_ws: Path) -> RunSpec:
        raise RuntimeError("kaboom")

    job_id = runner.launch(build)
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.FAILED
    assert job.error == "kaboom"


class _BoomPublisher:
    """Publisher qui échoue toujours (simule un dépôt distant injoignable)."""

    def publish(self, name: str, run_result_path: Path) -> str | None:
        raise RuntimeError("dépôt distant injoignable")


def test_publish_failure_does_not_fail_run(tmp_path: Path) -> None:
    # Lot G : un effet secondaire (publication) raté ne fait PAS échouer un run
    # réussi — le RunResult est écrit, le job reste DONE, published_url absent.
    registry = ModuleRegistry()
    register_default_modules(registry)
    runner = JobRunner(
        store=JobStore(),
        registry=registry,
        reports_dir=tmp_path,
        code_version="1.0",
        publisher=_BoomPublisher(),
    )
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="pub-fail")
    )
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    assert job.published_url is None
    assert (tmp_path / "pub-fail.json").exists()


def test_history_failure_does_not_fail_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Lot G : un échec d'écriture d'historique (effet secondaire) ne fait PAS
    # échouer un run réussi. On force record_run à lever.
    history = HistoryStore(tmp_path / "h.db")
    registry = ModuleRegistry()
    register_default_modules(registry)
    runner = JobRunner(
        store=JobStore(),
        registry=registry,
        reports_dir=tmp_path,
        code_version="1.0",
        history_store=history,
    )

    def _boom(*a: object, **k: object) -> int:
        raise RuntimeError("sqlite indisponible")

    monkeypatch.setattr("xerocr.app.jobs.record_run", _boom)
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="hist-fail")
    )
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    assert (tmp_path / "hist-fail.json").exists()


def test_cancel_unknown_or_terminal_is_false(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    assert runner.cancel("absent") is False
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="web-done")
    )
    assert runner.join(job_id, timeout=30)
    assert runner.cancel(job_id) is False  # déjà terminé


class _BlockingModule:
    """Module qui bloque jusqu'à l'annulation coopérative (test de cancel)."""

    def __init__(self) -> None:
        self.started = threading.Event()

    name = "blocking:test"
    version = "1.0"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        self.started.set()
        while not control.is_cancelled():
            time.sleep(0.005)
        control.raise_if_cancelled()  # lève RunCancelledError
        raise AssertionError("inatteignable")  # pragma: no cover


def _blocking_spec() -> RunSpec:
    corpus = CorpusSpec(
        name="block",
        documents=(DocumentRef(id="d1", image_uri="mem://d1"),),
    )
    pipeline = PipelineSpec(
        name="p",
        initial_inputs=(ArtifactType.IMAGE,),
        steps=(
            PipelineStep(
                id="s",
                kind="blocking",
                adapter_name="blocking:test",
                input_types=(ArtifactType.IMAGE,),
                output_types=(ArtifactType.RAW_TEXT,),
            ),
        ),
    )
    view = EvaluationView(
        name="text",
        candidate_types=frozenset({ArtifactType.RAW_TEXT}),
        metric_names=("cer",),
    )
    return RunSpec(
        corpus=corpus,
        pipelines=(pipeline,),
        evaluation=EvaluationSpec(views=(view,)),
        run_id="web-cancel",
    )


class _RecordingPublisher:
    """Publisher de test : enregistre l'appel, renvoie une URL distante."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def publish(self, name: str, run_result_path: Path) -> str | None:
        self.calls.append((name, str(run_result_path)))
        return "https://remote/reports/" + name


class _RaisingPublisher:
    def publish(self, name: str, run_result_path: Path) -> str | None:
        raise RuntimeError("réseau indisponible")


def test_publish_on_done_sets_url(tmp_path: Path) -> None:
    registry = ModuleRegistry()
    register_default_modules(registry)
    pub = _RecordingPublisher()
    runner = JobRunner(
        store=JobStore(), registry=registry, reports_dir=tmp_path,
        code_version="1.0", publisher=pub,
    )
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="web-pub")
    )
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    assert job.published_url == "https://remote/reports/web-pub"
    assert pub.calls == [("web-pub", str(tmp_path / "web-pub.json"))]


def test_publish_failure_does_not_fail_the_run(tmp_path: Path) -> None:
    registry = ModuleRegistry()
    register_default_modules(registry)
    runner = JobRunner(
        store=JobStore(), registry=registry, reports_dir=tmp_path,
        code_version="1.0", publisher=_RaisingPublisher(),
    )
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="web-pf")
    )
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    # best-effort : le run reste DONE (résultat local écrit), URL absente.
    assert job is not None and job.state is JobState.DONE
    assert job.published_url is None


def test_default_runner_does_not_publish(tmp_path: Path) -> None:
    runner = _runner(tmp_path)  # sans publisher → NoopPublisher
    job_id = runner.launch(
        lambda ws: demo_run_spec(write_demo_corpus(ws), run_id="web-np")
    )
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.published_url is None


def test_cancel_interrupts_a_running_job(tmp_path: Path) -> None:
    registry = ModuleRegistry()
    module = _BlockingModule()
    registry.register_builder("blocking", lambda _kwargs: module)
    runner = JobRunner(
        store=JobStore(), registry=registry, reports_dir=tmp_path, code_version="1.0"
    )

    job_id = runner.launch(lambda _ws: _blocking_spec())
    assert module.started.wait(timeout=30)  # le run est bien en vol
    assert runner.cancel(job_id) is True
    assert runner.join(job_id, timeout=30)

    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.CANCELLED
    assert not (tmp_path / "web-cancel.json").exists()  # aucun résultat écrit


# --- Sink LAYOUT → SegmentationStore (T2) --------------------------------------

def _layout_build(layout_text_id: str = "r1"):
    """Builder d'un run de segmentation precomputed (IMAGE→LAYOUT) dans le ws."""
    from xerocr.domain.layout import CanonicalLayout, LayoutPage, Region

    layout = CanonicalLayout(
        pages=(LayoutPage(regions=(Region(id=layout_text_id, region_type="text"),)),)
    )

    def build(ws: Path) -> RunSpec:
        image = ws / "doc1.png"
        image.write_bytes(b"\x89PNG stub")
        (ws / "doc1.layout.json").write_bytes(
            layout.model_dump_json().encode("utf-8")
        )
        step = PipelineStep(
            id="seg", kind="layout", adapter_name="precomputed_layout",
            input_types=(ArtifactType.IMAGE,), output_types=(ArtifactType.LAYOUT,),
        )
        return RunSpec(
            corpus=CorpusSpec(
                name="c", documents=(DocumentRef(id="doc1", image_uri=str(image)),)
            ),
            pipelines=(
                PipelineSpec(
                    name="seg", initial_inputs=(ArtifactType.IMAGE,), steps=(step,)
                ),
            ),
            evaluation=EvaluationSpec(views=()),
            run_id="seg-run",
        )

    return build


def test_run_persists_layout_to_segmentation_store(tmp_path: Path) -> None:
    from xerocr.app.segmentation import SegmentationStore

    seg = SegmentationStore(tmp_path / "seg")
    registry = ModuleRegistry()
    register_default_modules(registry)
    runner = JobRunner(
        store=JobStore(), registry=registry, reports_dir=tmp_path,
        code_version="1.0", segmentation_store=seg,
    )
    job_id = runner.launch(_layout_build())
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
    # le LAYOUT produit par le run est persisté → /segmentation le verra
    seg_id = seg.latest()
    assert seg_id is not None
    persisted = seg.get_layout(seg_id)
    assert persisted is not None
    assert persisted.pages[0].regions[0].id == "r1"


def test_run_without_segmentation_store_still_done(tmp_path: Path) -> None:
    # Sink optionnel : sans store, un run produisant un LAYOUT aboutit quand même.
    runner = _runner(tmp_path)  # pas de segmentation_store
    job_id = runner.launch(_layout_build())
    assert runner.join(job_id, timeout=30)
    job = runner.store.get(job_id)
    assert job is not None and job.state is JobState.DONE
