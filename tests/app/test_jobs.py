"""``JobRunner`` : run de fond → ``RunResult`` écrit, échec tracé, annulation."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from xerocr.adapters.storage import JobState, JobStore
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
from xerocr.pipeline.types import RunContext


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
    ) -> dict[ArtifactType, Artifact]:
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
